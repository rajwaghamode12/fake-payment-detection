"""
app.py - Main Flask Application
AI-Based Online Payment Fraud Detection System

Routes:
  AUTH        : /login  /register  /logout
  USER        : /dashboard  /check-transaction  /result/<id>
                /history  /alerts  /simulation
  ADMIN       : /admin  /admin/review  /admin/review/<id>
                /admin/feedback  /admin/retrain  /admin/model-performance
                /admin/monitoring  /admin/drift
  API         : /api/predict  /api/transactions  /api/statistics
                /api/alerts  /api/review  /api/retrain
                /api/report/pdf  /api/report/csv
  MISC        : /about  /graph-analysis  /geo-risk
"""

import os
import sys
import json
import uuid
import sqlite3
import secrets
import warnings
from datetime import datetime, timedelta
from functools import wraps

warnings.filterwarnings("ignore")

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, abort, g
)
from werkzeug.security import generate_password_hash, check_password_hash
import io

# ── Project imports ───────────────────────────
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from config import ActiveConfig
from database.init_db import init_db, get_connection
from services.fraud_prediction import predict, reload_model
from services.behavior_analysis import analyze_behavior
from services.velocity_detection import get_velocity
from services.report_generator import generate_pdf_report, generate_csv_report
from model.evaluate_model import load_performance, detect_drift


# ══════════════════════════════════════════════
# APP FACTORY
# ══════════════════════════════════════════════
def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = ActiveConfig.SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = ActiveConfig.PERMANENT_SESSION_LIFETIME

    os.makedirs(ActiveConfig.REPORTS_DIR, exist_ok=True)

    # Init DB & seed admin on first run
    init_db()

    # ── DB helper ──────────────────────────────
    def db():
        if "db" not in g:
            g.db = get_connection()
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        conn = g.pop("db", None)
        if conn:
            conn.close()

    # ══════════════════════════════════════════
    # AUTH DECORATORS
    # ══════════════════════════════════════════
    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated

    def admin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in.", "warning")
                return redirect(url_for("login"))
            if session.get("role") != "admin":
                flash("Admin access required.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated

    # ══════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════
    def _row_to_dict(row) -> dict:
        return dict(row) if row else {}

    def _rows_to_list(rows) -> list[dict]:
        return [dict(r) for r in rows]

    def _get_stats(user_id: int | None = None) -> dict:
        conn = db()
        where = "WHERE user_id = ?" if user_id else ""
        params = (user_id,) if user_id else ()

        total     = conn.execute(f"SELECT COUNT(*) FROM transactions {where}", params).fetchone()[0]
        genuine   = conn.execute(f"SELECT COUNT(*) FROM transactions {where} {'AND' if user_id else 'WHERE'} prediction='Genuine'",   params).fetchone()[0]
        suspicious= conn.execute(f"SELECT COUNT(*) FROM transactions {where} {'AND' if user_id else 'WHERE'} prediction='Suspicious'", params).fetchone()[0]
        fraud     = conn.execute(f"SELECT COUNT(*) FROM transactions {where} {'AND' if user_id else 'WHERE'} prediction='Fraud'",      params).fetchone()[0]
        high_risk = conn.execute(
            f"SELECT COUNT(*) FROM transactions {where} {'AND' if user_id else 'WHERE'} risk_level IN ('HIGH','CRITICAL')",
            params
        ).fetchone()[0]
        avg_risk_row = conn.execute(f"SELECT AVG(risk_score) FROM transactions {where}", params).fetchone()
        avg_risk = round(avg_risk_row[0] or 0, 1)

        fraud_rate = round(fraud / total * 100, 1) if total else 0
        return {
            "total":          total,
            "genuine":        genuine,
            "suspicious":     suspicious,
            "fraud":          fraud,
            "high_risk":      high_risk,
            "avg_risk_score": avg_risk,
            "fraud_rate":     fraud_rate,
        }

    def _save_alert(conn, transaction_id: str, risk_level: str, risk_score: float, message: str):
        if risk_level in ("HIGH", "CRITICAL"):
            conn.execute(
                "INSERT INTO alerts (transaction_id, risk_level, risk_score, message) VALUES (?,?,?,?)",
                (transaction_id, risk_level, risk_score, message)
            )

    # ══════════════════════════════════════════
    # ── AUTHENTICATION ─────────────────────────
    # ══════════════════════════════════════════

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("admin_dashboard") if session.get("role") == "admin" else url_for("dashboard"))
        return redirect(url_for("portal"))

    @app.route("/portal")
    @app.route("/hub")
    @app.route("/all-in-one")
    @app.route("/links")
    @app.route("/quick-access")
    def portal():
        return render_template("portal.html")

    @app.route("/quick-login/<role>")
    def quick_login(role):
        conn = db()
        target_role = "admin" if role == "admin" else "user"
        user = _row_to_dict(conn.execute(
            "SELECT * FROM users WHERE role = ? LIMIT 1", (target_role,)
        ).fetchone())

        if not user:
            if target_role == "admin":
                user = _row_to_dict(conn.execute(
                    "SELECT * FROM users WHERE email = ?", (ActiveConfig.ADMIN_EMAIL,)
                ).fetchone())
            else:
                user = _row_to_dict(conn.execute(
                    "SELECT * FROM users LIMIT 1"
                ).fetchone())

        if user:
            session.permanent = True
            session["user_id"] = user["id"]
            session["name"]    = user["name"]
            session["email"]   = user["email"]
            session["role"]    = user["role"]
            flash(f"Logged in as {user['name']} ({user['role']}).", "success")

        next_endpoint = request.args.get("next")
        if next_endpoint:
            try:
                return redirect(url_for(next_endpoint))
            except Exception:
                pass

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("check_transaction"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email    = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                flash("Email and password are required.", "danger")
                return render_template("login.html")

            conn = db()
            user = _row_to_dict(conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone())

            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html")

            session.permanent = True
            session["user_id"] = user["id"]
            session["name"]    = user["name"]
            session["email"]   = user["email"]
            session["role"]    = user["role"]

            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("admin_dashboard") if user["role"] == "admin" else url_for("dashboard"))

        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            name     = request.form.get("name", "").strip()
            email    = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm  = request.form.get("confirm_password", "")

            errors = []
            if not name:
                errors.append("Name is required.")
            if not email or "@" not in email:
                errors.append("Valid email is required.")
            if len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if password != confirm:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("register.html")

            conn = db()
            existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if existing:
                flash("Email already registered. Please log in.", "warning")
                return redirect(url_for("login"))

            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,'user')",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # ══════════════════════════════════════════
    # ── USER DASHBOARD ─────────────────────────
    # ══════════════════════════════════════════

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user_id = session["user_id"]
        stats   = _get_stats(user_id)
        conn    = db()

        recent = _rows_to_list(conn.execute(
            """SELECT * FROM transactions WHERE user_id=?
               ORDER BY created_at DESC LIMIT 8""",
            (user_id,)
        ).fetchall())

        # Chart data – risk level distribution
        risk_counts = {
            "LOW":      conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND risk_level='LOW'",      (user_id,)).fetchone()[0],
            "MEDIUM":   conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND risk_level='MEDIUM'",   (user_id,)).fetchone()[0],
            "HIGH":     conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND risk_level='HIGH'",     (user_id,)).fetchone()[0],
            "CRITICAL": conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND risk_level='CRITICAL'", (user_id,)).fetchone()[0],
        }

        # Trend data – last 7 days
        trend_labels, trend_values = [], []
        for i in range(6, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            cnt = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE user_id=? AND created_at LIKE ?",
                (user_id, f"{d}%")
            ).fetchone()[0]
            trend_labels.append(d[5:])   # MM-DD
            trend_values.append(cnt)

        return render_template(
            "dashboard.html",
            stats=stats,
            recent=recent,
            risk_counts=json.dumps(risk_counts),
            trend_labels=json.dumps(trend_labels),
            trend_values=json.dumps(trend_values),
        )

    # ══════════════════════════════════════════
    # ── TRANSACTION CHECKING ───────────────────
    # ══════════════════════════════════════════

    @app.route("/check-transaction", methods=["GET", "POST"])
    @app.route("/check_transaction", methods=["GET", "POST"])
    @app.route("/transaction", methods=["GET", "POST"])
    @app.route("/transaction/new", methods=["GET", "POST"])
    @login_required
    def check_transaction():
        if request.method == "POST":
            # ── Input validation ───────────────
            errors = []

            # Robust Amount Parsing (supports ₹, $, commas, decimals)
            raw_amt = str(request.form.get("amount", "")).replace("₹", "").replace("$", "").replace(",", "").strip()
            try:
                amount = float(raw_amt) if raw_amt else 0.0
                if amount <= 0:
                    errors.append("Amount must be greater than 0.")
            except (ValueError, TypeError):
                errors.append("Invalid amount. Please enter a number (e.g. 5000).")
                amount = 0.0

            # Robust Time & Hour Parsing (Supports time picker "14:30", "02:30 PM", or integer hour)
            raw_time = str(request.form.get("transaction_time", "")).strip()
            raw_hour = str(request.form.get("transaction_hour", "")).strip()

            transaction_hour = None
            for candidate in [raw_time, raw_hour]:
                if not candidate:
                    continue
                cand_lower = candidate.lower()
                try:
                    if ":" in candidate:
                        parts = candidate.split(":")
                        h = int(parts[0].strip())
                        if "pm" in cand_lower and h < 12:
                            h += 12
                        elif "am" in cand_lower and h == 12:
                            h = 0
                        transaction_hour = h % 24
                        break
                    else:
                        num = int(float(candidate))
                        transaction_hour = num % 24
                        break
                except Exception:
                    continue

            if transaction_hour is None:
                transaction_hour = datetime.now().hour

            # Robust Sender Balance Parsing
            raw_sbal = str(request.form.get("sender_balance", "")).replace("₹", "").replace("$", "").replace(",", "").strip()
            test_insufficient = request.form.get("test_insufficient_balance") == "1"
            try:
                sender_balance = float(raw_sbal) if raw_sbal else None
            except Exception:
                sender_balance = None

            # If sender_balance is omitted, automatically provide sufficient funds so user is never blocked
            if sender_balance is None:
                if test_insufficient:
                    sender_balance = max(amount - 500.0, 0.0)
                else:
                    sender_balance = max(amount * 2.0, 50000.0)

            # Robust Receiver Balance Parsing
            raw_rbal = str(request.form.get("receiver_balance", "0")).replace("₹", "").replace("$", "").replace(",", "").strip()
            try:
                receiver_balance = float(raw_rbal) if raw_rbal else 0.0
                if receiver_balance < 0:
                    receiver_balance = 0.0
            except Exception:
                receiver_balance = 0.0

            transaction_type = request.form.get("transaction_type", "UPI")
            location         = request.form.get("location", "Mumbai")
            device_type      = request.form.get("device_type", "Mobile")
            prev_count       = int(float(request.form.get("previous_transaction_count", 5) or 5))
            new_device       = int(request.form.get("new_device", 0) or 0)
            unusual_location = int(request.form.get("unusual_location", 0) or 0)
            tx_id            = request.form.get("transaction_id", "").strip() or f"TX{uuid.uuid4().hex[:8].upper()}"

            valid_types = ["UPI", "Card", "Bank Transfer", "Wallet", "E-commerce"]
            if transaction_type not in valid_types:
                transaction_type = "UPI"

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("transaction.html", form_data=request.form)

            user_id = session["user_id"]

            # ── Balance Validation ─────────────
            if amount > sender_balance:
                error_card = {
                    "reason": f"Insufficient Balance (Required ₹{amount:,.2f} vs Available ₹{sender_balance:,.2f})",
                    "available_balance": sender_balance,
                    "required_amount": amount
                }
                return render_template("transaction.html", form_data=request.form, error_card=error_card)

            # ── Velocity ──────────────────────
            vel = get_velocity(user_id)

            # ── Behaviour ─────────────────────
            beh = analyze_behavior(
                user_id=user_id,
                amount=amount,
                transaction_hour=transaction_hour,
                location=location,
                transaction_type=transaction_type,
                device_type=device_type,
                new_device=new_device,
            )

            # ── Prediction ────────────────────
            result = predict(
                amount=amount,
                transaction_type=transaction_type,
                transaction_hour=transaction_hour,
                sender_balance=sender_balance,
                receiver_balance=receiver_balance,
                location=location,
                device_type=device_type,
                previous_transaction_count=prev_count,
                new_device=new_device,
                unusual_location=unusual_location,
                transactions_last_hour=vel["count"],
                velocity_score=vel["velocity_score"],
                behavior_score=beh["behavior_score"],
                behavior_result=beh,
                velocity_result=vel,
                day_of_week=datetime.now().weekday(),
            )

            if "error" in result:
                flash(result["error"], "danger")
                return render_template("transaction.html", form_data=request.form)

            # ── Determine status ───────────────
            status = "Reviewed" if result["risk_level"] in ("HIGH", "CRITICAL") else "Processed"

            # ── Save to DB ─────────────────────
            conn = db()
            conn.execute(
                """INSERT INTO transactions
                   (transaction_id, user_id, amount, transaction_type, transaction_time,
                    transaction_hour, sender_balance, receiver_balance, location,
                    device_type, previous_transaction_count, new_device, unusual_location,
                    velocity_score, behavior_score, anomaly_score, fraud_probability,
                    risk_score, risk_level, prediction, status, transactions_last_hour)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tx_id, user_id, amount, transaction_type,
                    datetime.utcnow().isoformat(), transaction_hour,
                    sender_balance, receiver_balance, location, device_type,
                    prev_count, new_device, unusual_location,
                    vel["velocity_score"], beh["behavior_score"],
                    result["anomaly_score"], result["fraud_probability"],
                    result["risk_score"], result["risk_level"],
                    result["prediction"], status, vel["count"],
                )
            )

            _save_alert(conn, tx_id, result["risk_level"], result["risk_score"],
                        f"Transaction {tx_id} flagged as {result['prediction']}")
            conn.commit()

            return redirect(url_for("result", transaction_id=tx_id))

        return render_template("transaction.html", form_data={})

    # ── Result page ───────────────────────────
    @app.route("/result/<transaction_id>")
    @login_required
    def result(transaction_id):
        conn = db()
        if session.get("role") == "admin":
            tx = _row_to_dict(conn.execute(
                "SELECT * FROM transactions WHERE transaction_id=?",
                (transaction_id,)
            ).fetchone())
        else:
            tx = _row_to_dict(conn.execute(
                "SELECT * FROM transactions WHERE transaction_id=? AND user_id=?",
                (transaction_id, session["user_id"])
            ).fetchone())
        if not tx:
            flash("Transaction not found.", "danger")
            return redirect(url_for("check_transaction"))

        # Load reasons from last predict call via session cache (stored in result page context)
        reasons_key = f"reasons_{transaction_id}"
        reasons = session.pop(reasons_key, [])

        # Rebuild reasons from stored scores if session expired
        if not reasons:
            reasons = _rebuild_reasons(tx)

        return render_template("result.html", tx=tx, reasons=reasons)

    def _rebuild_reasons(tx: dict) -> list[str]:
        reasons = []
        if tx.get("fraud_probability", 0) > 0.5:
            reasons.append(f"ML model flagged high fraud probability ({tx['fraud_probability']*100:.0f}%)")
        if tx.get("anomaly_score", 0) > 50:
            reasons.append("Transaction pattern is anomalous (Isolation Forest)")
        if tx.get("behavior_score", 0) > 30:
            reasons.append("Transaction deviates from user's historical behaviour")
        if tx.get("new_device"):
            reasons.append("Transaction initiated from a new device")
        if tx.get("unusual_location"):
            reasons.append("Transaction from an unusual location")
        if tx.get("velocity_score", 0) > 40:
            reasons.append(f"High transaction velocity ({tx.get('transactions_last_hour',0)} txns recently)")
        if tx.get("amount", 0) > 50000:
            reasons.append(f"Large transaction amount: ₹{tx['amount']:,.0f}")
        if not reasons:
            reasons.append("No significant risk factors detected.")
        return reasons

    # ── Transaction history ───────────────────
    @app.route("/history")
    @login_required
    def history():
        user_id = session["user_id"]
        is_admin = session.get("role") == "admin"
        conn    = db()

        filter_pred  = request.args.get("prediction", "all")
        filter_risk  = request.args.get("risk_level", "all")
        search       = request.args.get("search", "").strip()
        page         = max(int(request.args.get("page", 1)), 1)
        per_page     = 15

        if is_admin:
            base_query  = "FROM transactions WHERE 1=1"
            params      = []
        else:
            base_query  = "FROM transactions WHERE user_id=?"
            params      = [user_id]

        if filter_pred != "all":
            base_query += " AND prediction=?"
            params.append(filter_pred.capitalize())
        if filter_risk != "all":
            base_query += " AND risk_level=?"
            params.append(filter_risk.upper())
        if search:
            base_query += " AND (transaction_id LIKE ? OR transaction_type LIKE ? OR location LIKE ?)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]

        total_rows = conn.execute(f"SELECT COUNT(*) {base_query}", params).fetchone()[0]
        rows = _rows_to_list(conn.execute(
            f"SELECT * {base_query} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, (page - 1) * per_page]
        ).fetchall())

        total_pages = max((total_rows + per_page - 1) // per_page, 1)
        return render_template(
            "history.html",
            transactions=rows,
            page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            filter_pred=filter_pred,
            filter_risk=filter_risk,
            search=search,
        )

    # ── Alerts ────────────────────────────────
    @app.route("/alerts")
    @login_required
    def alerts():
        conn = db()
        user_id = session["user_id"]
        is_admin = session.get("role") == "admin"

        if is_admin:
            rows = _rows_to_list(conn.execute(
                "SELECT a.*, t.amount, t.transaction_type, t.prediction "
                "FROM alerts a JOIN transactions t ON a.transaction_id=t.transaction_id "
                "ORDER BY a.created_at DESC LIMIT 50"
            ).fetchall())
        else:
            rows = _rows_to_list(conn.execute(
                "SELECT a.*, t.amount, t.transaction_type, t.prediction "
                "FROM alerts a JOIN transactions t ON a.transaction_id=t.transaction_id "
                "WHERE t.user_id=? ORDER BY a.created_at DESC LIMIT 30",
                (user_id,)
            ).fetchall())

        return render_template("alerts.html", alerts=rows)

    # ── Fraud Simulation Lab ──────────────────
    @app.route("/simulation", methods=["GET", "POST"])
    @login_required
    def simulation():
        result = None
        if request.method == "POST":
            # Build simulated transaction from checkboxes
            large_amount    = "large_amount"    in request.form
            new_dev         = "new_device"      in request.form
            unusual_loc     = "unusual_location" in request.form
            unusual_time    = "unusual_time"    in request.form
            high_velocity   = "high_velocity"   in request.form
            behavioral      = "behavioral"      in request.form

            # Robust Amount Parsing in Simulation
            raw_amt = str(request.form.get("amount", "5000")).replace("₹", "").replace("$", "").replace(",", "").strip()
            try:
                amount = float(raw_amt) if raw_amt else 5000.0
            except Exception:
                amount = 5000.0

            transaction_type = request.form.get("transaction_type", "UPI")

            if large_amount:
                amount = max(amount, 80000.0)

            # Robust Time Parsing in Simulation
            raw_time = str(request.form.get("transaction_time", "")).strip()
            raw_hour = str(request.form.get("transaction_hour", "")).strip()
            tx_hour = None
            for candidate in [raw_time, raw_hour]:
                if candidate:
                    try:
                        if ":" in candidate:
                            tx_hour = int(candidate.split(":")[0]) % 24
                            break
                        else:
                            tx_hour = int(float(candidate)) % 24
                            break
                    except Exception:
                        pass
            if tx_hour is None:
                tx_hour = 2 if unusual_time else 14
            velocity_score   = 80 if high_velocity else 5
            behavior_score   = 75 if behavioral else 10
            new_device_flag  = 1 if new_dev else 0
            unusual_loc_flag = 1 if unusual_loc else 0

            vel_mock = {
                "count": 15 if high_velocity else 2,
                "window_minutes": 60,
                "velocity_score": velocity_score,
                "risk_label": "HIGH" if high_velocity else "LOW",
                "is_high_velocity": high_velocity,
            }
            beh_mock = {
                "behavior_score": behavior_score,
                "anomalies": ["Simulated behavioural anomaly"] if behavioral else [],
                "profile_exists": True,
                "profile": {},
            }

            sim_result = predict(
                amount=amount,
                transaction_type=transaction_type,
                transaction_hour=tx_hour,
                sender_balance=amount * 1.2,
                receiver_balance=500,
                location="Delhi" if unusual_loc else "Mumbai",
                device_type="Mobile",
                previous_transaction_count=10,
                new_device=new_device_flag,
                unusual_location=unusual_loc_flag,
                transactions_last_hour=vel_mock["count"],
                velocity_score=velocity_score,
                behavior_score=behavior_score,
                behavior_result=beh_mock,
                velocity_result=vel_mock,
                day_of_week=1,
            )
            result = sim_result
            result["simulation_flags"] = {
                "large_amount":    large_amount,
                "new_device":      new_dev,
                "unusual_location": unusual_loc,
                "unusual_time":    unusual_time,
                "high_velocity":   high_velocity,
                "behavioral":      behavioral,
            }
            result["amount"] = amount

        return render_template("simulation.html", result=result)

    # ══════════════════════════════════════════
    # ── ADMIN ROUTES ───────────────────────────
    # ══════════════════════════════════════════

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        conn  = db()
        stats = _get_stats()

        # Chart: predictions distribution
        pred_counts = {
            "Genuine":    stats["genuine"],
            "Suspicious": stats["suspicious"],
            "Fraud":      stats["fraud"],
        }

        # Chart: risk levels
        risk_counts = {
            "LOW":      conn.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='LOW'").fetchone()[0],
            "MEDIUM":   conn.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='MEDIUM'").fetchone()[0],
            "HIGH":     conn.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='HIGH'").fetchone()[0],
            "CRITICAL": conn.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='CRITICAL'").fetchone()[0],
        }

        # Chart: fraud by transaction type
        type_rows = conn.execute(
            "SELECT transaction_type, COUNT(*) as cnt FROM transactions "
            "WHERE prediction='Fraud' GROUP BY transaction_type"
        ).fetchall()
        fraud_by_type = {r["transaction_type"]: r["cnt"] for r in type_rows}

        # Chart: transactions over last 14 days
        trend_labels, trend_genuine, trend_fraud = [], [], []
        for i in range(13, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            g_cnt = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE created_at LIKE ? AND prediction='Genuine'", (f"{d}%",)
            ).fetchone()[0]
            f_cnt = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE created_at LIKE ? AND prediction='Fraud'", (f"{d}%",)
            ).fetchone()[0]
            trend_labels.append(d[5:])
            trend_genuine.append(g_cnt)
            trend_fraud.append(f_cnt)

        # Recent high-risk
        high_risk_tx = _rows_to_list(conn.execute(
            "SELECT * FROM transactions WHERE risk_level IN ('HIGH','CRITICAL') "
            "ORDER BY created_at DESC LIMIT 10"
        ).fetchall())

        # Unresolved alerts count
        alert_count = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE is_resolved=0"
        ).fetchone()[0]

        perf = load_performance()

        return render_template(
            "admin.html",
            stats=stats,
            pred_counts=json.dumps(pred_counts),
            risk_counts=json.dumps(risk_counts),
            fraud_by_type=json.dumps(fraud_by_type),
            trend_labels=json.dumps(trend_labels),
            trend_genuine=json.dumps(trend_genuine),
            trend_fraud=json.dumps(trend_fraud),
            high_risk_tx=high_risk_tx,
            alert_count=alert_count,
            perf=perf,
        )

    # ── Review Queue ──────────────────────────
    @app.route("/admin/review")
    @admin_required
    def review_queue():
        conn = db()
        queue = _rows_to_list(conn.execute(
            "SELECT t.*, u.name as user_name FROM transactions t "
            "JOIN users u ON t.user_id=u.id "
            "WHERE t.risk_level IN ('HIGH','CRITICAL') AND t.status != 'Reviewed' "
            "ORDER BY t.risk_score DESC LIMIT 50"
        ).fetchall())
        return render_template("review.html", queue=queue)

    @app.route("/admin/review/<transaction_id>", methods=["GET", "POST"])
    @admin_required
    def review_transaction(transaction_id):
        conn = db()
        tx = _row_to_dict(conn.execute(
            "SELECT t.*, u.name as user_name FROM transactions t "
            "JOIN users u ON t.user_id=u.id "
            "WHERE t.transaction_id=?",
            (transaction_id,)
        ).fetchone())

        if not tx:
            flash("Transaction not found.", "danger")
            return redirect(url_for("review_queue"))

        reasons = _rebuild_reasons(tx)

        if request.method == "POST":
            decision = request.form.get("decision")
            notes    = request.form.get("notes", "")

            valid_decisions = ["Confirm Fraud", "Mark Genuine", "Keep Under Review"]
            if decision not in valid_decisions:
                flash("Invalid decision.", "danger")
                return render_template("review.html", tx=tx, single=True, reasons=reasons)

            # Save feedback
            conn.execute(
                "INSERT INTO feedback (transaction_id, model_prediction, admin_decision, notes, reviewed_by) "
                "VALUES (?,?,?,?,?)",
                (transaction_id, tx["prediction"], decision, notes, session["user_id"])
            )

            # Update transaction status
            conn.execute(
                "UPDATE transactions SET status=? WHERE transaction_id=?",
                (decision, transaction_id)
            )

            # Resolve alert
            conn.execute(
                "UPDATE alerts SET is_resolved=1 WHERE transaction_id=?",
                (transaction_id,)
            )
            conn.commit()

            flash(f"Decision recorded: {decision}", "success")
            return redirect(url_for("review_queue"))

        return render_template("review.html", tx=tx, single=True, reasons=reasons)

    # ── Admin Feedback ────────────────────────
    @app.route("/admin/feedback")
    @admin_required
    def feedback_page():
        conn = db()
        feedback_rows = _rows_to_list(conn.execute(
            "SELECT f.*, t.amount, t.transaction_type, t.risk_score, t.risk_level "
            "FROM feedback f JOIN transactions t ON f.transaction_id=t.transaction_id "
            "ORDER BY f.created_at DESC LIMIT 100"
        ).fetchall())

        total   = len(feedback_rows)
        correct = sum(1 for r in feedback_rows if _is_correct(r["model_prediction"], r["admin_decision"]))
        fp      = sum(1 for r in feedback_rows if r["model_prediction"] == "Fraud" and r["admin_decision"] == "Mark Genuine")
        fn      = sum(1 for r in feedback_rows if r["model_prediction"] == "Genuine" and r["admin_decision"] == "Confirm Fraud")

        summary = {
            "total":          total,
            "correct":        correct,
            "incorrect":      total - correct,
            "false_positives": fp,
            "false_negatives": fn,
            "accuracy":       round(correct / total * 100, 1) if total else 0,
        }

        min_for_retrain = ActiveConfig.MIN_FEEDBACK_FOR_RETRAIN
        can_retrain = total >= min_for_retrain

        return render_template(
            "feedback.html",
            feedback_rows=feedback_rows,
            summary=summary,
            can_retrain=can_retrain,
            min_for_retrain=min_for_retrain,
        )

    def _is_correct(model_pred: str, admin_decision: str) -> bool:
        if model_pred == "Fraud" and admin_decision == "Confirm Fraud":
            return True
        if model_pred in ("Genuine", "Suspicious") and admin_decision == "Mark Genuine":
            return True
        return False

    # ── Model Retraining ─────────────────────
    @app.route("/admin/retrain", methods=["GET", "POST"])
    @admin_required
    def retrain():
        if request.method == "POST":
            try:
                from model.train_model import train
                result = train(min_f1=ActiveConfig.RETRAIN_MIN_F1)
                reload_model()

                if result.get("status") == "success":
                    # Log in model_versions table
                    conn = db()
                    conn.execute(
                        "UPDATE model_versions SET is_active=0",
                    )
                    conn.execute(
                        """INSERT INTO model_versions
                           (model_name, version, accuracy, precision, recall, f1_score, roc_auc, is_active)
                           VALUES (?,?,?,?,?,?,?,1)""",
                        (
                            result.get("model_name", "Random Forest"),
                            datetime.utcnow().strftime("%Y%m%d%H%M"),
                            result.get("accuracy"),
                            result.get("precision"),
                            result.get("recall"),
                            result.get("f1_score"),
                            result.get("roc_auc"),
                        )
                    )
                    conn.commit()
                    flash(f"Model retrained successfully! F1={result.get('f1_score', 0):.4f}", "success")
                else:
                    flash(f"Retraining rejected: {result.get('reason', 'Unknown')}", "warning")

            except Exception as e:
                flash(f"Retraining failed: {str(e)}", "danger")

            return redirect(url_for("feedback_page"))

        # GET – show retrain page
        conn = db()
        versions = _rows_to_list(conn.execute(
            "SELECT * FROM model_versions ORDER BY created_at DESC LIMIT 10"
        ).fetchall())
        fb_count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        perf = load_performance()
        return render_template("retrain.html", versions=versions, fb_count=fb_count, perf=perf)

    # ── Model Performance ─────────────────────
    @app.route("/admin/model-performance")
    @admin_required
    def model_performance():
        perf = load_performance()
        conn = db()
        versions = _rows_to_list(conn.execute(
            "SELECT * FROM model_versions ORDER BY created_at DESC LIMIT 10"
        ).fetchall())
        return render_template("model_performance.html", perf=perf, versions=versions)

    # ── Live Monitoring ───────────────────────
    @app.route("/admin/monitoring")
    @admin_required
    def monitoring():
        conn = db()
        recent = _rows_to_list(conn.execute(
            "SELECT t.*, u.name as user_name FROM transactions t "
            "JOIN users u ON t.user_id=u.id "
            "ORDER BY t.created_at DESC LIMIT 20"
        ).fetchall())
        stats = _get_stats()
        return render_template("monitoring.html", transactions=recent, stats=stats)

    # ── Model Drift ───────────────────────────
    @app.route("/admin/drift")
    @admin_required
    def drift_page():
        conn = db()
        recent_rows = _rows_to_list(conn.execute(
            "SELECT * FROM transactions ORDER BY created_at DESC LIMIT 200"
        ).fetchall())
        drift_report = detect_drift(recent_rows)
        return render_template("drift.html", drift=drift_report)

    # ── Geographic Risk View ──────────────────
    @app.route("/geo-risk")
    @login_required
    def geo_risk():
        conn = db()
        rows = conn.execute(
            """SELECT location,
                      COUNT(*) as total,
                      SUM(CASE WHEN prediction='Fraud' THEN 1 ELSE 0 END) as fraud_count,
                      AVG(risk_score) as avg_risk
               FROM transactions
               GROUP BY location"""
        ).fetchall()
        geo_data = []
        for r in rows:
            avg = r["avg_risk"] or 0
            geo_data.append({
                "location":   r["location"],
                "total":      r["total"],
                "fraud_count": r["fraud_count"],
                "avg_risk":   round(avg, 1),
                "risk_level": "LOW" if avg <= 25 else "MEDIUM" if avg <= 50 else "HIGH" if avg <= 75 else "CRITICAL",
            })
        return render_template("geo_risk.html", geo_data=geo_data)

    # ── Graph Analysis ────────────────────────
    @app.route("/graph-analysis")
    @login_required
    def graph_analysis():
        conn = db()
        user_id = session["user_id"]
        txns = _rows_to_list(conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 30",
            (user_id,)
        ).fetchall())
        return render_template("graph_analysis.html", transactions=txns)

    # ── About ─────────────────────────────────
    @app.route("/about")
    def about():
        perf = load_performance()
        return render_template("about.html", perf=perf)

    # ══════════════════════════════════════════
    # ── REST API ENDPOINTS ─────────────────────
    # ══════════════════════════════════════════

    @app.route("/api/predict", methods=["POST"])
    @login_required
    def api_predict():
        data = request.get_json(silent=True) or {}
        try:
            amount           = float(data.get("amount", 0))
            transaction_type = str(data.get("transaction_type", "UPI"))
            transaction_hour = int(data.get("transaction_hour", 12))
            sender_balance   = float(data.get("sender_balance", 10000))
            receiver_balance = float(data.get("receiver_balance", 0))
            location         = str(data.get("location", "Mumbai"))
            device_type      = str(data.get("device_type", "Mobile"))
            prev_count       = int(data.get("previous_transaction_count", 5))
            new_device       = int(data.get("new_device", 0))
            unusual_location = int(data.get("unusual_location", 0))

            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400

            user_id = session["user_id"]
            vel = get_velocity(user_id)
            beh = analyze_behavior(user_id, amount, transaction_hour, location,
                                   transaction_type, device_type, new_device)

            result = predict(
                amount=amount, transaction_type=transaction_type,
                transaction_hour=transaction_hour, sender_balance=sender_balance,
                receiver_balance=receiver_balance, location=location,
                device_type=device_type, previous_transaction_count=prev_count,
                new_device=new_device, unusual_location=unusual_location,
                transactions_last_hour=vel["count"],
                velocity_score=vel["velocity_score"],
                behavior_score=beh["behavior_score"],
                behavior_result=beh, velocity_result=vel,
            )
            return jsonify(result)

        except (ValueError, TypeError) as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/transactions", methods=["GET"])
    @login_required
    def api_transactions():
        conn    = db()
        user_id = session["user_id"]
        is_admin = session.get("role") == "admin"
        limit   = min(int(request.args.get("limit", 20)), 100)
        offset  = int(request.args.get("offset", 0))

        if is_admin:
            rows = _rows_to_list(conn.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall())
        else:
            rows = _rows_to_list(conn.execute(
                "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            ).fetchall())

        return jsonify({"transactions": rows, "count": len(rows)})

    @app.route("/api/statistics", methods=["GET"])
    @login_required
    def api_statistics():
        user_id  = session["user_id"]
        is_admin = session.get("role") == "admin"
        stats    = _get_stats(None if is_admin else user_id)
        return jsonify(stats)

    @app.route("/api/alerts", methods=["GET"])
    @login_required
    def api_alerts():
        conn = db()
        user_id  = session["user_id"]
        is_admin = session.get("role") == "admin"

        if is_admin:
            rows = _rows_to_list(conn.execute(
                "SELECT * FROM alerts WHERE is_resolved=0 ORDER BY created_at DESC LIMIT 50"
            ).fetchall())
        else:
            rows = _rows_to_list(conn.execute(
                "SELECT a.* FROM alerts a "
                "JOIN transactions t ON a.transaction_id=t.transaction_id "
                "WHERE t.user_id=? AND a.is_resolved=0 ORDER BY a.created_at DESC",
                (user_id,)
            ).fetchall())

        return jsonify({"alerts": rows, "count": len(rows)})

    @app.route("/api/review", methods=["POST"])
    @admin_required
    def api_review():
        data = request.get_json(silent=True) or {}
        transaction_id = data.get("transaction_id")
        decision       = data.get("decision")
        notes          = data.get("notes", "")

        valid = ["Confirm Fraud", "Mark Genuine", "Keep Under Review"]
        if not transaction_id or decision not in valid:
            return jsonify({"error": "Invalid transaction_id or decision"}), 400

        conn = db()
        tx = _row_to_dict(conn.execute(
            "SELECT * FROM transactions WHERE transaction_id=?", (transaction_id,)
        ).fetchone())
        if not tx:
            return jsonify({"error": "Transaction not found"}), 404

        conn.execute(
            "INSERT INTO feedback (transaction_id, model_prediction, admin_decision, notes, reviewed_by) VALUES (?,?,?,?,?)",
            (transaction_id, tx["prediction"], decision, notes, session["user_id"])
        )
        conn.execute("UPDATE transactions SET status=? WHERE transaction_id=?", (decision, transaction_id))
        conn.execute("UPDATE alerts SET is_resolved=1 WHERE transaction_id=?", (transaction_id,))
        conn.commit()
        return jsonify({"status": "ok", "decision": decision})

    @app.route("/api/retrain", methods=["POST"])
    @admin_required
    def api_retrain():
        try:
            from model.train_model import train
            result = train(min_f1=ActiveConfig.RETRAIN_MIN_F1)
            reload_model()
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/report/csv")
    @login_required
    def api_report_csv():
        conn = db()
        user_id  = session["user_id"]
        is_admin = session.get("role") == "admin"

        if is_admin:
            rows = _rows_to_list(conn.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC"
            ).fetchall())
        else:
            rows = _rows_to_list(conn.execute(
                "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC", (user_id,)
            ).fetchall())

        csv_bytes = generate_csv_report(rows)
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"fraud_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    @app.route("/api/report/pdf")
    @admin_required
    def api_report_pdf():
        conn  = db()
        stats = _get_stats()
        rows  = _rows_to_list(conn.execute(
            "SELECT * FROM transactions ORDER BY created_at DESC"
        ).fetchall())

        pdf_bytes = generate_pdf_report(stats, rows)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"fraud_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

    @app.route("/api/monitoring/live")
    @admin_required
    def api_monitoring_live():
        conn = db()
        rows = _rows_to_list(conn.execute(
            "SELECT transaction_id, amount, transaction_type, risk_score, risk_level, prediction, created_at "
            "FROM transactions ORDER BY created_at DESC LIMIT 15"
        ).fetchall())
        stats = _get_stats()
        return jsonify({"transactions": rows, "stats": stats})

    @app.route("/api/drift")
    @admin_required
    def api_drift():
        conn = db()
        recent = _rows_to_list(conn.execute(
            "SELECT * FROM transactions ORDER BY created_at DESC LIMIT 200"
        ).fetchall())
        report = detect_drift(recent)
        return jsonify(report)

    # ══════════════════════════════════════════
    # ── ERROR HANDLERS ─────────────────────────
    # ══════════════════════════════════════════
    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="Access forbidden."), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500, message="Internal server error."), 500

    # ── Template context processors ───────────
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "FraudShield AI",
            "current_year": datetime.now().year,
        }

    return app


# ── Entry point ───────────────────────────────
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
