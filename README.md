# FraudShield AI — Online Payment Fraud Detection System

> **Academic Demo System** — Uses synthetic data only. Not for real banking use.

A full-stack, machine-learning-powered web application that detects fraudulent online payment transactions using a multi-layer AI pipeline combining ML Classification, Anomaly Detection, Behavioural Analysis, Velocity Detection, Dynamic Risk Scoring, and Explainable AI.

---

## Problem Statement

Online payment fraud costs billions of dollars globally every year. Traditional rule-based systems struggle to keep up with evolving fraud patterns. This project demonstrates how machine learning can be used to automatically detect suspicious transactions by analysing multiple signals simultaneously.

---

## Objectives

- Detect fraudulent transactions using ML classification models
- Identify statistical anomalies using Isolation Forest
- Analyse user behavioural patterns to flag deviations
- Detect high-frequency transaction bursts (velocity)
- Combine all signals into a single explainable Risk Score (0–100)
- Provide an admin review workflow with feedback-based learning
- Monitor model performance and detect model drift

---

## Features

| Feature | Description |
|---|---|
| Sender Balance Validation | Checks if sender has enough balance before AI fraud prediction |
| ML Classification | Logistic Regression, Decision Tree, Random Forest, XGBoost |
| Anomaly Detection | Isolation Forest flags statistically unusual transactions |
| Behavioural Analysis | Historical profile comparison for each user |
| Velocity Detection | Detects rapid transaction bursts per hour |
| Dynamic Risk Engine | Weighted 0–100 score combining all signals |
| Explainable AI | Plain-language reasons for every prediction |
| Fraud Simulation Lab | Test fraud scenarios with synthetic data |
| Admin Dashboard | Charts, stats, model metrics |
| Manual Review | Admin review queue for high-risk transactions |
| Feedback Learning | Admin decisions stored for model improvement |
| Model Retraining | Safe retraining with validation gate |
| Drift Detection | Monitors for statistical shifts in transaction data |
| Report Generation | PDF and CSV fraud reports |
| Geographic Risk View | Coarse location-based risk map |
| Graph Analysis | Transaction relationship network visualisation |
| Role-Based Access | Separate user and admin interfaces |

---

## Technologies Used

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0 |
| Machine Learning | Scikit-learn, XGBoost, imbalanced-learn (SMOTE) |
| Data Processing | Pandas, NumPy |
| Model Persistence | Joblib |
| Database | SQLite (via sqlite3) |
| Frontend | Bootstrap 5, Chart.js 4, Bootstrap Icons |
| Fonts | Google Fonts (Inter) |
| Reports | ReportLab (PDF), csv (CSV) |
| Authentication | Werkzeug password hashing, Flask sessions |

---

## Project Structure

```
online-payment-fraud-detection-v2/
│
├── app.py                        # Main Flask application
├── config.py                     # Configuration (thresholds, paths, settings)
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── README.md                     # This file
├── VIVA.md                       # Viva questions and answers
│
├── dataset/
│   ├── generate_data.py          # Synthetic dataset generator
│   └── payment_fraud.csv         # Generated CSV (5000 rows)
│
├── model/
│   ├── train_model.py            # Training script (4 models + Isolation Forest)
│   ├── evaluate_model.py         # Drift detection & evaluation utilities
│   ├── fraud_model.pkl           # Saved best model
│   ├── preprocessor.pkl          # Fitted preprocessor (StandardScaler + OHE)
│   ├── random_forest.pkl         # Random Forest for XAI feature importance
│   ├── isolation_forest.pkl      # Isolation Forest for anomaly detection
│   └── model_performance.json    # All model metrics (actual, not fabricated)
│
├── database/
│   ├── models.py                 # SQLite table DDL statements
│   ├── init_db.py                # DB initialiser + admin seeding
│   └── database.db               # SQLite database (auto-created)
│
├── services/
│   ├── fraud_prediction.py       # Core prediction pipeline
│   ├── risk_engine.py            # Dynamic risk score (0–100)
│   ├── behavior_analysis.py      # User behavioural profiling
│   ├── anomaly_detection.py      # Isolation Forest wrapper
│   ├── velocity_detection.py     # Transaction frequency analysis
│   └── report_generator.py       # PDF + CSV report generation
│
├── templates/                    # Jinja2 HTML templates
│   ├── base.html                 # Base layout with navbar
│   ├── login.html / register.html
│   ├── dashboard.html            # User dashboard
│   ├── transaction.html          # Transaction input form
│   ├── result.html               # Prediction result page
│   ├── history.html              # Transaction history
│   ├── alerts.html               # Alert center
│   ├── simulation.html           # Fraud simulation lab
│   ├── admin.html                # Admin dashboard
│   ├── review.html               # Manual review queue
│   ├── model_performance.html    # Model metrics page
│   ├── feedback.html             # Feedback log
│   ├── retrain.html              # Model retraining page
│   ├── drift.html                # Drift detection page
│   ├── monitoring.html           # Live transaction monitor
│   ├── about.html                # About page
│   ├── geo_risk.html             # Geographic risk view
│   ├── graph_analysis.html       # Graph-based analysis
│   └── error.html                # 404/403/500 error page
│
├── static/
│   ├── css/style.css             # Custom dark-theme CSS
│   └── js/
│       ├── dashboard.js          # UI utilities (counters, toasts)
│       └── charts.js             # Chart.js global dark theme defaults
│
└── reports/                      # Generated reports saved here
```

---

## Installation

### Step 1 — Clone / Open the project

```bash
cd "online-payment-fraud-detection-v2"
```

### Step 2 — Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Copy environment file

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux
```

Edit `.env` if you want to change the admin password or secret key.

---

## Model Training

Train all four ML models and generate performance metrics:

```bash
python model/train_model.py
```

This will:
1. Generate the synthetic dataset (if not present)
2. Train: Logistic Regression, Decision Tree, Random Forest, XGBoost
3. Apply SMOTE oversampling
4. Train Isolation Forest for anomaly detection
5. Save: `model/fraud_model.pkl`, `model/preprocessor.pkl`, `model/model_performance.json`
6. Print actual performance metrics (Accuracy, Precision, Recall, F1, ROC-AUC)

Training takes approximately 30–60 seconds on a standard laptop.

---

## Running the Application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@frauddetect.demo | Admin@123 |
| User | Register a new account | Any password (min 6 chars) |

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/predict` | Predict fraud for a transaction | User |
| GET | `/api/transactions` | List transactions | User/Admin |
| GET | `/api/statistics` | Summary statistics | User/Admin |
| GET | `/api/alerts` | Active alerts | User/Admin |
| POST | `/api/review` | Submit admin review decision | Admin |
| POST | `/api/retrain` | Trigger model retraining | Admin |
| GET | `/api/report/csv` | Download CSV report | User |
| GET | `/api/report/pdf` | Download PDF report | Admin |
| GET | `/api/monitoring/live` | Live monitoring data | Admin |
| GET | `/api/drift` | Model drift analysis | Admin |

---

## Sample Test Transactions

### Test 1 — Normal (Expected: LOW risk)
```
Amount: ₹1,500 | Type: UPI | Hour: 14 | Location: Mumbai
New Device: No | Unusual Location: No
```

### Test 2 — Large Amount (Expected: MEDIUM–HIGH risk)
```
Amount: ₹95,000 | Type: Bank Transfer | Hour: 3
New Device: Yes | Unusual Location: Yes
```

### Test 3 — Suspicious Pattern (Expected: HIGH–CRITICAL risk)
```
Amount: ₹78,000 | Type: Card | Hour: 2 | Location: Kolkata
New Device: Yes | Unusual Location: Yes
```

Use the **Quick Test Cases** buttons on the Check Transaction page to fill these automatically.

---

## ML Pipeline

```
Raw Input
    ↓
Feature Engineering
(log_amount, balance_diff, is_night, is_weekend, amount_to_balance_ratio)
    ↓
StandardScaler (numeric) + OneHotEncoder (categorical)
    ↓
┌─────────────────────┐     ┌──────────────────────┐
│  Random Forest /    │     │  Isolation Forest     │
│  XGBoost (best)     │     │  Anomaly Detection    │
└────────┬────────────┘     └───────────┬──────────┘
         │ Fraud Probability            │ Anomaly Score
         └──────────────┬───────────────┘
                        ↓
              Behavioural Analysis
              Velocity Detection
                        ↓
              Dynamic Risk Engine
              (Weighted combination)
                        ↓
              Risk Score: 0–100
              Risk Level: LOW/MEDIUM/HIGH/CRITICAL
                        ↓
              Explainable AI (reasons list)
```

---

## Class Imbalance Handling

The synthetic dataset has ~10% fraud rate — a realistic imbalance. The system handles this with:

1. **SMOTE** (Synthetic Minority Oversampling Technique) — generates synthetic fraud samples in the training set
2. **class_weight='balanced'** — used in Logistic Regression, Decision Tree, Random Forest
3. **scale_pos_weight** — used in XGBoost

Why accuracy alone is not enough: with 90% genuine and 10% fraud, a model that always predicts "genuine" would achieve 90% accuracy while catching zero frauds. That is why **Recall**, **Precision**, **F1-score**, and **ROC-AUC** are the primary metrics here.

---

## Risk Engine Weights

| Signal | Weight |
|---|---|
| ML Fraud Probability | 35% |
| Anomaly Score (Isolation Forest) | 20% |
| Behavioural Score | 20% |
| Velocity Score | 10% |
| New Device | 8% |
| Unusual Location | 7% |

These thresholds are for demonstration purposes and are not official banking standards.

---

## Security Considerations

- Passwords hashed with Werkzeug PBKDF2 (never stored in plain text)
- SQL injection protection via parameterised SQLite queries
- Session-based authentication with configurable timeout
- Role-based access control (user vs admin)
- Input validation on all forms and API endpoints
- No real card numbers, CVVs, PINs, or OTPs collected
- Environment variables for secrets (.env file)

This system is **not production-ready** without additional security review, HTTPS, rate limiting, WAF, regulatory compliance, and infrastructure hardening.

---

## Limitations

- Uses synthetic data — real-world fraud patterns are more complex
- Risk thresholds are heuristic, not derived from real banking standards
- No real-time connection to payment networks
- Retraining is triggered manually, not automatically
- Graph analysis is visual only — no graph database
- Geographic risk uses city names only, not real coordinates

---

## Future Improvements

- Deep learning models (LSTM for sequence-based fraud detection)
- Graph Neural Networks for relationship-based fraud detection
- Real-time streaming with Apache Kafka
- AutoML for automated hyperparameter tuning
- Multi-factor authentication
- Kubernetes deployment with horizontal scaling
- Integration with actual payment gateway sandboxes (demo only)
- Federated learning for privacy-preserving model training

---

## Disclaimer

This project is built for **academic and demonstration purposes only**. It uses entirely synthetic, randomly-generated data. No real card numbers, PINs, OTPs, bank passwords, or personal financial information are collected or processed. The risk thresholds shown are not official banking standards. This system should not be deployed in production without extensive security review, regulatory compliance (PCI DSS, RBI guidelines, etc.), and professional validation.

## Test Cases

### 1. Sufficient Balance (Proceeds to Fraud Detection)
- **Sender Balance**: ₹50,000
- **Transaction Amount**: ₹10,000
- **Result**: Transaction is processed and sent to the ML risk engine.

### 2. Insufficient Balance (Immediate Rejection)
- **Sender Balance**: ₹5,000
- **Transaction Amount**: ₹20,000
- **Result**: Transaction Rejected: Insufficient Balance.

