"""
evaluate_model.py - Model Drift & Evaluation Utilities
AI-Based Online Payment Fraud Detection System
"""

import os
import sys
import json
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix
)
from config import ActiveConfig


# ── Feature lists (must match train_model.py) ─
NUMERIC_FEATURES = [
    "amount", "sender_balance", "receiver_balance",
    "previous_transaction_count", "transactions_last_hour",
    "amount_to_balance_ratio", "log_amount", "balance_diff",
    "transaction_hour", "day_of_week",
    "new_device", "unusual_location",
    "is_night", "is_weekend",
]
CATEGORICAL_FEATURES = ["transaction_type", "location", "device_type"]


def load_model():
    """Load the active fraud detection model."""
    if not os.path.exists(ActiveConfig.MODEL_PATH):
        return None
    return joblib.load(ActiveConfig.MODEL_PATH)


def load_preprocessor():
    """Load the fitted preprocessor."""
    if not os.path.exists(ActiveConfig.PREPROCESSOR_PATH):
        return None
    return joblib.load(ActiveConfig.PREPROCESSOR_PATH)


def load_performance() -> dict:
    """Load saved model performance metrics."""
    if not os.path.exists(ActiveConfig.MODEL_PERFORMANCE_PATH):
        return {}
    with open(ActiveConfig.MODEL_PERFORMANCE_PATH) as f:
        return json.load(f)


# ══════════════════════════════════════════════
# MODEL DRIFT DETECTION
# ══════════════════════════════════════════════
def detect_drift(recent_transactions: list[dict]) -> dict:
    """
    Compare recent transaction statistics against training baseline.
    Returns a drift report dict.
    """
    perf = load_performance()
    if not perf or not recent_transactions:
        return {"drift_detected": False, "reason": "Insufficient data"}

    model = load_model()
    preprocessor = load_preprocessor()
    if model is None or preprocessor is None:
        return {"drift_detected": False, "reason": "Model not loaded"}

    # Build a small DataFrame from recent transactions
    rows = []
    for tx in recent_transactions:
        rows.append({
            "amount":                    float(tx.get("amount", 0)),
            "sender_balance":            float(tx.get("sender_balance", 0)),
            "receiver_balance":          float(tx.get("receiver_balance", 0)),
            "previous_transaction_count": int(tx.get("previous_transaction_count", 0)),
            "transactions_last_hour":    int(tx.get("transactions_last_hour", 1)),
            "amount_to_balance_ratio":   float(tx.get("amount", 0)) / max(float(tx.get("sender_balance", 1)), 1),
            "log_amount":                np.log1p(float(tx.get("amount", 0))),
            "balance_diff":              float(tx.get("sender_balance", 0)) - float(tx.get("receiver_balance", 0)),
            "transaction_hour":          int(tx.get("transaction_hour", 12)),
            "day_of_week":               0,
            "new_device":                int(tx.get("new_device", 0)),
            "unusual_location":          int(tx.get("unusual_location", 0)),
            "is_night":                  1 if int(tx.get("transaction_hour", 12)) >= 22 or int(tx.get("transaction_hour", 12)) <= 5 else 0,
            "is_weekend":                0,
            "transaction_type":          tx.get("transaction_type", "UPI"),
            "location":                  tx.get("location", "Mumbai"),
            "device_type":               tx.get("device_type", "Mobile"),
        })

    df = pd.DataFrame(rows)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]

    try:
        X_proc = preprocessor.transform(X)
        preds = model.predict(X_proc)
        recent_fraud_rate = preds.mean()
    except Exception as e:
        return {"drift_detected": False, "reason": f"Transform error: {e}"}

    # Compare with training fraud rate
    baseline_fraud_rate = 0.10   # known from synthetic dataset (~10%)
    drift_threshold = 0.15        # >15% absolute change triggers alert

    drift_amount = abs(recent_fraud_rate - baseline_fraud_rate)
    drift_detected = drift_amount > drift_threshold

    # Feature distribution check: mean amount vs baseline
    recent_avg_amount = df["amount"].mean()
    baseline_avg_amount = 8000   # approximate from training data
    amount_drift = abs(recent_avg_amount - baseline_avg_amount) / baseline_avg_amount

    report = {
        "drift_detected":        drift_detected or amount_drift > 0.5,
        "recent_fraud_rate":     round(float(recent_fraud_rate), 4),
        "baseline_fraud_rate":   baseline_fraud_rate,
        "fraud_rate_change":     round(float(drift_amount), 4),
        "recent_avg_amount":     round(float(recent_avg_amount), 2),
        "baseline_avg_amount":   baseline_avg_amount,
        "amount_drift_pct":      round(float(amount_drift) * 100, 1),
        "sample_size":           len(recent_transactions),
        "recommendation":        "Consider retraining the model." if (drift_detected or amount_drift > 0.5) else "Model appears stable.",
    }
    return report


# ══════════════════════════════════════════════
# EVALUATE MODEL ON A LABELED DATASET
# ══════════════════════════════════════════════
def evaluate_on_dataset(df: pd.DataFrame) -> dict:
    """Evaluate the current model on a labelled DataFrame."""
    model = load_model()
    preprocessor = load_preprocessor()
    if model is None or preprocessor is None:
        return {}

    # Ensure derived features
    df = df.copy()
    df["log_amount"] = np.log1p(df["amount"])
    df["balance_diff"] = df["sender_balance"] - df["receiver_balance"]
    df["is_night"] = df["transaction_hour"].apply(lambda h: 1 if h >= 22 or h <= 5 else 0)
    df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)

    required = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["is_fraud"]
    for col in required:
        if col not in df.columns:
            return {"error": f"Missing column: {col}"}

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["is_fraud"]

    X_proc = preprocessor.transform(X)
    y_pred = model.predict(X_proc)
    y_prob = model.predict_proba(X_proc)[:, 1] if hasattr(model, "predict_proba") else y_pred

    return {
        "accuracy":  round(accuracy_score(y, y_pred), 4),
        "precision": round(precision_score(y, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y, y_pred, zero_division=0), 4),
        "f1_score":  round(f1_score(y, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y, y_prob), 4),
        "confusion_matrix": confusion_matrix(y, y_pred).tolist(),
        "sample_size": len(df),
    }
