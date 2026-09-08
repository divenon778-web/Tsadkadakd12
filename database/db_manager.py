import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trackin.db")


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
