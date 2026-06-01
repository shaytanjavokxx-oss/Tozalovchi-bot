import sqlite3
from datetime import datetime

DB = "majburiy.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        invited_by INTEGER DEFAULT 0,
        sana TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invited_id INTEGER,
        sana TEXT
    )''')
    conn.commit()
    conn.close()

def member_qoshish(user_id, username, first_name, invited_by=0):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR IGNORE INTO members (user_id, username, first_name, invited_by, sana)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, username or "", first_name or "", invited_by,
                   datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()

def invite_qoshish(inviter_id, invited_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM invites WHERE inviter_id=? AND invited_id=?", (inviter_id, invited_id))
    if not c.fetchone():
        c.execute("INSERT INTO invites (inviter_id, invited_id, sana) VALUES (?, ?, ?)",
                  (inviter_id, invited_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def invite_soni(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invites WHERE inviter_id=?", (user_id,))
    n = c.fetchone()[0]
    conn.close()
    return n

def top_inviters(limit=10):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT m.user_id, m.username, m.first_name, COUNT(i.id) as cnt
                 FROM members m
                 LEFT JOIN invites i ON m.user_id = i.inviter_id
                 GROUP BY m.user_id
                 ORDER BY cnt DESC
                 LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def jami_members():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    n = c.fetchone()[0]
    conn.close()
    return n

def barcha_members():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name FROM members")
    rows = c.fetchall()
    conn.close()
    return rows
