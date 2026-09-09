import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "trackin.db")
PART_SIZE = 50 * 1024 * 1024  # 50MB per part

def split_db():
    if not os.path.exists(DB_PATH):
        print("No trackin.db found")
        return

    size = os.path.getsize(DB_PATH)
    print(f"Database size: {size / (1024*1024):.1f} MB")

    with open(DB_PATH, "rb") as f:
        data = f.read()

    parts = []
    for i in range(0, len(data), PART_SIZE):
        chunk = data[i:i+PART_SIZE]
        suffix = chr(ord("a") + len(parts))
        part_name = f"trackin.db.part.{suffix}"
        with open(part_name, "wb") as pf:
            pf.write(chunk)
        parts.append(part_name)
        print(f"Created {part_name} ({len(chunk) / (1024*1024):.1f} MB)")

    print(f"\n{len(parts)} parts created.")
    print("Upload each part to Google Drive, get the file ID from the URL, then set GDRIVE_DB_PARTS in Railway to:")
    print(",".join(["YOUR_FILE_ID_HERE"] * len(parts)))

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    split_db()
