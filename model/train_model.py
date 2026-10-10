"""
train_model.py - ML Model Training Script
AI-Based Online Payment Fraud Detection System

Run from project root:
    python model/train_model.py

Trains: Logistic Regression, Decision Tree, Random Forest, XGBoost
Handles class imbalance with SMOTE + class_weight
Saves best model (Random Forest) + preprocessor + performance metrics
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

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, classification_report
)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("  XGBoost not installed - skipping XGBoost model.")

try:
    from imblearn.over_sampling import SMOTE
    from imblearn.pipeline import Pipeline as ImbPipeline
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    print("  imbalanced-learn not installed - using class_weight only.")

from dataset.generate_data import generate_dataset
from config import ActiveConfig


# -- Feature lists --
NUMERIC_FEATURES = [
    "amount", "sender_balance", "receiver_balance",
    "previous_transaction_count", "transactions_last_hour",
    "amount_to_balance_ratio", "log_amount", "balance_diff",
    "transaction_hour", "day_of_week",
    "new_device", "unusual_location",
    "is_night", "is_weekend",
]

CATEGORICAL_FEATURES = ["transaction_type", "location", "device_type"]

TARGET = "is_fraud"


# =============================================
# DATA LOADING & PREPROCESSING
# =============================================
def load_data() -> pd.DataFrame:
    path = ActiveConfig.DATASET_PATH
    if os.path.exists(path):
        print(f"  Loading dataset from {path}")
        df = pd.read_csv(path)
    else:
        print("  Dataset not found - generating synthetic data...")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df = generate_dataset(output_path=path)
    return df


def build_preprocessor() -> ColumnTransformer:
    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

    preprocessor = ColumnTransformer(transformers=[
        ("num", numeric_transformer, NUMERIC_FEATURES),
        ("cat", categorical_transformer, CATEGORICAL_FEATURES),
    ])
    return preprocessor


# =============================================
# MODEL EVALUATION HELPER
# =============================================
def evaluate_model(name: str, model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    acc   = accuracy_score(y_test, y_pred)
    prec  = precision_score(y_test, y_pred, zero_division=0)
    rec   = recall_score(y_test, y_pred, zero_division=0)
    f1    = f1_score(y_test, y_pred, zero_division=0)
    auc   = roc_auc_score(y_test, y_prob)
    cm    = confusion_matrix(y_test, y_pred).tolist()

    print(f"\n  -- {name} --")
    print(f"     Accuracy  : {acc:.4f}")
    print(f"     Precision : {prec:.4f}")
    print(f"     Recall    : {rec:.4f}")
    print(f"     F1 Score  : {f1:.4f}")
    print(f"     ROC-AUC   : {auc:.4f}")
    print(f"     Confusion Matrix:\n       {cm[0]}\n       {cm[1]}")

    return {
        "model_name": name,
        "accuracy":   round(acc, 4),
        "precision":  round(prec, 4),
        "recall":     round(rec, 4),
        "f1_score":   round(f1, 4),
        "roc_auc":    round(auc, 4),
        "confusion_matrix": cm,
    }


# =============================================
# TRAIN ALL MODELS
# =============================================
def train(retrain_feedback_path: str | None = None, min_f1: float | None = None) -> dict:
    print("\n" + "="*55)
    print("  AI FRAUD DETECTION - MODEL TRAINING")
    print("="*55)

    # -- Load data --
    df = load_data()

    # Optional: append feedback data for retraining
    if retrain_feedback_path and os.path.exists(retrain_feedback_path):
        fb = pd.read_csv(retrain_feedback_path)
        print(f"  Appending {len(fb)} feedback rows for retraining.")
        df = pd.concat([df, fb], ignore_index=True)

    # -- Feature engineering --
    df["log_amount"] = np.log1p(df["amount"])
    df["balance_diff"] = df["sender_balance"] - df["receiver_balance"]
    df["is_night"] = df["transaction_hour"].apply(lambda h: 1 if h >= 22 or h <= 5 else 0)
    df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    print(f"\n  Samples: {len(df)} | Features: {len(NUMERIC_FEATURES + CATEGORICAL_FEATURES)}")
    print(f"  Fraud rate: {y.mean()*100:.1f}%")

    # -- Train / test split --
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # -- Preprocessor --
    preprocessor = build_preprocessor()

    # -- Fit preprocessor on training set --
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc  = preprocessor.transform(X_test)

    # -- Apply SMOTE to training set --
    if SMOTE_AVAILABLE:
        print("\n  Applying SMOTE oversampling...")
        sm = SMOTE(random_state=42, k_neighbors=5)
        X_train_bal, y_train_bal = sm.fit_resample(X_train_proc, y_train)
        print(f"  After SMOTE - genuine: {(y_train_bal==0).sum()}, fraud: {(y_train_bal==1).sum()}")
    else:
        X_train_bal, y_train_bal = X_train_proc, y_train

    # =============================================
    # DEFINE MODELS
    # =============================================
    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=42
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=8, class_weight="balanced", random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=150, max_depth=12, class_weight="balanced",
            random_state=42, n_jobs=-1
        ),
    }
    if XGBOOST_AVAILABLE:
        scale_pos = int((y_train_bal == 0).sum() / max((y_train_bal == 1).sum(), 1))
        models["XGBoost"] = XGBClassifier(
            n_estimators=150, max_depth=6, learning_rate=0.1,
            scale_pos_weight=scale_pos, random_state=42,
            eval_metric="logloss", verbosity=0
        )

    # =============================================
    # TRAIN & EVALUATE
    # =============================================
    print("\n  Training and evaluating models...")
    results = {}
    trained_models = {}

    for name, clf in models.items():
        clf.fit(X_train_bal, y_train_bal)
        metrics = evaluate_model(name, clf, X_test_proc, y_test)
        results[name] = metrics
        trained_models[name] = clf

    # =============================================
    # SELECT BEST MODEL (by F1 on test set)
    # =============================================
    best_name = max(results, key=lambda k: results[k]["f1_score"])
    best_model = trained_models[best_name]
    best_metrics = results[best_name]
    print(f"\n  Best model: {best_name} (F1={best_metrics['f1_score']:.4f})")

    # Always expose Random Forest feature importances for XAI
    rf_model = trained_models["Random Forest"]

    # -- Feature importance --
    cat_encoder = preprocessor.named_transformers_["cat"]
    cat_feature_names = cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist()
    all_feature_names = NUMERIC_FEATURES + cat_feature_names

    importance_dict = {}
    if hasattr(rf_model, "feature_importances_"):
        importances = rf_model.feature_importances_
        for fname, imp in zip(all_feature_names, importances):
            importance_dict[fname] = round(float(imp), 6)

    # -- Train Isolation Forest (anomaly detection) --
    print("\n  Training Isolation Forest for anomaly detection...")
    iso_forest = IsolationForest(
        n_estimators=100, contamination=0.1, random_state=42
    )
    iso_forest.fit(X_train_bal)

    # =============================================
    # SAVE ARTEFACTS
    # =============================================
    os.makedirs(ActiveConfig.MODEL_DIR, exist_ok=True)

    # Backup existing model if present
    if os.path.exists(ActiveConfig.MODEL_PATH):
        joblib.dump(
            joblib.load(ActiveConfig.MODEL_PATH),
            ActiveConfig.MODEL_BACKUP_PATH
        )
        print("  Previous model backed up.")

    # Validate before saving (retraining guard)
    if min_f1 and best_metrics["f1_score"] < min_f1:
        print(f"\n  WARNING: New model F1 ({best_metrics['f1_score']:.4f}) < threshold ({min_f1}). NOT saved.")
        return {"status": "rejected", "reason": "F1 below threshold", **best_metrics}

    joblib.dump(best_model,    ActiveConfig.MODEL_PATH)
    joblib.dump(preprocessor,  ActiveConfig.PREPROCESSOR_PATH)
    joblib.dump(iso_forest,    os.path.join(ActiveConfig.MODEL_DIR, "isolation_forest.pkl"))
    joblib.dump(rf_model,      os.path.join(ActiveConfig.MODEL_DIR, "random_forest.pkl"))

    # Save all model results + feature importance to JSON
    performance = {
        "models": results,
        "best_model": best_name,
        "feature_importance": importance_dict,
        "feature_names": all_feature_names,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "smote_applied": SMOTE_AVAILABLE,
        "xgboost_available": XGBOOST_AVAILABLE,
        "trained_at": pd.Timestamp.now().isoformat(),
    }
    with open(ActiveConfig.MODEL_PERFORMANCE_PATH, "w") as f:
        json.dump(performance, f, indent=2)

    print(f"\n  [OK] Model saved   : {ActiveConfig.MODEL_PATH}")
    print(f"  [OK] Preprocessor  : {ActiveConfig.PREPROCESSOR_PATH}")
    print(f"  [OK] Performance   : {ActiveConfig.MODEL_PERFORMANCE_PATH}")
    print("\n" + "="*55)
    print("  TRAINING COMPLETE")
    print("="*55 + "\n")

    return {"status": "success", **best_metrics}


if __name__ == "__main__":
    train()
