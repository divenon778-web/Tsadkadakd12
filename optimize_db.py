import sqlite3, gzip, os

conn = sqlite3.connect("trackin.db")
c = conn.cursor()

c.execute("ATTACH DATABASE 'trackin_optimized.db' AS opt")
c.execute("""CREATE TABLE opt.logs AS 
    SELECT id, filename, hwid, ip, computer_name, os, stealer_type,
           SUBSTR(cookies, 1, 5000) as cookies,
           SUBSTR(passwords, 1, 5000) as passwords,
           SUBSTR(tokens, 1, 2000) as tokens,
           SUBSTR(credit_cards, 1, 1000) as credit_cards,
           SUBSTR(wallets, 1, 1000) as wallets,
           created_at
    FROM logs""")
c.execute("CREATE INDEX opt.idx_ip ON logs(ip)")
c.execute("CREATE INDEX opt.idx_hwid ON logs(hwid)")
c.execute("CREATE INDEX opt.idx_computer_name ON logs(computer_name)")
c.execute("CREATE INDEX opt.idx_stealer_type ON logs(stealer_type)")
conn.close()

conn2 = sqlite3.connect("trackin_optimized.db")
conn2.execute("VACUUM")
conn2.close()

size_orig = os.path.getsize("trackin.db")
size_opt = os.path.getsize("trackin_optimized.db")
print(f"Original: {size_orig/(1024*1024):.0f} MB")
print(f"Optimized: {size_opt/(1024*1024):.0f} MB")

with open("trackin_optimized.db", "rb") as f:
    data = f.read()
compressed = gzip.compress(data, compresslevel=9)
with open("trackin.db.gz", "wb") as f:
    f.write(compressed)
print(f"Compressed: {len(compressed)/(1024*1024):.0f} MB")
os.remove("trackin_optimized.db")
print("Done")
