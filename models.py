import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "database.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                dob TEXT,
                summary TEXT,
                skills TEXT,
                experience TEXT,
                education TEXT,
                certifications TEXT,
                languages TEXT,
                password TEXT,
                download_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS share_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id TEXT NOT NULL,
                method TEXT NOT NULL,
                recipient TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                whatsapp_sent INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id TEXT,
                action TEXT NOT NULL,
                detail TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feature_flags (
                key TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1
            );

            INSERT OR IGNORE INTO feature_flags VALUES ('download', 1);
            INSERT OR IGNORE INTO feature_flags VALUES ('print', 1);
            INSERT OR IGNORE INTO feature_flags VALUES ('email', 0);
            INSERT OR IGNORE INTO feature_flags VALUES ('whatsapp', 1);
            INSERT OR IGNORE INTO feature_flags VALUES ('password_protection', 1);
        """)
        conn.commit()


def get_flags(conn):
    rows = conn.execute("SELECT key, enabled FROM feature_flags").fetchall()
    return {r["key"]: bool(r["enabled"]) for r in rows}


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for field in ("skills", "experience", "education", "certifications", "languages"):
        try:
            d[field] = json.loads(d[field]) if d.get(field) else []
        except Exception:
            d[field] = []
    return d
