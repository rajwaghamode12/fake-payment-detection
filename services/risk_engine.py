"""
risk_engine.py - Dynamic Risk Scoring Engine
AI-Based Online Payment Fraud Detection System

Combines ML fraud probability + anomaly score + behavioural score
+ velocity + device + location into a single Risk Score (0–100).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import ActiveConfig


# ── Weights (must sum to ~1.0) ────────────────
WEIGHTS = {
    "ml_fraud_prob":   0.35,
    "anomaly_score":   0.20,
    "behavior_score":  0.20,
    "velocity_score":  0.10,
    "new_device":      0.08,
    "unusual_location":0.07,
}


def compute_risk_score(
    fraud_probability: float,       # 0.0 – 1.0
    anomaly_score: float,           # 0 – 100
    behavior_score: float,          # 0 – 100
    velocity_score: float,          # 0 – 100
    new_device: int,                # 0 or 1
    unusual_location: int,          # 0 or 1
    amount: float = 0.0,
    sender_balance: float = 1.0,
) -> dict:
    """
    Compute a composite risk score and return full breakdown.
    """

    # Normalise inputs to 0–100 scale
    ml_score       = fraud_probability * 100
    anomaly_norm   = anomaly_score          # already 0–100
    behavior_norm  = behavior_score         # already 0–100
    velocity_norm  = velocity_score         # already 0–100
    device_norm    = new_device * 100
    location_norm  = unusual_location * 100

    raw_score = (
        WEIGHTS["ml_fraud_prob"]    * ml_score      +
        WEIGHTS["anomaly_score"]    * anomaly_norm  +
        WEIGHTS["behavior_score"]   * behavior_norm +
        WEIGHTS["velocity_score"]   * velocity_norm +
        WEIGHTS["new_device"]       * device_norm   +
        WEIGHTS["unusual_location"] * location_norm
    )

    # Bonus for large amount relative to balance
    if sender_balance > 0:
        ratio = amount / sender_balance
        if ratio > 0.9:
            raw_score = min(100, raw_score + 10)
        elif ratio > 0.7:
            raw_score = min(100, raw_score + 5)

    risk_score = round(min(max(raw_score, 0), 100), 2)
    risk_level = _get_risk_level(risk_score)
    prediction = _get_prediction(risk_score, fraud_probability)
    action     = _get_action(risk_level)

    return {
        "risk_score":          risk_score,
        "risk_level":          risk_level,
        "prediction":          prediction,
        "recommended_action":  action,
        "breakdown": {
            "ml_contribution":        round(WEIGHTS["ml_fraud_prob"]     * ml_score, 2),
            "anomaly_contribution":   round(WEIGHTS["anomaly_score"]     * anomaly_norm, 2),
            "behavior_contribution":  round(WEIGHTS["behavior_score"]    * behavior_norm, 2),
            "velocity_contribution":  round(WEIGHTS["velocity_score"]    * velocity_norm, 2),
            "device_contribution":    round(WEIGHTS["new_device"]        * device_norm, 2),
            "location_contribution":  round(WEIGHTS["unusual_location"]  * location_norm, 2),
        },
    }


def _get_risk_level(score: float) -> str:
    if score <= ActiveConfig.RISK_LOW_MAX:
        return "LOW"
    elif score <= ActiveConfig.RISK_MEDIUM_MAX:
        return "MEDIUM"
    elif score <= ActiveConfig.RISK_HIGH_MAX:
        return "HIGH"
    else:
        return "CRITICAL"


def _get_prediction(score: float, fraud_prob: float) -> str:
    if score > ActiveConfig.RISK_HIGH_MAX or fraud_prob > 0.7:
        return "Fraud"
    elif score > ActiveConfig.RISK_LOW_MAX or fraud_prob > 0.35:
        return "Suspicious"
    else:
        return "Genuine"


def _get_action(risk_level: str) -> str:
    actions = {
        "LOW":      "Approve – Transaction appears consistent with normal behaviour.",
        "MEDIUM":   "Review – Send for additional verification before processing.",
        "HIGH":     "Alert – Flag for immediate admin review and hold transaction.",
        "CRITICAL": "Block – Immediate alert raised. Transaction blocked pending investigation.",
    }
    return actions.get(risk_level, "Review")


# ── XAI: Explain the top risk factors ─────────
def explain_risk(
    fraud_probability: float,
    anomaly_result: dict,
    behavior_result: dict,
    velocity_result: dict,
    new_device: int,
    unusual_location: int,
    amount: float,
    sender_balance: float,
    feature_importance: dict | None = None,
) -> list[str]:
    """
    Return a plain-language list of the main contributing risk factors,
    ordered from most to least impactful.
    """
    factors = []

    # Amount vs balance
    if sender_balance > 0 and amount / sender_balance > 0.8:
        factors.append(
            f"Transaction amount (₹{amount:,.0f}) is {amount/sender_balance*100:.0f}% of sender balance"
        )

    if fraud_probability > 0.7:
        factors.append(f"ML model assigned high fraud probability ({fraud_probability*100:.0f}%)")
    elif fraud_probability > 0.4:
        factors.append(f"ML model flagged moderate fraud risk ({fraud_probability*100:.0f}%)")

    if anomaly_result.get("is_anomaly"):
        factors.append("Transaction pattern is significantly different from normal transactions (Isolation Forest)")

    for anom in behavior_result.get("anomalies", []):
        factors.append(anom)

    if velocity_result.get("is_high_velocity"):
        factors.append(
            f"High transaction velocity: {velocity_result['count']} transactions "
            f"in the last {velocity_result['window_minutes']} minutes"
        )

    if new_device:
        factors.append("Transaction initiated from a new/unrecognised device")

    if unusual_location:
        factors.append("Transaction location differs from user's typical regions")

    # Fallback
    if not factors:
        factors.append("No significant risk factors detected")

    return factors[:8]   # cap at 8 for display clarity
