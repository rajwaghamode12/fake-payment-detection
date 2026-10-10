"""
generate_data.py - Synthetic Dataset Generator
AI-Based Online Payment Fraud Detection System

Generates a clearly labeled SYNTHETIC/DEMO dataset.
No real financial information is used.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

# ── Reproducibility ───────────────────────────
np.random.seed(42)
random.seed(42)

# ── Constants ─────────────────────────────────
TRANSACTION_TYPES = ["UPI", "Card", "Bank Transfer", "Wallet", "E-commerce"]
LOCATIONS = [
    "Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad",
    "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
]
DEVICE_TYPES = ["Mobile", "Desktop", "Tablet", "Laptop"]

NUM_GENUINE = 4500
NUM_FRAUD = 500          # ~10% fraud rate → class imbalance for ML demo
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)


def random_datetime(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def random_business_hour() -> datetime:
    """Return a datetime within business hours (8 AM – 8 PM)."""
    dt = random_datetime(START_DATE, END_DATE)
    return dt.replace(hour=random.randint(8, 20), minute=random.randint(0, 59))


def random_night_hour() -> datetime:
    """Return a datetime in late-night hours (11 PM – 4 AM)."""
    dt = random_datetime(START_DATE, END_DATE)
    hour = random.choice([23, 0, 1, 2, 3, 4])
    return dt.replace(hour=hour, minute=random.randint(0, 59))


# ══════════════════════════════════════════════
# GENUINE TRANSACTIONS
# ══════════════════════════════════════════════
def generate_genuine(n: int) -> list[dict]:
    records = []
    for i in range(n):
        amount = round(np.random.lognormal(mean=7.0, sigma=0.8), 2)  # ₹100 – ₹10k typical
        amount = min(amount, 50000)
        tx_time = random_business_hour()
        sender_balance = round(amount + np.random.uniform(500, 100000), 2)
        receiver_balance = round(np.random.uniform(100, 50000), 2)
        records.append({
            "transaction_id": f"TX{10000 + i}",
            "amount": amount,
            "transaction_type": random.choice(TRANSACTION_TYPES),
            "transaction_hour": tx_time.hour,
            "day_of_week": tx_time.weekday(),
            "sender_balance": sender_balance,
            "receiver_balance": receiver_balance,
            "location": random.choices(LOCATIONS, weights=[20,18,15,12,10,8,7,4,3,3])[0],
            "device_type": random.choices(DEVICE_TYPES, weights=[45,30,10,15])[0],
            "previous_transaction_count": random.randint(5, 200),
            "new_device": 0,
            "unusual_location": 0,
            "transactions_last_hour": random.randint(1, 4),
            "amount_to_balance_ratio": round(amount / sender_balance, 4),
            "is_fraud": 0,
        })
    return records


# ══════════════════════════════════════════════
# FRAUD TRANSACTIONS  (synthetic patterns)
# ══════════════════════════════════════════════
def generate_fraud(n: int) -> list[dict]:
    records = []
    patterns = [
        "large_amount",
        "new_device_night",
        "unusual_location",
        "high_velocity",
        "behavioral_anomaly",
        "combo_risk",
    ]
    per_pattern = n // len(patterns)
    remainder = n % len(patterns)

    idx = 0
    for p_idx, pattern in enumerate(patterns):
        count = per_pattern + (1 if p_idx < remainder else 0)

        for _ in range(count):
            tx_time = random_night_hour() if "night" in pattern or pattern in ["combo_risk", "behavioral_anomaly"] else random_business_hour()
            base_amount = round(np.random.uniform(60000, 200000), 2)
            sender_balance = round(np.random.uniform(100, base_amount * 1.5), 2)
            receiver_balance = round(np.random.uniform(0, 5000), 2)

            if pattern == "large_amount":
                amount = round(np.random.uniform(80000, 200000), 2)
                new_device = random.choice([0, 1])
                unusual_location = random.choice([0, 1])
                velocity = random.randint(1, 4)

            elif pattern == "new_device_night":
                amount = round(np.random.uniform(5000, 40000), 2)
                new_device = 1
                unusual_location = 0
                velocity = random.randint(1, 5)
                tx_time = random_night_hour()

            elif pattern == "unusual_location":
                amount = round(np.random.uniform(10000, 60000), 2)
                new_device = random.choice([0, 1])
                unusual_location = 1
                velocity = random.randint(1, 5)

            elif pattern == "high_velocity":
                amount = round(np.random.uniform(500, 20000), 2)
                new_device = random.choice([0, 1])
                unusual_location = random.choice([0, 1])
                velocity = random.randint(12, 30)

            elif pattern == "behavioral_anomaly":
                amount = round(np.random.uniform(30000, 150000), 2)
                new_device = 1
                unusual_location = 1
                velocity = random.randint(5, 15)
                tx_time = random_night_hour()

            else:  # combo_risk
                amount = round(np.random.uniform(50000, 180000), 2)
                new_device = 1
                unusual_location = 1
                velocity = random.randint(10, 25)
                tx_time = random_night_hour()

            sender_balance = max(sender_balance, amount * 0.5)
            records.append({
                "transaction_id": f"TXF{20000 + idx}",
                "amount": amount,
                "transaction_type": random.choice(TRANSACTION_TYPES),
                "transaction_hour": tx_time.hour,
                "day_of_week": tx_time.weekday(),
                "sender_balance": round(sender_balance, 2),
                "receiver_balance": receiver_balance,
                "location": random.choice(LOCATIONS),
                "device_type": random.choices(DEVICE_TYPES, weights=[45,30,10,15])[0],
                "previous_transaction_count": random.randint(0, 30),
                "new_device": new_device,
                "unusual_location": unusual_location,
                "transactions_last_hour": velocity,
                "amount_to_balance_ratio": round(amount / sender_balance, 4),
                "is_fraud": 1,
            })
            idx += 1

    return records


# ══════════════════════════════════════════════
# MAIN – generate and save
# ══════════════════════════════════════════════
def generate_dataset(output_path: str | None = None) -> pd.DataFrame:
    print("Generating synthetic payment fraud dataset...")

    genuine = generate_genuine(NUM_GENUINE)
    fraud = generate_fraud(NUM_FRAUD)

    all_records = genuine + fraud
    df = pd.DataFrame(all_records)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle

    # Derived features
    df["log_amount"] = np.log1p(df["amount"])
    df["balance_diff"] = df["sender_balance"] - df["receiver_balance"]
    df["is_night"] = df["transaction_hour"].apply(lambda h: 1 if h >= 22 or h <= 5 else 0)
    df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)

    fraud_count = df["is_fraud"].sum()
    genuine_count = len(df) - fraud_count
    print(f"  Total records   : {len(df)}")
    print(f"  Genuine (0)     : {genuine_count}")
    print(f"  Fraud   (1)     : {fraud_count}")
    print(f"  Fraud rate      : {fraud_count/len(df)*100:.1f}%")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"  Saved to        : {output_path}")

    return df


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "payment_fraud.csv")
    generate_dataset(output_path=out)
    print("Dataset generation complete.")
