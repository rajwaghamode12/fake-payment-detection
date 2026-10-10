"""
config.py - Application Configuration
AI-Based Online Payment Fraud Detection System
"""

import os
from datetime import timedelta

# ─────────────────────────────────────────────
# Base Directory
# ─────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""

    # ── Security ──────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production-2024"
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # ── Database ──────────────────────────────
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "database.db")

    # ── ML Model Paths ────────────────────────
    MODEL_DIR = os.path.join(BASE_DIR, "model")
    MODEL_PATH = os.path.join(MODEL_DIR, "fraud_model.pkl")
    PREPROCESSOR_PATH = os.path.join(MODEL_DIR, "preprocessor.pkl")
    MODEL_PERFORMANCE_PATH = os.path.join(MODEL_DIR, "model_performance.json")
    MODEL_BACKUP_PATH = os.path.join(MODEL_DIR, "fraud_model_backup.pkl")

    # ── Dataset ───────────────────────────────
    DATASET_PATH = os.path.join(BASE_DIR, "dataset", "payment_fraud.csv")

    # ── Reports ───────────────────────────────
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")

    # ── Risk Engine Thresholds ────────────────
    RISK_LOW_MAX = 25
    RISK_MEDIUM_MAX = 50
    RISK_HIGH_MAX = 75
    # > 75 = CRITICAL

    # ── Velocity Detection ────────────────────
    VELOCITY_WINDOW_MINUTES = 60
    VELOCITY_THRESHOLD_LOW = 5       # per hour – normal
    VELOCITY_THRESHOLD_HIGH = 10     # per hour – suspicious

    # ── Retraining ────────────────────────────
    MIN_FEEDBACK_FOR_RETRAIN = 10    # minimum feedback records before retraining
    RETRAIN_MIN_F1 = 0.70            # new model must beat this F1 to replace old

    # ── Admin ─────────────────────────────────
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL") or "admin@frauddetect.demo"
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "Admin@123"

    # ── App ───────────────────────────────────
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = False  # Railway terminates TLS at proxy level


class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "test_database.db")


# ── Active Config ─────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

_env = os.environ.get("FLASK_ENV") or os.environ.get("RAILWAY_ENVIRONMENT") or "development"
ActiveConfig = config_map.get(_env, DevelopmentConfig)

