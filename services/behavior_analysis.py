"""
behavior_analysis.py - User Behavioral Profiling
AI-Based Online Payment Fraud Detection System
"""

import os
import sys
import sqlite3
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import ActiveConfig


# ── Constants ─────────────────────────────────
NIGHT_HOURS = set(range(22, 24)) | set(range(0, 6))   # 10 PM – 6 AM


def get_user_profile(user_id: int) -> dict:
    """
    Build a behavioural profile from the user's transaction history.
    Returns empty profile if there are fewer than 3 historical transactions.
    """
    db_path = ActiveConfig.DATABASE_PATH
    profile = {
        "avg_amount": None,
        "std_amount": None,
        "min_amount": None,
        "max_amount": None,
        "typical_hours": [],
        "typical_locations": [],
        "typical_types": [],
        "typical_devices": [],
        "total_transactions": 0,
    }

    if not os.path.exists(db_path):
        return profile

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT amount, transaction_hour, location, transaction_type, device_type
            FROM transactions
            WHERE user_id = ? AND prediction != 'Error'
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if len(rows) < 3:
        return profile

    amounts = [r[0] for r in rows]
    hours   = [r[1] for r in rows if r[1] is not None]
    locs    = [r[2] for r in rows if r[2]]
    types   = [r[3] for r in rows if r[3]]
    devices = [r[4] for r in rows if r[4]]

    profile.update({
        "avg_amount":        round(float(np.mean(amounts)), 2),
        "std_amount":        round(float(np.std(amounts)), 2),
        "min_amount":        round(float(np.min(amounts)), 2),
        "max_amount":        round(float(np.max(amounts)), 2),
        "typical_hours":     list(set(hours)),
        "typical_locations": _top_n(locs, 3),
        "typical_types":     _top_n(types, 3),
        "typical_devices":   _top_n(devices, 2),
        "total_transactions": len(rows),
    })
    return profile


def _top_n(lst: list, n: int) -> list:
    from collections import Counter
    return [item for item, _ in Counter(lst).most_common(n)]


def analyze_behavior(
    user_id: int,
    amount: float,
    transaction_hour: int,
    location: str,
    transaction_type: str,
    device_type: str,
    new_device: int,
) -> dict:
    """
    Compare the current transaction against the user's historical profile.

    Returns a dict with:
        behavior_score   - 0–100 (higher = more anomalous)
        anomalies        - list of detected behavioural issues
        profile_exists   - whether a profile was available
    """
    profile = get_user_profile(user_id)
    anomalies = []

    if not profile["avg_amount"]:
        # No history yet – neutral score
        return {
            "behavior_score": 20,
            "anomalies": ["No historical profile available"],
            "profile_exists": False,
            "profile": profile,
        }

    score = 0

    # 1. Amount anomaly
    avg = profile["avg_amount"]
    std = max(profile["std_amount"], avg * 0.1)  # avoid zero std
    z_score = abs(amount - avg) / std

    if z_score > 4:
        score += 35
        anomalies.append(f"Extremely high transaction amount (₹{amount:,.0f} vs avg ₹{avg:,.0f})")
    elif z_score > 2.5:
        score += 20
        anomalies.append(f"Unusually high transaction amount (₹{amount:,.0f} vs avg ₹{avg:,.0f})")
    elif z_score > 1.5:
        score += 10
        anomalies.append(f"Slightly above typical amount (₹{amount:,.0f})")

    # 2. Time anomaly
    is_night = transaction_hour in NIGHT_HOURS
    if is_night:
        night_tx_pct = sum(1 for h in profile["typical_hours"] if h in NIGHT_HOURS) / max(len(profile["typical_hours"]), 1)
        if night_tx_pct < 0.1:
            score += 20
            anomalies.append(f"Unusual transaction time ({transaction_hour}:00 – typically transacts during day)")

    # 3. Location anomaly
    if profile["typical_locations"] and location not in profile["typical_locations"]:
        score += 15
        anomalies.append(f"Unusual location: {location} (typical: {', '.join(profile['typical_locations'])})")

    # 4. New device
    if new_device:
        score += 15
        anomalies.append("Transaction from a new/unrecognised device")

    # 5. Transaction type anomaly
    if profile["typical_types"] and transaction_type not in profile["typical_types"]:
        score += 10
        anomalies.append(f"Unusual transaction type: {transaction_type}")

    score = min(score, 100)

    return {
        "behavior_score": score,
        "anomalies":      anomalies,
        "profile_exists": True,
        "profile":        profile,
    }
