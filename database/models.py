"""
models.py - Database Schema (raw SQLite via sqlite3)
AI-Based Online Payment Fraud Detection System
"""

# ── Table DDL Statements ──────────────────────

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'user',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id              TEXT    NOT NULL UNIQUE,
    user_id                     INTEGER NOT NULL,
    amount                      REAL    NOT NULL,
    transaction_type            TEXT    NOT NULL,
    transaction_time            TEXT    NOT NULL,
    transaction_hour            INTEGER,
    sender_balance              REAL,
    receiver_balance            REAL,
    location                    TEXT,
    device_type                 TEXT,
    previous_transaction_count  INTEGER DEFAULT 0,
    new_device                  INTEGER DEFAULT 0,
    unusual_location            INTEGER DEFAULT 0,
    velocity_score              REAL    DEFAULT 0,
    behavior_score              REAL    DEFAULT 0,
    anomaly_score               REAL    DEFAULT 0,
    fraud_probability           REAL    DEFAULT 0,
    risk_score                  REAL    DEFAULT 0,
    risk_level                  TEXT    DEFAULT 'LOW',
    prediction                  TEXT    DEFAULT 'Genuine',
    status                      TEXT    DEFAULT 'Pending',
    transactions_last_hour      INTEGER DEFAULT 1,
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_FEEDBACK = """
CREATE TABLE IF NOT EXISTS feedback (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id      TEXT    NOT NULL,
    model_prediction    TEXT    NOT NULL,
    admin_decision      TEXT    NOT NULL,
    notes               TEXT,
    reviewed_by         INTEGER,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    FOREIGN KEY (reviewed_by)   REFERENCES users(id)
);
"""

CREATE_MODEL_VERSIONS = """
CREATE TABLE IF NOT EXISTS model_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name  TEXT    NOT NULL,
    version     TEXT    NOT NULL,
    accuracy    REAL,
    precision   REAL,
    recall      REAL,
    f1_score    REAL,
    roc_auc     REAL,
    is_active   INTEGER DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  TEXT    NOT NULL,
    risk_level      TEXT    NOT NULL,
    risk_score      REAL    NOT NULL,
    message         TEXT,
    is_resolved     INTEGER DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);
"""

ALL_TABLES = [
    CREATE_USERS,
    CREATE_TRANSACTIONS,
    CREATE_FEEDBACK,
    CREATE_MODEL_VERSIONS,
    CREATE_ALERTS,
]
