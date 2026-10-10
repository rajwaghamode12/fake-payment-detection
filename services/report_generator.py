"""
report_generator.py - Fraud Report Generation (PDF + CSV)
AI-Based Online Payment Fraud Detection System
"""

import os
import sys
import csv
import json
import io
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import ActiveConfig


def _load_performance() -> dict:
    path = ActiveConfig.MODEL_PERFORMANCE_PATH
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


# ══════════════════════════════════════════════
# CSV REPORT
# ══════════════════════════════════════════════
def generate_csv_report(transactions: list[dict]) -> bytes:
    """
    Generate a CSV bytes object from a list of transaction dicts.
    """
    if not transactions:
        return b"No transactions found.\n"

    fieldnames = [
        "transaction_id", "amount", "transaction_type", "transaction_time",
        "location", "device_type", "risk_score", "risk_level",
        "prediction", "fraud_probability", "status", "created_at",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for tx in transactions:
        writer.writerow(tx)

    return output.getvalue().encode("utf-8")


# ══════════════════════════════════════════════
# PDF REPORT
# ══════════════════════════════════════════════
def generate_pdf_report(stats: dict, transactions: list[dict]) -> bytes:
    """
    Generate a PDF fraud report using ReportLab.
    Falls back to a plain-text PDF if ReportLab is unavailable.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title2", parent=styles["Title"],
            fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a1a2e")
        )
        h2_style = ParagraphStyle(
            "H2", parent=styles["Heading2"],
            fontSize=13, textColor=colors.HexColor("#16213e"), spaceAfter=4
        )
        body_style = styles["Normal"]

        elements = []

        # ── Header ────────────────────────────
        elements.append(Paragraph("Online Payment Fraud Detection Report", title_style))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
            f"System: AI-Based Fraud Detection  |  Dataset: Synthetic/Demo",
            body_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.4*cm))

        # ── Summary Statistics ────────────────
        elements.append(Paragraph("1. Summary Statistics", h2_style))
        summary_data = [
            ["Metric", "Value"],
            ["Total Transactions",      str(stats.get("total", 0))],
            ["Genuine Transactions",    str(stats.get("genuine", 0))],
            ["Suspicious Transactions", str(stats.get("suspicious", 0))],
            ["Fraud Predictions",       str(stats.get("fraud", 0))],
            ["Fraud Rate",              f"{stats.get('fraud_rate', 0):.1f}%"],
            ["Average Risk Score",      f"{stats.get('avg_risk_score', 0):.1f} / 100"],
            ["High-Risk Transactions",  str(stats.get("high_risk", 0))],
        ]
        t = Table(summary_data, colWidths=[8*cm, 6*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTSIZE",   (0, 0), (-1, -1), 10),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))

        # ── Model Performance ─────────────────
        perf = _load_performance()
        best = perf.get("best_model", "Random Forest")
        models_data = perf.get("models", {})
        best_metrics = models_data.get(best, {})

        elements.append(Paragraph("2. Model Performance", h2_style))
        elements.append(Paragraph(f"Best Performing Model: {best}", body_style))
        elements.append(Spacer(1, 0.2*cm))

        if best_metrics:
            perf_table_data = [
                ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"],
            ]
            for model_name, m in models_data.items():
                perf_table_data.append([
                    model_name,
                    f"{m.get('accuracy', 0):.4f}",
                    f"{m.get('precision', 0):.4f}",
                    f"{m.get('recall', 0):.4f}",
                    f"{m.get('f1_score', 0):.4f}",
                    f"{m.get('roc_auc', 0):.4f}",
                ])
            pt = Table(perf_table_data, colWidths=[4.5*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm])
            pt.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#16213e")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("PADDING",     (0, 0), (-1, -1), 5),
                ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ]))
            elements.append(pt)
        elements.append(Spacer(1, 0.5*cm))

        # ── Top Risk Factors ──────────────────
        fi = perf.get("feature_importance", {})
        if fi:
            elements.append(Paragraph("3. Top Risk Factors (Feature Importance)", h2_style))
            sorted_fi = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:10]
            fi_data = [["Feature", "Importance"]] + [
                [name.replace("_", " ").title(), f"{val:.4f}"]
                for name, val in sorted_fi
            ]
            fit = Table(fi_data, colWidths=[10*cm, 4*cm])
            fit.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("PADDING",     (0, 0), (-1, -1), 5),
            ]))
            elements.append(fit)
            elements.append(Spacer(1, 0.5*cm))

        # ── Recent Transactions ───────────────
        if transactions:
            elements.append(Paragraph("4. Recent Flagged Transactions (High/Critical)", h2_style))
            flagged = [t for t in transactions if t.get("risk_level") in ("HIGH", "CRITICAL")][:20]
            if flagged:
                tx_data = [["TX ID", "Amount (₹)", "Type", "Risk Score", "Level", "Prediction"]]
                for tx in flagged:
                    tx_data.append([
                        str(tx.get("transaction_id", "")),
                        f"{float(tx.get('amount', 0)):,.0f}",
                        str(tx.get("transaction_type", "")),
                        str(tx.get("risk_score", "")),
                        str(tx.get("risk_level", "")),
                        str(tx.get("prediction", "")),
                    ])
                txt = Table(tx_data, colWidths=[3.5*cm, 2.8*cm, 2.8*cm, 2.5*cm, 2.2*cm, 2.7*cm])
                txt.setStyle(TableStyle([
                    ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#e94560")),
                    ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                    ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff5f5")]),
                    ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("FONTSIZE",    (0, 0), (-1, -1), 8),
                    ("PADDING",     (0, 0), (-1, -1), 4),
                ]))
                elements.append(txt)
            else:
                elements.append(Paragraph("No high/critical transactions found.", body_style))

        elements.append(Spacer(1, 0.5*cm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Paragraph(
            "DISCLAIMER: This report is generated from a synthetic/demo dataset for academic purposes only. "
            "It does not reflect real financial data or real banking transactions.",
            ParagraphStyle("disclaimer", parent=body_style, fontSize=8, textColor=colors.grey)
        ))

        doc.build(elements)
        return buffer.getvalue()

    except ImportError:
        # Fallback plain-text content
        lines = [
            "ONLINE PAYMENT FRAUD DETECTION REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "ReportLab is not installed. Please install it with:",
            "  pip install reportlab",
            "",
            "Summary Statistics:",
            f"  Total Transactions     : {stats.get('total', 0)}",
            f"  Genuine                : {stats.get('genuine', 0)}",
            f"  Suspicious             : {stats.get('suspicious', 0)}",
            f"  Fraud Predictions      : {stats.get('fraud', 0)}",
            f"  Average Risk Score     : {stats.get('avg_risk_score', 0):.1f}",
        ]
        return "\n".join(lines).encode("utf-8")
