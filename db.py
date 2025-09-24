import sqlite3

DB_NAME = "conversations.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        role TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                   (user_id, role, content))
    conn.commit()
    conn.close()

def get_last_messages(user_id, limit=20):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                   (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
