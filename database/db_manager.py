import aiosqlite
import os
import glob
import re
import urllib.request

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trackin.db")


def _download_from_gdrive(file_id, dest_path):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type:
        body = resp.read().decode("utf-8", errors="ignore")
        confirm_match = re.search(r'confirm=([0-9A-Za-z_-]+)', body)
        if confirm_match:
            url += f"&confirm={confirm_match.group(1)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req)
    with open(dest_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def reassemble_db_from_parts():
    if os.path.exists(DB_PATH):
        return
    db_dir = os.path.dirname(DB_PATH)
    part_files = glob.glob(os.path.join(db_dir, "trackin.db.part.*"))
    if not part_files:
        gdrive_ids = os.getenv("GDRIVE_DB_PARTS", "")
        if gdrive_ids:
            ids = [i.strip() for i in gdrive_ids.split(",") if i.strip()]
            for idx, file_id in enumerate(ids):
                suffix = chr(ord("a") + idx) if idx < 26 else f"{idx}"
                dest = os.path.join(db_dir, f"trackin.db.part.{suffix}")
                if not os.path.exists(dest):
                    print(f"Downloading DB part {suffix} from Google Drive...")
                    _download_from_gdrive(file_id, dest)
            part_files = glob.glob(os.path.join(db_dir, "trackin.db.part.*"))
    if not part_files:
        return
    def sort_key(path):
        match = re.search(r"\.part\.(\w+)$", path)
        return match.group(1) if match else ""
    part_files.sort(key=sort_key)
    with open(DB_PATH, "wb") as out:
        for pf in part_files:
            with open(pf, "rb") as f:
                out.write(f.read())
    print(f"Assembled trackin.db from {len(part_files)} parts")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            hwid TEXT,
            ip TEXT,
            computer_name TEXT,
            os TEXT,
            stealer_type TEXT,
            cookies TEXT,
            passwords TEXT,
            tokens TEXT,
            credit_cards TEXT,
            wallets TEXT,
            raw_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ip ON logs(ip)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_hwid ON logs(hwid)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_computer_name ON logs(computer_name)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_stealer_type ON logs(stealer_type)")
    await db.commit()
    await db.close()


async def search_logs(keyword=None, limit=10, offset=0):
    db = await get_db()
    params = []

    if keyword:
        like = f"%{keyword}%"
        where = """(
            ip LIKE ? OR
            hwid LIKE ? OR
            computer_name LIKE ? OR
            cookies LIKE ? OR
            passwords LIKE ? OR
            tokens LIKE ? OR
            credit_cards LIKE ? OR
            wallets LIKE ? OR
            raw_text LIKE ?
        )"""
        params = [like, like, like, like, like, like, like, like, like]
    else:
        where = "1=1"

    query = f"SELECT * FROM logs WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    query_params = params + [limit, offset]

    cursor = await db.execute(query, query_params)
    rows = await cursor.fetchall()

    count_query = f"SELECT COUNT(*) as total FROM logs WHERE {where}"
    count_cursor = await db.execute(count_query, params)
    total_row = await count_cursor.fetchone()
    total = total_row["total"] if total_row else 0

    await db.close()
    return [dict(row) for row in rows], total


async def get_log_by_id(log_id):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def insert_log(data: dict):
    db = await get_db()
    await db.execute("""
        INSERT INTO logs (filename, hwid, ip, computer_name, os, stealer_type, cookies, passwords, tokens, credit_cards, wallets, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("filename"),
        data.get("hwid"),
        data.get("ip"),
        data.get("computer_name"),
        data.get("os"),
        data.get("stealer_type"),
        data.get("cookies"),
        data.get("passwords"),
        data.get("tokens"),
        data.get("credit_cards"),
        data.get("wallets"),
        data.get("raw_text"),
    ))
    await db.commit()
    await db.close()


async def get_stats():
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) as total FROM logs")
    row = await cursor.fetchone()
    total = row["total"] if row else 0

    cursor2 = await db.execute("SELECT COUNT(DISTINCT ip) as unique_ips FROM logs")
    row2 = await cursor2.fetchone()
    unique_ips = row2["unique_ips"] if row2 else 0

    cursor3 = await db.execute("SELECT COUNT(DISTINCT hwid) as unique_hwids FROM logs")
    row3 = await cursor3.fetchone()
    unique_hwids = row3["unique_hwids"] if row3 else 0

    await db.close()
    return total, unique_ips, unique_hwids


async def search_machines(keyword=None, limit=20, offset=0):
    db = await get_db()
    if keyword:
        like = f"%{keyword}%"
        query = """
            SELECT computer_name, COUNT(*) as log_count,
                   GROUP_CONCAT(DISTINCT ip) as ips,
                   GROUP_CONCAT(DISTINCT hwid) as hwids,
                   GROUP_CONCAT(DISTINCT os) as os_list,
                   GROUP_CONCAT(DISTINCT stealer_type) as stealer_types
            FROM logs
            WHERE computer_name LIKE ?
            GROUP BY LOWER(computer_name)
            ORDER BY log_count DESC
            LIMIT ? OFFSET ?
        """
        cursor = await db.execute(query, [like, limit, offset])
        rows = await cursor.fetchall()

        count_cursor = await db.execute(
            "SELECT COUNT(DISTINCT LOWER(computer_name)) as total FROM logs WHERE computer_name LIKE ?",
            [like]
        )
        total_row = await count_cursor.fetchone()
    else:
        query = """
            SELECT computer_name, COUNT(*) as log_count,
                   GROUP_CONCAT(DISTINCT ip) as ips,
                   GROUP_CONCAT(DISTINCT hwid) as hwids,
                   GROUP_CONCAT(DISTINCT os) as os_list,
                   GROUP_CONCAT(DISTINCT stealer_type) as stealer_types
            FROM logs
            GROUP BY LOWER(computer_name)
            ORDER BY log_count DESC
            LIMIT ? OFFSET ?
        """
        cursor = await db.execute(query, [limit, offset])
        rows = await cursor.fetchall()

        count_cursor = await db.execute("SELECT COUNT(DISTINCT LOWER(computer_name)) as total FROM logs")
        total_row = await count_cursor.fetchone()

    total = total_row["total"] if total_row else 0
    await db.close()
    return [dict(row) for row in rows], total


async def get_machine_data(computer_name):
    db = await get_db()
    like = f"%{computer_name}%"
    cursor = await db.execute("SELECT * FROM logs WHERE computer_name LIKE ? ORDER BY created_at DESC", [like])
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


async def get_all_machines(limit=20, offset=0):
    db = await get_db()
    query = """
        SELECT computer_name, COUNT(*) as log_count,
               GROUP_CONCAT(DISTINCT ip) as ips,
               GROUP_CONCAT(DISTINCT hwid) as hwids
        FROM logs
        WHERE computer_name IS NOT NULL AND computer_name != ''
        GROUP BY LOWER(computer_name)
        ORDER BY log_count DESC
        LIMIT ? OFFSET ?
    """
    cursor = await db.execute(query, [limit, offset])
    rows = await cursor.fetchall()

    count_cursor = await db.execute(
        "SELECT COUNT(DISTINCT LOWER(computer_name)) as total FROM logs WHERE computer_name IS NOT NULL AND computer_name != ''"
    )
    total_row = await count_cursor.fetchone()
    total = total_row["total"] if total_row else 0

    await db.close()
    return [dict(row) for row in rows], total
