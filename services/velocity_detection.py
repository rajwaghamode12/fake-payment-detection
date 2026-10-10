"""
velocity_detection.py - Transaction Velocity Analysis
AI-Based Online Payment Fraud Detection System
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import ActiveConfig


def get_velocity(user_id: int, window_minutes: int | None = None) -> dict:
    """
    Count how many transactions the user submitted in the last N minutes.

    Returns a velocity dict with:
        count           - number of recent transactions
        window_minutes  - window used
        velocity_score  - 0–100 risk contribution
        risk_label      - LOW / MEDIUM / HIGH
        is_high_velocity - bool
    """
    window = window_minutes or ActiveConfig.VELOCITY_WINDOW_MINUTES
    cutoff = (datetime.utcnow() - timedelta(minutes=window)).isoformat()

    db_path = ActiveConfig.DATABASE_PATH
    count = 0

    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM transactions
                WHERE user_id = ? AND created_at >= ?
                """,
                (user_id, cutoff),
            ).fetchone()
            count = row[0] if row else 0
        finally:
            conn.close()

    lo = ActiveConfig.VELOCITY_THRESHOLD_LOW
    hi = ActiveConfig.VELOCITY_THRESHOLD_HIGH

    if count <= lo:
        velocity_score = 0
        risk_label = "LOW"
        is_high = False
    elif count <= hi:
        # Linear scale between lo and hi → 20–60
        velocity_score = int(20 + (count - lo) / (hi - lo) * 40)
        risk_label = "MEDIUM"
        is_high = False
    else:
        # Beyond hi → caps at 100
        velocity_score = min(100, 60 + (count - hi) * 4)
        risk_label = "HIGH"
        is_high = True

    return {
        "count":            count,
        "window_minutes":   window,
        "velocity_score":   velocity_score,
        "risk_label":       risk_label,
        "is_high_velocity": is_high,
    }
