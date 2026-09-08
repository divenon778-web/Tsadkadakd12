import os
import sys
import re
import json
import csv
import io
import sqlite3
import time
import zipfile
import tempfile
import hashlib
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

DB_PATH = os.path.join(os.path.dirname(__file__), "trackin.db")

STEALER_KEYWORDS = {
    "redline": ["redline", "red line", "redlinestealer"],
    "raccoon": ["raccoon", "raccoon stealer", "raccoonstealer"],
    "vidar": ["vidar", "vidar stealer"],
    "phoenix": ["phoenix", "phoenix stealer", "phoenixstealer"],
    "atomic": ["atomicstealer", "atomic stealer", "atomic"],
    "meta": ["metastealer", "meta stealer"],
    "rise": ["risestealer", "rise stealer", "riseinfostealer"],
    "recordbreaker": ["recordbreaker", "record breaker"],
    "lobshot": ["lobshot", "lob shot"],
    "danabot": ["danabot", "dana bot"],
    "zloader": ["zloader", "z loader"],
    "smokeloader": ["smokeloader", "smoke loader"],
    "daisy": ["daisy", "daisy stealer"],
    "amadey": ["amadey", "amadey stealer"],
    "laplas": ["laplas", "laplas stealer"],
    "planet": ["planet", "planet stealer"],
    "octopus": ["octopus", "octopus stealer"],
    "medusa": ["medusa", "medusa stealer"],
    "aurora": ["aurora", "aurora stealer"],
    "beast": ["beast", "beast stealer"],
    "benis": ["benis", "benis stealer"],
    "brave": ["brave stealer"],
    "chameleon": ["chameleon", "chameleon stealer"],
    "clipper": ["clipper", "clipper stealer"],
    "cornell": ["cornell", "cornell stealer"],
    "craxs": ["craxs", "craxs rat"],
    "creepstealer": ["creepstealer", "creep stealer"],
    "cuba": ["cuba", "cuba stealer"],
    "darkcomet": ["darkcomet", "dark comet"],
    "darktrack": ["darktrack", "dark track"],
    "dcrat": ["dcrat", "dcrat stealer"],
    "emotet": ["emotet"],
    "erberus": ["erberus", "erberus stealer"],
    "formbook": ["formbook", "form book"],
    "gbote": ["gbote", "gbote stealer"],
    "godot": ["godot stealer"],
    "grandstealer": ["grandstealer", "grand stealer"],
    "hawkEye": ["hawkeye", "hawk eye", "hawkeyestealer"],
    "hermes": ["hermes", "hermes stealer"],
    "hijackLoader": ["hijackloader", "hijack loader"],
    "ironnet": ["ironnet", "ironnet stealer"],
    "islander": ["islander", "islander stealer"],
    "limbo": ["limbo", "limbo stealer"],
    "lokibot": ["lokibot", "loki bot"],
    "lumma": ["lumma", "lumma stealer"],
    "macaw": ["macaw", "macaw stealer"],
    "malos": ["malos", "malos stealer"],
    "mogilev": ["mogilev", "mogilev stealer"],
    "myskle": ["myskle", "myskle stealer"],
    "nanobot": ["nanobot", "nanobot stealer"],
    "oceanloader": ["oceanloader", "ocean loader"],
    "okulu": ["okulu", "okulu stealer"],
    "operacura": ["operacura", "opera cura"],
    "parasite": ["parasite", "parasite stealer"],
    "perplexed": ["perplexed", "perplexed stealer"],
    "pinch": ["pinch", "pinch stealer"],
    "predator": ["predator", "predator stealer"],
    "privateLoader": ["privateloader", "private loader"],
    "prometei": ["prometei"],
    "purelogstealer": ["purelog", "purelogstealer"],
    "quasar": ["quasar", "quasar rat"],
    "ransom": ["ransom", "ransomware"],
    "redline_v2": ["redlinest", "redline_v2"],
    "remcos": ["remcos", "remcos rat"],
    "russianbee": ["russianbee", "russian bee"],
    "seer": ["seer", "seer stealer"],
    "sheriff": ["sheriff", "sheriff stealer"],
    "snakekeylogger": ["snakekeylogger", "snake keylogger"],
    "socio": ["socio", "socio stealer"],
    "stealc": ["stealc", "steal c"],
    "stopbot": ["stopbot", "stop bot"],
    "storm": ["storm stealer"],
    "strrat": ["strrat", "str rat"],
    "supsis": ["supsis", "supsis stealer"],
    "swift": ["swift stealer"],
    "tea bot": ["tea bot", "teabot"],
    "thefuck": ["thefuck", "the fuck"],
    "tnight": ["tnight", "t-night"],
    "tohogun": ["tohogun", "toho gun"],
    "vbcStealer": ["vbcstealer", "vbc stealer"],
    "vengeanc": ["vengeance", "vengeanc stealer"],
    "vidar_v2": ["vidar v2"],
    "volodya": ["volodya", "volodya stealer"],
    "wacatac": ["wacatac"],
    "warzone": ["warzone", "warzone rat"],
    "whisker": ["whisker", "whisker stealer"],
    "winstealer": ["winstealer", "win stealer"],
    "worldclient": ["worldclient", "world client"],
    "xeno": ["xeno", "xeno stealer"],
    "zepeto": ["zepeto", "zepeto stealer"],
    "zephyr": ["zephyr", "zephyr stealer"],
    "zgrab": ["zgrab"],
}

KNOWN_EXTENSIONS = {
    ".txt", ".log", ".csv", ".json", ".html", ".htm", ".xml",
    ".sqlite", ".db", ".s3db", ".sqlite3", ".db3",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
    ".exe", ".dll", ".scr", ".bat", ".cmd", ".ps1",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".dat", ".bin", ".cfg", ".ini", ".conf", ".config",
    ".enc", ".encr", ".locked", ".crypted", ".crypto",
    ".key", ".pem", ".cer", ".crt", ".pfx",
    ".doc", ".docx", ".pdf", ".xlsx", ".xls",
    ".mp3", ".mp4", ".wav", ".avi",
    ".py", ".js", ".lua",
}


def read_file(path, max_size=500000):
    try:
        with open(path, "rb") as f:
            return f.read(max_size).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def try_extract_archive(path, dest_dir):
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(dest_dir)
                return True
    except Exception:
        pass
    return False


def detect_stealer_from_content(text, folder_path=""):
    all_lower = (text[:50000].lower() + " " + folder_path.lower())
    best_match = None
    best_len = 0
    for stype, keywords in STEALER_KEYWORDS.items():
        for kw in keywords:
            if kw in all_lower:
                if len(kw) > best_len:
                    best_match = stype
                    best_len = len(kw)
    return best_match


def detect_stealer_from_structure(root, dirs, files):
    dir_names = [d.lower() for d in dirs]
    file_names = [f.lower() for f in files]
    all_names = dir_names + file_names

    structure_hints = {
        "redline": ["profiles", "grabbed"],
        "raccoon": ["rac", "raccoon"],
        "vidar": ["vidar"],
        "phoenix": ["phoenix"],
        "atomic": ["atomic"],
        "meta": ["meta"],
        "rise": ["rise"],
        "lobshot": ["lob", "shot"],
        "danabot": ["dana"],
        "laplas": ["laplas"],
        "amadey": ["amadey"],
        "recordbreaker": ["record"],
        "zloader": ["zloader"],
        "smokeloader": ["smoke"],
        "medusa": ["medusa"],
        "lumma": ["lumma"],
        "stealc": ["stealc"],
        "vidar": ["vidar", "vidar_v2"],
        "privateloader": ["private", "private_loader"],
        "remcos": ["remcos"],
        "dcrat": ["dcrat", "dc rat"],
    }
    for stype, hints in structure_hints.items():
        for hint in hints:
            if hint in all_names:
                return stype
    return None


def parse_json_file(content):
    try:
        data = json.loads(content)
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def parse_csv_file(content):
    try:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        return rows
    except Exception:
        return None


def extract_passwords_from_json(data):
    lines = []
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        url = item.get("url", item.get("host", item.get("domain", item.get("login_url", ""))))
                        login = item.get("login", item.get("username", item.get("user", item.get("email", ""))))
                        password = item.get("password", item.get("pass", item.get("pwd", "")))
                        browser = item.get("browser", item.get("browserName", item.get("source", "")))
                        if login or password:
                            entry = f"{url} | {login}:{password}"
                            if browser:
                                entry = f"[{browser}] {entry}"
                            lines.append(entry)
            elif isinstance(val, dict):
                for item in extract_passwords_from_json(val):
                    lines.append(item)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                url = item.get("url", item.get("host", item.get("domain", "")))
                login = item.get("login", item.get("username", item.get("user", item.get("email", ""))))
                password = item.get("password", item.get("pass", item.get("pwd", "")))
                browser = item.get("browser", item.get("browserName", item.get("source", "")))
                if login or password:
                    entry = f"{url} | {login}:{password}"
                    if browser:
                        entry = f"[{browser}] {entry}"
                    lines.append(entry)
            elif isinstance(item, list) and len(item) >= 2:
                entry = f"{item[0]} | {item[1]}"
                if len(item) >= 3:
                    entry = f"{item[2]} {entry}"
                lines.append(entry)
    return "\n".join(lines[:1000])


def extract_cookies_from_json(data):
    lines = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                domain = item.get("domain", item.get("host", item.get("domainName", "")))
                name = item.get("name", item.get("cookieName", ""))
                value = item.get("value", item.get("cookieValue", ""))
                path = item.get("path", "")
                if domain or name:
                    lines.append(f"{domain}\tTRUE\t{path}\tTRUE\t\t{name}\t{value}")
            elif isinstance(item, list) and len(item) >= 2:
                lines.append(str(item))
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("cookieName", ""))
                        value = item.get("value", item.get("cookieValue", ""))
                        if name:
                            lines.append(f"{key}\tTRUE\t/\tTRUE\t\t{name}\t{value}")
    return "\n".join(lines[:1000])


def extract_tokens_from_json(data):
    tokens = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str) and len(item) > 20:
                tokens.append(item)
            elif isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, str) and len(v) > 20:
                        tokens.append(v)
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, str) and len(val) > 20:
                tokens.append(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and len(item) > 20:
                        tokens.append(item)
            elif isinstance(val, dict):
                tokens.extend(extract_tokens_from_json(val))
    return "\n".join(tokens[:200])


def extract_system_info_from_json(data):
    result = {}
    if isinstance(data, dict):
        field_map = {
            "ip": ["ip", "ipAddress", "ip_address", "externalip", "external_ip", "public_ip", "publicip"],
            "hwid": ["hwid", "hardwareId", "hardware_id", "machine_id", "machineid", "device_id", "deviceid"],
            "os": ["os", "operatingSystem", "operating_system", "osVersion", "windowsVersion", "system"],
            "computer_name": ["computerName", "computer_name", "pcName", "pc_name", "hostname", "hostName", "machineName"],
            "username": ["userName", "user_name", "username", "user", "accountName", "account_name", "login"],
            "cpu": ["cpu", "cpuInfo", "cpu_info", "processor"],
            "ram": ["ram", "ramAmount", "ram_amount", "memory"],
            "country": ["country", "countryCode", "country_code", "geo", "location"],
            "screen": ["screen", "screenResolution", "screen_resolution", "display"],
            "gpu": ["gpu", "gpuName", "gpu_name", "graphicsCard"],
            "arch": ["arch", "architecture", "systemArch"],
        }
        for field, keys in field_map.items():
            for key in keys:
                if key in data:
                    result[field] = str(data[key])
                    break
    return result


def extract_credit_cards_from_json(data):
    lines = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                cc = item.get("number", item.get("cardNumber", item.get("card_number", item.get("cc", ""))))
                exp = item.get("expiry", item.get("expiration", item.get("exp", "")))
                name = item.get("name", item.get("cardholderName", item.get("holder", "")))
                if cc:
                    lines.append(f"{cc} | {exp} | {name}")
    elif isinstance(data, dict):
        for key, val in data.items():
            if "card" in key.lower() or "cc" in key.lower():
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            cc = item.get("number", item.get("cardNumber", ""))
                            if cc:
                                lines.append(str(item))
    return "\n".join(lines[:100])


def extract_wallets_from_json(data):
    lines = []
    wallet_keywords = ["wallet", "crypto", "btc", "bitcoin", "eth", "ethereum", "monero", "xmr", "ltc", "litecoin", "dash", "ripple", "xrp"]
    if isinstance(data, dict):
        for key, val in data.items():
            if any(wk in key.lower() for wk in wallet_keywords):
                if isinstance(val, str) and val:
                    lines.append(f"{key}: {val}")
                elif isinstance(val, list):
                    for item in val:
                        lines.append(str(item))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, val in item.items():
                    if any(wk in key.lower() for wk in wallet_keywords):
                        if isinstance(val, str) and val:
                            lines.append(f"{key}: {val}")
    return "\n".join(lines[:100])


def parse_html_log(content):
    lines = []
    lines.extend(re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', content))
    passwords = re.findall(r'password["\s:=]+([^\s<"]+)', content, re.IGNORECASE)
    for p in passwords[:500]:
        lines.append(f"password: {p}")
    tokens = re.findall(r'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}', content)
    for t in tokens[:100]:
        lines.append(f"token: {t}")
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', content)
    for ip in ips[:50]:
        lines.append(f"ip: {ip}")
    return "\n".join(lines)


def parse_passwords_text(content):
    lines = []
    blocks = content.split("\n\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        url = ""
        login = ""
        password = ""
        browser = ""
        for line in block.split("\n"):
            line = line.strip()
            lower = line.lower()
            if lower.startswith("url:") or lower.startswith("site:") or lower.startswith("host:"):
                url = line.split(":", 1)[1].strip()
            elif lower.startswith("login:") or lower.startswith("username:") or lower.startswith("user:") or lower.startswith("email:"):
                login = line.split(":", 1)[1].strip()
            elif lower.startswith("password:") or lower.startswith("pass:") or lower.startswith("pwd:"):
                password = line.split(":", 1)[1].strip()
            elif lower.startswith("browser:") or lower.startswith("source:"):
                browser = line.split(":", 1)[1].strip()
        if login or password:
            entry = f"{url} | {login}:{password}"
            if browser:
                entry = f"[{browser}] {entry}"
            lines.append(entry)
    return "\n".join(lines[:1000])


def parse_system_info_text(content):
    result = {}
    patterns = {
        "ip": [r"[-*]\s*IP\s*[:=]", r"IP Address\s*[:=]", r"ExternalIP\s*[:=]", r"Public\s*IP\s*[:=]", r"IP\s+is\s+"],
        "hwid": [r"[-*]\s*HWID\s*[:=]", r"Hardware\s*ID\s*[:=]", r"Machine\s*ID\s*[:=]", r"Device\s*ID\s*[:=]", r"HWID\s+is\s+"],
        "os": [r"[-*]\s*OS\s*[:=]", r"Operating\s*System\s*[:=]", r"System\s*[:=]", r"Windows\s*[:=]"],
        "computer_name": [r"[-*]\s*Computer\s*Name\s*[:=]", r"PC\s*Name\s*[:=]", r"Hostname\s*[:=]", r"Machine\s*Name\s*[:=]", r"Computer\s+is\s+"],
        "username": [r"[-*]\s*UserName\s*[:=]", r"[-*]\s*Username\s*[:=]", r"User\s*[:=]", r"Account\s*[:=]", r"User\s+is\s+"],
        "cpu": [r"[-*]\s*CPU\s*[:=]", r"Processor\s*[:=]"],
        "ram": [r"[-*]\s*RAM\s*[:=]", r"Memory\s*[:=]"],
        "country": [r"[-*]\s*Country\s*[:=]", r"Location\s*[:=]", r"Geo\s*[:=]"],
        "screen": [r"[-*]\s*Screen\s*[:=]", r"Display\s*[:=]", r"Resolution\s*[:=]"],
        "gpu": [r"[-*]\s*GPU\s*[:=]", r"Graphics\s*[:=]", r"Video\s*[:=]"],
        "arch": [r"[-*]\s*Architecture\s*[:=]", r"Arch\s*[:=]", r"System\s*Arch\s*[:=]"],
        "user_agent": [r"[-*]\s*User\s*Agent\s*[:=]", r"UA\s*[:=]"],
    }
    for line in content.split("\n"):
        line = line.strip()
        for field, regexes in patterns.items():
            for regex in regexes:
                match = re.search(regex, line, re.IGNORECASE)
                if match:
                    value = line[match.end():].strip()
                    if value:
                        result[field] = value
                        break
    return result


def parse_cookie_text(content):
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    return "\n".join(lines[:1000])


def parse_token_text(content):
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) > 20:
            lines.append(line)
        elif ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2 and len(parts[1].strip()) > 20:
                lines.append(line)
    return "\n".join(lines[:200])


def parse_wallet_text(content):
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(kw in lower for kw in ["wallet", "btc", "bitcoin", "eth", "ethereum", "monero", "xmr", "ltc", "dash", "ripple", "xrp", "address", "seed", "mnemonic", "private key"]):
            lines.append(line)
    return "\n".join(lines[:100])


def parse_credit_card_text(content):
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        numbers = re.findall(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', line)
        if numbers:
            lines.append(line)
    return "\n".join(lines[:100])


def organize_cookies_from_text_files(cookie_files):
    organized = defaultdict(list)
    for browser_name, content in cookie_files:
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                domain = parts[0]
                name = parts[5]
                value = parts[6]
                organized[domain].append(f"{name}={value}")
            elif "=" in line:
                organized["unknown"].append(line)
    result = []
    for domain in sorted(organized.keys()):
        cookies = organized[domain]
        result.append(f"[{domain}] ({len(cookies)} cookies)")
        for c in cookies[:30]:
            result.append(f"  {c}")
        if len(cookies) > 30:
            result.append(f"  ... and {len(cookies) - 30} more")
    return "\n".join(result)


def parse_sqlite_db(path):
    passwords = []
    tokens = []
    cookies = []
    credit_cards = []
    wallets = []
    system_info = {}
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0].lower() for row in cursor.fetchall()]

        password_tables = ["logins", "passwords", "credentials", "accounts", "login_data", "password_data"]
        for table in password_tables:
            if table in tables:
                try:
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT 500")
                    cols = [d[0].lower() for d in cursor.description]
                    for row in cursor.fetchall():
                        entry = {}
                        for i, col in enumerate(cols):
                            entry[col] = str(row[i]) if row[i] else ""
                        url = entry.get("url", entry.get("host", entry.get("domain", "")))
                        login = entry.get("login", entry.get("username", entry.get("user", entry.get("email", ""))))
                        password = entry.get("password", entry.get("pass", entry.get("pwd", "")))
                        if login or password:
                            passwords.append(f"{url} | {login}:{password}")
                except Exception:
                    pass

        token_tables = ["tokens", "token_data", "auth_tokens"]
        for table in token_tables:
            if table in tables:
                try:
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT 200")
                    for row in cursor.fetchall():
                        for val in row:
                            if isinstance(val, str) and len(val) > 20:
                                tokens.append(val)
                except Exception:
                    pass

        cookie_tables = ["cookies", "cookie_data"]
        for table in cookie_tables:
            if table in tables:
                try:
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT 500")
                    for row in cursor.fetchall():
                        parts = [str(v) for v in row if v]
                        if len(parts) >= 2:
                            cookies.append("\t".join(parts))
                except Exception:
                    pass

        system_tables = ["system_info", "machine_info", "computer_info"]
        for table in system_tables:
            if table in tables:
                try:
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT 10")
                    cols = [d[0].lower() for d in cursor.description]
                    row = cursor.fetchone()
                    if row:
                        for i, col in enumerate(cols):
                            system_info[col] = str(row[i]) if row[i] else ""
                except Exception:
                    pass

        conn.close()
    except Exception:
        pass

    return {
        "passwords": "\n".join(passwords[:1000]),
        "tokens": "\n".join(tokens[:200]),
        "cookies": "\n".join(cookies[:1000]),
        "credit_cards": "\n".join(credit_cards[:100]),
        "wallets": "\n".join(wallets[:100]),
        "system_info": system_info,
    }


def classify_file_by_content(content, filename):
    lower = filename.lower()
    content_lower = content[:5000].lower() if content else ""

    if lower.endswith((".json",)):
        return "json"
    elif lower.endswith((".csv",)):
        return "csv"
    elif lower.endswith((".html", ".htm")):
        return "html"
    elif lower.endswith((".sqlite", ".db", ".s3db", ".sqlite3", ".db3")):
        return "sqlite"
    elif lower.endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        return "archive"

    if content:
        try:
            json.loads(content[:1000])
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

    if content_lower and ("url:" in content_lower or "login:" in content_lower or "password:" in content_lower or "site:" in content_lower):
        return "passwords"
    elif content_lower and ("domain" in content_lower and "cookie" in content_lower):
        return "cookies"
    elif content_lower and ("token" in content_lower and len(content) > 100):
        return "tokens"
    elif content_lower and ("ip:" in content_lower or "hwid:" in content_lower or "computer" in content_lower):
        return "system_info"
    elif content_lower and ("wallet" in content_lower or "btc" in content_lower or "ethereum" in content_lower):
        return "wallets"
    elif content_lower and ("card" in content_lower or "cvv" in content_lower or "expiry" in content_lower):
        return "credit_cards"
    elif content_lower and ("email" in content_lower and "pass" in content_lower):
        return "passwords"

    return "unknown"


def guess_category_from_path(rel_parts, filename):
    lower = filename.lower()
    parts_str = " ".join(rel_parts).lower()

    if any(x in lower for x in ["system_info", "systeminfo", "systeminfo.txt", "info.txt", "machine.txt", "pcinfo.txt"]):
        return "system_info"
    elif any(x in lower for x in ["passwords", "password", "pass.txt", "creds", "credentials", "logins", "accounts.txt"]):
        return "passwords"
    elif any(x in lower for x in ["cookies", "cookie", "cookie_list", "cookies.txt"]):
        return "cookies"
    elif any(x in lower for x in ["tokens", "token", "discord", "telegram", "session"]):
        return "tokens"
    elif any(x in lower for x in ["autofill", "form", "saved"]):
        return "autofill"
    elif any(x in lower for x in ["credit", "card", "cc", "payment", "billing"]):
        return "credit_cards"
    elif any(x in lower for x in ["wallet", "crypto", "btc", "seed", "mnemonic", "key"]):
        return "wallets"
    elif any(x in lower for x in ["brute", "combo", "wordlist"]):
        return "passwords"
    elif any(x in lower for x in ["accounttoken", "account_token", "acctoken"]):
        return "tokens"
    elif any(x in lower for x in ["soft", "installed", "programs"]):
        return "system_info"

    if "password" in parts_str or "login" in parts_str or "cred" in parts_str:
        return "passwords"
    elif "cookie" in parts_str:
        return "cookies"
    elif "token" in parts_str:
        return "tokens"
    elif "wallet" in parts_str or "crypto" in parts_str:
        return "wallets"
    elif "card" in parts_str or "credit" in parts_str:
        return "credit_cards"

    if lower.endswith((".txt", ".log", ".csv")):
        return "raw_text"

    return "unknown"


def parse_folder(folder_path):
    all_text = ""
    system_info_raw = ""
    passwords_raw = ""
    cookie_files = []
    tokens_raw = ""
    credit_cards_raw = ""
    wallets_raw = ""
    autofill_raw = ""
    json_data = []
    sqlite_files = []
    html_content = ""
    raw_texts = []

    temp_dir = None

    for root, dirs, files in os.walk(folder_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            fname_lower = fname.lower()
            rel_path = os.path.relpath(fpath, folder_path).lower().replace("/", "\\")
            rel_parts = rel_path.split("\\")

            if fname_lower.endswith((".zip",)):
                if temp_dir is None:
                    temp_dir = tempfile.mkdtemp(prefix="trackin_")
                extract_dir = os.path.join(temp_dir, fname)
                if try_extract_archive(fpath, extract_dir):
                    for ext_root, ext_dirs, ext_files in os.walk(extract_dir):
                        for ext_fname in ext_files:
                            ext_fpath = os.path.join(ext_root, ext_fname)
                            ext_fname_lower = ext_fname.lower()
                            ext_rel = os.path.relpath(ext_fpath, extract_dir).lower().replace("/", "\\")
                            ext_rel_parts = ext_rel.split("\\")
                            ext_content = read_file(ext_fpath)
                            if ext_content:
                                all_text += ext_content + "\n"
                                cat = guess_category_from_path(ext_rel_parts, ext_fname)
                                if cat == "system_info":
                                    system_info_raw += ext_content + "\n"
                                elif cat == "passwords":
                                    passwords_raw += ext_content + "\n"
                                elif cat == "cookies":
                                    browser_name = ext_rel_parts[0] if ext_rel_parts[0] != "cookies" else "Browser"
                                    cookie_files.append((browser_name, ext_content))
                                elif cat == "tokens":
                                    tokens_raw += ext_content + "\n"
                                elif cat == "credit_cards":
                                    credit_cards_raw += ext_content + "\n"
                                elif cat == "wallets":
                                    wallets_raw += ext_content + "\n"
                                elif cat == "autofill":
                                    autofill_raw += ext_content + "\n"
                                elif ext_fname_lower.endswith((".json",)):
                                    json_data.append((ext_rel_parts, ext_fname, ext_content))
                                elif ext_fname_lower.endswith((".sqlite", ".db", ".s3db", ".sqlite3")):
                                    sqlite_files.append(ext_fpath)
                    continue

            content = read_file(fpath)
            if not content:
                continue
            all_text += content + "\n"

            if fname_lower.endswith((".sqlite", ".db", ".s3db", ".sqlite3", ".db3")):
                sqlite_files.append(fpath)
                continue

            if fname_lower.endswith((".json",)):
                json_data.append((rel_parts, fname, content))
                continue

            if fname_lower.endswith((".html", ".htm")):
                html_content += content + "\n"
                continue

            cat = guess_category_from_path(rel_parts, fname)
            if cat == "system_info":
                system_info_raw += content + "\n"
            elif cat == "passwords":
                passwords_raw += content + "\n"
            elif cat == "cookies":
                browser_name = rel_parts[0] if rel_parts[0] != "cookies" else "Browser"
                if len(rel_parts) > 2:
                    browser_name = rel_parts[-2] if rel_parts[-2] != "cookies" else rel_parts[0]
                cookie_files.append((browser_name, content))
            elif cat == "tokens":
                tokens_raw += content + "\n"
            elif cat == "credit_cards":
                credit_cards_raw += content + "\n"
            elif cat == "wallets":
                wallets_raw += content + "\n"
            elif cat == "autofill":
                autofill_raw += content + "\n"
            elif cat == "raw_text":
                raw_texts.append(content)

    if temp_dir:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    if not all_text.strip() and not json_data and not sqlite_files:
        return None

    all_lower = all_text.lower()[:50000]
    stealer_type = detect_stealer_from_content(all_text, folder_path)
    if not stealer_type:
        stealer_type = detect_stealer_from_structure(folder_path, [], os.listdir(folder_path))

    final_system_info = {}
    if system_info_raw.strip():
        final_system_info = parse_system_info_text(system_info_raw)

    final_passwords_parts = []
    final_cookies_parts = []
    final_tokens_parts = []
    final_credit_cards_parts = []
    final_wallets_parts = []

    for rel_parts, fname, content in json_data:
        cat = guess_category_from_path(rel_parts, fname)
        data = parse_json_file(content)
        if not data:
            continue
        if cat == "passwords" or cat == "raw_text" or cat == "unknown":
            pw = extract_passwords_from_json(data)
            if pw:
                final_passwords_parts.append(pw)
            cc = extract_credit_cards_from_json(data)
            if cc:
                final_credit_cards_parts.append(cc)
            wc = extract_wallets_from_json(data)
            if wc:
                final_wallets_parts.append(wc)
            tk = extract_tokens_from_json(data)
            if tk:
                final_tokens_parts.append(tk)
            si = extract_system_info_from_json(data)
            if si:
                final_system_info.update(si)
            ck = extract_cookies_from_json(data)
            if ck:
                final_cookies_parts.append(ck)
        elif cat == "cookies":
            ck = extract_cookies_from_json(data)
            if ck:
                final_cookies_parts.append(ck)
        elif cat == "tokens":
            tk = extract_tokens_from_json(data)
            if tk:
                final_tokens_parts.append(tk)
        elif cat == "wallets":
            wc = extract_wallets_from_json(data)
            if wc:
                final_wallets_parts.append(wc)
        elif cat == "credit_cards":
            cc = extract_credit_cards_from_json(data)
            if cc:
                final_credit_cards_parts.append(cc)

    for db_path in sqlite_files:
        db_data = parse_sqlite_db(db_path)
        if db_data["passwords"]:
            final_passwords_parts.append(db_data["passwords"])
        if db_data["tokens"]:
            final_tokens_parts.append(db_data["tokens"])
        if db_data["cookies"]:
            final_cookies_parts.append(db_data["cookies"])
        if db_data["credit_cards"]:
            final_credit_cards_parts.append(db_data["credit_cards"])
        if db_data["wallets"]:
            final_wallets_parts.append(db_data["wallets"])
        if db_data["system_info"]:
            final_system_info.update(db_data["system_info"])

    if html_content.strip():
        parsed_html = parse_html_log(html_content)
        if parsed_html:
            final_tokens_parts.append(parsed_html)

    if passwords_raw.strip():
        final_passwords_parts.append(parse_passwords_text(passwords_raw))

    for browser_name, content in cookie_files:
        parsed = organize_cookies_from_text_files([(browser_name, content)])
        if parsed:
            final_cookies_parts.append(parsed)

    if tokens_raw.strip():
        final_tokens_parts.append(parse_token_text(tokens_raw))

    if autofill_raw.strip():
        final_passwords_parts.append("[Autofill]\n" + parse_passwords_text(autofill_raw))

    if credit_cards_raw.strip():
        final_credit_cards_parts.append(parse_credit_card_text(credit_cards_raw))

    if wallets_raw.strip():
        final_wallets_parts.append(parse_wallet_text(wallets_raw))

    for text in raw_texts:
        for stype, keywords in STEALER_KEYWORDS.items():
            for kw in keywords:
                if kw in text.lower():
                    if not stealer_type:
                        stealer_type = stype
                    break

    cookies_final = "\n\n".join(final_cookies_parts)
    passwords_final = "\n".join(final_passwords_parts)
    tokens_final = "\n".join(final_tokens_parts)
    credit_cards_final = "\n".join(final_credit_cards_parts)
    wallets_final = "\n".join(final_wallets_parts)

    hwid = final_system_info.get("hwid", "")
    ip = final_system_info.get("ip", "")
    computer_name = final_system_info.get("computer_name", "")
    os_info = final_system_info.get("os", "")
    username = final_system_info.get("username", "")
    country = final_system_info.get("country", "")

    if not hwid:
        hwid_match = re.search(r'(?:HWID|Hardware\s*ID|Machine\s*ID|Device\s*ID)\s*[:=]\s*(\S+)', all_text[:30000], re.IGNORECASE)
        if hwid_match:
            hwid = hwid_match.group(1)
    if not ip:
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', all_text[:30000])
        if ip_match:
            ip = ip_match.group(0)
    if not computer_name:
        name_match = re.search(r'(?:Computer\s*Name|PC\s*Name|Hostname)\s*[:=]\s*(\S+)', all_text[:30000], re.IGNORECASE)
        if name_match:
            computer_name = name_match.group(1)

    if not computer_name and username:
        computer_name = username

    return {
        "filename": os.path.basename(folder_path),
        "hwid": hwid,
        "ip": ip,
        "computer_name": computer_name,
        "os": os_info,
        "stealer_type": stealer_type,
        "cookies": cookies_final,
        "passwords": passwords_final,
        "tokens": tokens_final,
        "credit_cards": credit_cards_final,
        "wallets": wallets_final,
        "raw_text": all_text[:50000],
    }


def scan_folders(root_path):
    folders = []
    seen = set()

    if zipfile.is_zipfile(root_path):
        temp_dir = tempfile.mkdtemp(prefix="trackin_root_")
        if try_extract_archive(root_path, temp_dir):
            root_path = temp_dir
        else:
            return []

    for entry in os.listdir(root_path):
        full = os.path.join(root_path, entry)
        if os.path.isdir(full):
            real = os.path.realpath(full)
            if real not in seen:
                seen.add(real)
                folders.append(full)
    return folders


def parse_folder_chunk(folders):
    results = []
    for folder in folders:
        try:
            data = parse_folder(folder)
            if data:
                results.append(data)
        except Exception as e:
            pass
    return results


def init_db_fast():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=OFF")
    c.execute("PRAGMA cache_size=-500000")
    c.execute("PRAGMA temp_store=MEMORY")
    c.execute("PRAGMA page_size=65536")
    c.execute("PRAGMA mmap_size=268435456")
    c.execute("""
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
    c.execute("CREATE INDEX IF NOT EXISTS idx_ip ON logs(ip)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_hwid ON logs(hwid)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_computer_name ON logs(computer_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_stealer_type ON logs(stealer_type)")
    conn.commit()
    conn.close()


def batch_insert(rows):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=OFF")
    c.execute("PRAGMA cache_size=-500000")
    c.execute("PRAGMA mmap_size=268435456")
    c.execute("PRAGMA temp_store=MEMORY")

    batch_size = 10000
    total = len(rows)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = rows[i:i+batch_size]
        c.executemany("""
            INSERT INTO logs (filename, hwid, ip, computer_name, os, stealer_type, cookies, passwords, tokens, credit_cards, wallets, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(r["filename"], r["hwid"], r["ip"], r["computer_name"], r["os"], r["stealer_type"],
               r["cookies"], r["passwords"], r["tokens"], r["credit_cards"], r["wallets"], r["raw_text"]) for r in batch])
        conn.commit()
        inserted += len(batch)
        pct = inserted * 100 // total
        print(f"\r  [{pct:3d}%] {inserted}/{total}", end="", flush=True)

    print()
    conn.close()
    return inserted


def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path_to_logs_folder_or_zip>")
        sys.exit(1)

    folder = sys.argv[1]
    if not os.path.exists(folder):
        print(f"Error: {folder} does not exist")
        sys.exit(1)

    if os.path.isfile(folder) and folder.lower().endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        temp_dir = tempfile.mkdtemp(prefix="trackin_extract_")
        print(f"Extracting archive to {temp_dir}...")
        if try_extract_archive(folder, temp_dir):
            folder = temp_dir
        else:
            print(f"Error: Could not extract {folder}")
            sys.exit(1)
    elif not os.path.isdir(folder):
        print(f"Error: {folder} is not a valid directory or archive")
        sys.exit(1)

    cores = cpu_count()
    t0 = time.perf_counter()

    print(f"[1/4] Init DB...", flush=True)
    init_db_fast()

    print(f"[2/4] Scanning folders...", flush=True)
    folders = scan_folders(folder)
    total_folders = len(folders)
    print(f"  {total_folders} machine folders found", flush=True)

    if total_folders == 0:
        print("No folders found. Trying to parse as single log...")
        data = parse_folder(folder)
        if data:
            print("  Found single log, inserting...")
            init_db_fast()
            batch_insert([data])
            print("Done!")
        else:
            print("  No parseable data found.")
        return

    print(f"[3/4] Parsing ({cores} cores)...", flush=True)
    t1 = time.perf_counter()

    chunk_size = max(10, total_folders // (cores * 2))
    chunks = [folders[i:i+chunk_size] for i in range(0, total_folders, chunk_size)]

    results = []
    done = 0
    with ProcessPoolExecutor(max_workers=cores) as executor:
        futures = [executor.submit(parse_folder_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            r = future.result()
            results.extend(r)
            done += 1
            pct = done * 100 // len(futures)
            print(f"\r  [{pct:3d}%] {len(results)} machines parsed", end="", flush=True)

    print()
    t2 = time.perf_counter()
    if t2 - t1 > 0:
        print(f"  Parsed in {t2-t1:.1f}s ({len(results)/(t2-t1):.0f}/sec)", flush=True)
    else:
        print(f"  Parsed {len(results)} machines", flush=True)

    print(f"[4/4] Inserting {len(results)}...", flush=True)
    inserted = batch_insert(results)

    t3 = time.perf_counter()
    total_time = t3 - t0
    if total_time > 0:
        print(f"\nDone: {total_time:.1f}s | {inserted} logs | {inserted/total_time:.0f} logs/sec", flush=True)
    else:
        print(f"\nDone: {inserted} logs inserted", flush=True)


if __name__ == "__main__":
    main()
