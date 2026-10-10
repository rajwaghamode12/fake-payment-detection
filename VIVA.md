# VIVA.md — Viva Questions and Answers
## AI-Based Online Payment Fraud Detection and Risk Analysis System

> Prepared for college project viva/oral examination. Answers are written in simple language.

---

## Section 1: Project Overview

**Q1. What is the title and objective of your project?**

The project is titled "AI-Based Online Payment Fraud Detection and Risk Analysis System." The objective is to build a web application that uses machine learning to analyse simulated online payment transactions and determine whether they are genuine, suspicious, or fraudulent. It calculates a risk score, explains the reasons, and recommends an action.

---

**Q2. What problem does your project solve?**

Online payment fraud is a major problem — fraudsters use stolen credentials, unusual devices, and unusual locations to make unauthorised transactions. Traditional systems use fixed rules. Our system uses machine learning to learn patterns from data and detect fraud more accurately, even when fraud patterns change.

---

**Q3. What kind of data does your system use?**

The system uses a synthetic (artificially generated) dataset of 5000 transactions — 4500 genuine and 500 fraudulent. The data includes transaction amount, type, time, location, device, sender balance, receiver balance, and behavioural flags. No real financial data is used.

---

**Q4. Is this connected to a real bank or payment gateway?**

No. This is a purely academic demo system. It does not connect to any real bank, payment network, or financial institution. All transactions are simulated for demonstration purposes.

---

## Section 2: Machine Learning

**Q5. What is supervised learning?**

Supervised learning is a type of machine learning where the model is trained on labelled data — meaning each training example has an input (transaction features) and a known output (fraud = 1 or genuine = 0). The model learns the relationship and predicts the label for new, unseen data.

---

**Q6. What is classification?**

Classification is a supervised learning task where the output is a category (class). In our project, the two classes are Fraud (1) and Genuine (0). The model takes transaction features as input and outputs a class label and a probability.

---

**Q7. What ML models did you use?**

We trained four models:
1. **Logistic Regression** — Simple, fast, interpretable baseline classifier
2. **Decision Tree** — Tree-based model that makes splits on feature values
3. **Random Forest** — Ensemble of 150 decision trees; most reliable model
4. **XGBoost** — Gradient boosting; often achieves the best performance on tabular data

The best model (by F1 score) is selected as the active model.

---

**Q8. What is Random Forest and why is it used?**

Random Forest trains many decision trees on random subsets of the data and features, then combines their predictions (majority vote). It is used because:
- It handles class imbalance well with class_weight='balanced'
- It gives feature importance scores (useful for Explainable AI)
- It is robust to overfitting
- It works well on tabular financial data

---

**Q9. What is Logistic Regression?**

Logistic Regression is a linear model that uses a sigmoid function to output a probability between 0 and 1. If the probability > 0.5, the transaction is classified as fraud. It is simple, fast, and interpretable, making it a good baseline model.

---

**Q10. What is a Decision Tree?**

A Decision Tree splits data into branches based on feature values (e.g., "Is amount > ₹50,000?"). Each branch leads to a decision. It is easy to visualise and explain. The main weakness is overfitting, which we address by setting max_depth=8.

---

**Q11. What is XGBoost?**

XGBoost (Extreme Gradient Boosting) is an ensemble method that builds trees sequentially, where each new tree corrects the errors of the previous ones. It is known for high performance on structured/tabular data and is widely used in fraud detection competitions.

---

**Q12. What is SMOTE and why is it needed?**

SMOTE stands for Synthetic Minority Oversampling Technique. In our dataset, only 10% of transactions are fraud — this is class imbalance. If we train the model on imbalanced data, it will simply predict "genuine" for everything and still get 90% accuracy. SMOTE creates synthetic fraud examples in the training set to balance the classes, helping the model learn fraud patterns properly.

---

**Q13. Why is accuracy not enough for fraud detection?**

With 90% genuine and 10% fraud transactions, a model that always predicts "genuine" achieves 90% accuracy — but it catches zero frauds. That is useless. Instead, we focus on:
- **Recall** (did we catch all actual frauds?)
- **Precision** (are our fraud alerts actually fraud?)
- **F1 Score** (balance of precision and recall)
- **ROC-AUC** (overall discrimination ability)

---

**Q14. What is Precision?**

Precision = TP / (TP + FP). Of all transactions the model predicted as fraud, what fraction were actually fraud? High precision means fewer false alarms (false positives).

---

**Q15. What is Recall?**

Recall = TP / (TP + FN). Of all actual fraud transactions, what fraction did the model catch? High recall means fewer missed frauds (false negatives). In fraud detection, recall is usually more important — missing a fraud is more costly than a false alarm.

---

**Q16. What is F1 Score?**

F1 Score is the harmonic mean of Precision and Recall: F1 = 2 × (Precision × Recall) / (Precision + Recall). It balances the trade-off between precision and recall. It is the primary metric we use to select the best model.

---

**Q17. What is ROC-AUC?**

ROC stands for Receiver Operating Characteristic curve. AUC is the Area Under the Curve. It measures how well the model separates the two classes (fraud vs genuine) across all possible decision thresholds. AUC = 1.0 is perfect; AUC = 0.5 is random guessing. We aim for AUC > 0.90.

---

**Q18. What is a Confusion Matrix?**

A confusion matrix shows four values:
- **True Positive (TP)**: Fraud predicted as fraud (correct)
- **True Negative (TN)**: Genuine predicted as genuine (correct)
- **False Positive (FP)**: Genuine predicted as fraud (false alarm)
- **False Negative (FN)**: Fraud predicted as genuine (missed fraud)

---

**Q19. What are False Positives and False Negatives?**

- **False Positive**: The model said "fraud" but the transaction was actually genuine. This causes inconvenience to customers.
- **False Negative**: The model said "genuine" but the transaction was actually fraud. This means a fraud went undetected — a more serious error in banking.

---

## Section 3: Anomaly Detection

**Q20. What is anomaly detection?**

Anomaly detection identifies data points that are significantly different from the normal pattern. It does not require labelled fraud data — it learns what "normal" looks like and flags outliers.

---

**Q21. What is Isolation Forest?**

Isolation Forest is an anomaly detection algorithm that isolates outliers by randomly partitioning the data. Anomalies are isolated more quickly (fewer partitions needed) than normal points. We use it to flag transactions that look statistically unusual — for example, a ₹90,000 transaction when all previous transactions were below ₹5,000.

---

**Q22. How do you combine ML classification and anomaly detection?**

We do not treat every anomaly as fraud. Instead:
- ML model gives a fraud probability (0–1)
- Isolation Forest gives an anomaly score (0–100)
- Both scores are fed into the Risk Engine with different weights (ML = 35%, anomaly = 20%)
- The combined weighted score gives the final Risk Score

---

## Section 4: Behavioural Analysis and Velocity

**Q23. What is behavioural analysis in your project?**

The system builds a historical profile for each user from their past transactions, tracking: average amount, typical transaction hours, typical locations, typical device types. When a new transaction arrives, it is compared against this profile. Deviations (like a very large amount at 2 AM from a new device in a different city) increase the risk score.

---

**Q24. What is transaction velocity detection?**

Velocity detection counts how many transactions a user submitted in the last N minutes (default: 60 minutes). If a user normally submits 2–3 transactions per hour but suddenly submits 15 transactions in 5 minutes, it is flagged as unusual velocity and contributes to the risk score.

---

## Section 5: Risk Engine and Explainable AI

**Q25. How does the Risk Engine work?**

The Risk Engine takes six weighted inputs:
1. ML Fraud Probability (35%)
2. Anomaly Score (20%)
3. Behavioural Score (20%)
4. Velocity Score (10%)
5. New Device flag (8%)
6. Unusual Location flag (7%)

These are combined into a single Risk Score from 0 to 100. The score is mapped to: LOW (0–25), MEDIUM (26–50), HIGH (51–75), CRITICAL (76–100).

---

**Q26. What is Explainable AI (XAI)?**

Explainable AI means providing human-understandable reasons for a model's prediction. Instead of just saying "this is fraud," we explain: "Transaction amount (₹80,000) is 95% of sender balance," "New device detected," "Transaction at 2 AM — unusual time." We use Random Forest feature importance to identify the most influential features.

---

**Q27. What is feature importance?**

Feature importance in Random Forest measures how much each feature contributes to reducing impurity (uncertainty) across all trees. Features like `log_amount`, `amount_to_balance_ratio`, and `transaction_hour` tend to have the highest importance. This helps explain why a transaction was flagged.

---

**Q28. Does feature importance prove causation?**

No. Feature importance shows correlation — a feature that is highly predictive of fraud does not mean it causes fraud. For example, a large amount is correlated with fraud but a large genuine transaction also exists. We clearly state this limitation in the result page.

---

## Section 6: System Design

**Q29. What is Flask?**

Flask is a lightweight Python web framework. It handles HTTP requests, routes URLs to Python functions, renders HTML templates, and manages user sessions. We use Flask 3.0 for this project.

---

**Q30. What is SQLite and why did you choose it?**

SQLite is a serverless, file-based relational database. We chose it because it requires no separate server setup, is perfect for demos and prototypes, and supports SQL queries. The database file is stored at `database/database.db`.

---

**Q31. What tables are in your database?**

Five tables:
1. `users` — user accounts (id, name, email, password_hash, role)
2. `transactions` — all analysed transactions with scores and predictions
3. `feedback` — admin review decisions for model training
4. `model_versions` — history of trained model versions and metrics
5. `alerts` — high-risk transaction alerts

---

**Q32. How do you store passwords securely?**

We use Werkzeug's `generate_password_hash()` which applies PBKDF2-SHA256 hashing with a random salt. Plain-text passwords are never stored. On login, `check_password_hash()` verifies the entered password against the stored hash.

---

**Q33. What are your API endpoints?**

Key endpoints:
- `POST /api/predict` — runs the fraud prediction pipeline
- `GET /api/transactions` — returns transaction list
- `GET /api/statistics` — summary stats
- `POST /api/review` — admin submits review decision
- `POST /api/retrain` — triggers model retraining
- `GET /api/report/csv` and `/api/report/pdf` — download reports

---

**Q34. What is role-based access control in your project?**

Users have two roles: `user` and `admin`. Regular users can check transactions, view history, and use the simulation lab. Admins can access the review queue, model performance page, retraining, drift detection, and monitoring. A decorator `@admin_required` protects admin routes.

---

## Section 7: Model Drift and Retraining

**Q35. What is model drift?**

Model drift occurs when the statistical properties of incoming data change over time, causing the model's performance to degrade. For example, if fraudsters change their tactics after training, the model trained on old patterns may miss new fraud. Our drift detection module compares recent transaction statistics (fraud rate, average amount) against the training baseline.

---

**Q36. How does your retraining workflow work?**

1. Admin clicks "Retrain Model"
2. System loads the original dataset + admin feedback
3. All four models are retrained
4. The new model must achieve F1 ≥ 0.70 (configurable threshold)
5. If it passes: old model is backed up, new model is saved
6. If it fails: old model is kept and the admin is informed
7. The model is reloaded in memory automatically

---

**Q37. Why don't you retrain automatically?**

Automatic retraining without validation is dangerous. A poorly trained model could start approving fraudulent transactions or blocking all genuine ones. We require manual admin approval and a minimum F1 threshold before the new model replaces the old one.

---

## Section 8: Fraud Simulation Lab

**Q38. What is the Fraud Simulation Lab?**

The Fraud Simulation Lab allows the admin or student to create synthetic fraud scenarios by selecting flags like Large Amount, New Device, Unusual Location, Unusual Time, High Velocity, and Abnormal Behaviour. The system runs these through the complete AI pipeline and shows the resulting risk score and explanation. It is useful for demonstrating how the system responds to different fraud patterns.

---

## Section 9: Data and Privacy

**Q39. What kind of data does your system collect?**

The system collects only simulated transaction data entered by users for demo purposes. It does not collect:
- Real card numbers
- CVVs or PINs
- OTPs
- Bank passwords
- Real personal financial information

---

**Q40. What security measures are implemented?**

- Password hashing (PBKDF2-SHA256)
- Session-based authentication with timeout
- Role-based access control
- Input validation on all forms and APIs
- Parameterised SQLite queries (prevents SQL injection)
- Environment variables for secrets
- No real payment data collected

---

**Q41. What are the limitations of your system?**

1. Uses synthetic data — real fraud patterns are more complex
2. Risk thresholds are heuristic, not official banking standards
3. Not connected to real payment networks
4. Retraining is manual, not automated
5. No HTTPS, rate limiting, or WAF in the demo setup
6. Geographic analysis uses city names only, not real GPS coordinates

---

**Q42. What is the future scope of this project?**

1. Deep learning (LSTM) for sequence-based fraud detection
2. Graph Neural Networks for detecting connected fraud rings
3. Real-time streaming with Apache Kafka
4. AutoML for automated model selection
5. Multi-factor authentication
6. Cloud deployment (AWS/GCP) with auto-scaling
7. Federated learning for privacy-preserving training
8. Integration with payment gateway sandboxes (demo only)

---

**Q43. What is the difference between Precision and Recall in simple terms?**

Imagine you are a security guard at an airport:
- **Precision**: Of everyone you stopped and searched, what fraction was actually carrying contraband? (Avoiding false alarms)
- **Recall**: Of everyone who was actually carrying contraband, what fraction did you catch? (Avoiding missed detections)

In fraud detection, recall is usually more important — it is worse to miss a fraud than to have a false alarm.

---

**Q44. What is the difference between supervised and unsupervised learning?**

- **Supervised**: Trained on labelled data (we know which transactions are fraud). Examples: Logistic Regression, Decision Tree, Random Forest, XGBoost.
- **Unsupervised**: No labels needed — the model finds patterns on its own. Example: Isolation Forest — it does not know what fraud looks like, it just identifies unusual transactions.

---

**Q45. Why do you use an ensemble like Random Forest instead of a single decision tree?**

A single decision tree tends to overfit — it memorises the training data but performs poorly on new data. Random Forest trains 150 trees on random subsets of data and features, then combines their votes. This reduces overfitting and gives more robust predictions. It also produces feature importance, which we use for Explainable AI.
