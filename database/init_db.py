"""
init_db.py - Database Initialiser
AI-Based Online Payment Fraud Detection System

Run directly to create tables and seed the admin account:
    python database/init_db.py
"""

import sqlite3
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.security import generate_password_hash
from database.models import ALL_TABLES
from config import ActiveConfig


# ── Connection helper ────────────────────────
def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or ActiveConfig.DATABASE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ── Create all tables ────────────────────────
def create_tables(conn: sqlite3.Connection) -> None:
    for ddl in ALL_TABLES:
        conn.execute(ddl)
    conn.commit()
    print("  Tables created (or already exist).")


# ── Seed admin account ───────────────────────
def seed_admin(conn: sqlite3.Connection) -> None:
    email = ActiveConfig.ADMIN_EMAIL
    password = ActiveConfig.ADMIN_PASSWORD

    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()

    if existing:
        print(f"  Admin account already exists: {email}")
        return

    conn.execute(
        """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, 'admin')
        """,
        ("Administrator", email, generate_password_hash(password)),
    )
    conn.commit()
    print(f"  Admin account created: {email} / {password}")


# ── Main ─────────────────────────────────────
def init_db(db_path: str | None = None) -> None:
    print("Initialising database...")
    conn = get_connection(db_path)
    try:
        create_tables(conn)
        seed_admin(conn)
        print("  Database ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
