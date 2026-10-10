"""
fraud_prediction.py - Core Prediction Pipeline
AI-Based Online Payment Fraud Detection System
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import ActiveConfig
from services.anomaly_detection import compute_anomaly_score
from services.risk_engine import compute_risk_score, explain_risk

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

_model       = None
_preprocessor = None


def _load_artefacts():
    global _model, _preprocessor
    if _model is None and os.path.exists(ActiveConfig.MODEL_PATH):
        _model = joblib.load(ActiveConfig.MODEL_PATH)
    if _preprocessor is None and os.path.exists(ActiveConfig.PREPROCESSOR_PATH):
        _preprocessor = joblib.load(ActiveConfig.PREPROCESSOR_PATH)


def reload_model():
    """Force reload (call after retraining)."""
    global _model, _preprocessor
    _model = None
    _preprocessor = None
    _load_artefacts()


def predict(
    amount: float,
    transaction_type: str,
    transaction_hour: int,
    sender_balance: float,
    receiver_balance: float,
    location: str,
    device_type: str,
    previous_transaction_count: int,
    new_device: int,
    unusual_location: int,
    transactions_last_hour: int,
    velocity_score: float,
    behavior_score: float,
    behavior_result: dict,
    velocity_result: dict,
    day_of_week: int = 0,
) -> dict:
    """
    Run the complete prediction pipeline for one transaction.

    Returns a comprehensive result dict.
    """
    _load_artefacts()

    if _model is None or _preprocessor is None:
        return {
            "error": "Model not loaded. Please run model/train_model.py first.",
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "prediction": "Error",
        }

    # ── Build feature row ──────────────────────
    amount_to_balance_ratio = amount / max(sender_balance, 1)
    log_amount = np.log1p(amount)
    balance_diff = sender_balance - receiver_balance
    is_night = 1 if transaction_hour >= 22 or transaction_hour <= 5 else 0
    is_weekend = 1 if day_of_week >= 5 else 0

    row = {
        "amount":                    amount,
        "sender_balance":            sender_balance,
        "receiver_balance":          receiver_balance,
        "previous_transaction_count": previous_transaction_count,
        "transactions_last_hour":    transactions_last_hour,
        "amount_to_balance_ratio":   amount_to_balance_ratio,
        "log_amount":                log_amount,
        "balance_diff":              balance_diff,
        "transaction_hour":          transaction_hour,
        "day_of_week":               day_of_week,
        "new_device":                new_device,
        "unusual_location":          unusual_location,
        "is_night":                  is_night,
        "is_weekend":                is_weekend,
        "transaction_type":          transaction_type,
        "location":                  location,
        "device_type":               device_type,
    }

    df = pd.DataFrame([row])
    X_proc = _preprocessor.transform(df[NUMERIC_FEATURES + CATEGORICAL_FEATURES])

    # ── ML Prediction ──────────────────────────
    fraud_probability = float(_model.predict_proba(X_proc)[0][1])

    # ── Anomaly Score ──────────────────────────
    anomaly_result = compute_anomaly_score(X_proc[0])
    anomaly_score  = anomaly_result["anomaly_score"]

    # ── Risk Score ────────────────────────────
    risk_result = compute_risk_score(
        fraud_probability=fraud_probability,
        anomaly_score=anomaly_score,
        behavior_score=behavior_score,
        velocity_score=velocity_score,
        new_device=new_device,
        unusual_location=unusual_location,
        amount=amount,
        sender_balance=sender_balance,
    )

    # ── Explainability ────────────────────────
    reasons = explain_risk(
        fraud_probability=fraud_probability,
        anomaly_result=anomaly_result,
        behavior_result=behavior_result,
        velocity_result=velocity_result,
        new_device=new_device,
        unusual_location=unusual_location,
        amount=amount,
        sender_balance=sender_balance,
    )

    return {
        "fraud_probability": round(fraud_probability, 4),
        "fraud_probability_pct": round(fraud_probability * 100, 1),
        "anomaly_score":     round(anomaly_score, 2),
        "is_anomaly":        anomaly_result["is_anomaly"],
        "risk_score":        risk_result["risk_score"],
        "risk_level":        risk_result["risk_level"],
        "prediction":        risk_result["prediction"],
        "recommended_action": risk_result["recommended_action"],
        "risk_breakdown":    risk_result["breakdown"],
        "reasons":           reasons,
        "behavior_score":    behavior_score,
        "velocity_score":    velocity_score,
    }
