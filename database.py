import sqlite3

conn = sqlite3.connect("conversation.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE history ADD COLUMN person TEXT")
    print("Person column added.")
except Exception as e:
    print(e)

conn.commit()
conn.close()