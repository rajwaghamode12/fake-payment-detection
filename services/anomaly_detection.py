"""
anomaly_detection.py - Isolation Forest Anomaly Detection
AI-Based Online Payment Fraud Detection System
"""

import os
import sys
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import ActiveConfig

_iso_forest = None


def _load_iso_forest():
    global _iso_forest
    if _iso_forest is None:
        path = os.path.join(ActiveConfig.MODEL_DIR, "isolation_forest.pkl")
        if os.path.exists(path):
            _iso_forest = joblib.load(path)
    return _iso_forest


def compute_anomaly_score(X_processed: np.ndarray) -> dict:
    """
    Compute an anomaly score for a preprocessed feature vector.

    Returns:
        {
            "is_anomaly": bool,
            "anomaly_score": float (0–100, higher = more anomalous),
            "raw_score": float (Isolation Forest decision function)
        }
    """
    iso = _load_iso_forest()
    if iso is None:
        return {"is_anomaly": False, "anomaly_score": 0.0, "raw_score": 0.0}

    # decision_function: negative = anomaly, positive = normal
    raw = float(iso.decision_function(X_processed.reshape(1, -1))[0])
    prediction = iso.predict(X_processed.reshape(1, -1))[0]   # -1 = anomaly

    is_anomaly = (prediction == -1)

    # Normalise to 0–100 (anomaly score; higher = more suspicious)
    # Typical range of raw score: -0.3 (anomalous) to +0.3 (normal)
    clipped = np.clip(raw, -0.5, 0.5)
    anomaly_score = round((0.5 - clipped) / 1.0 * 100, 2)   # 0 = normal, 100 = extreme anomaly

    return {
        "is_anomaly":    is_anomaly,
        "anomaly_score": anomaly_score,
        "raw_score":     round(raw, 6),
    }
