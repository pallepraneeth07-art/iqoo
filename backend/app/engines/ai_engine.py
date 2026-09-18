import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest
from ..models import Transaction, AnomalyEvent, Alert

def analyze_transaction_intelligence(transaction: Transaction) -> Dict[str, Any]:
    """
    Analyzes a specific transaction using rule-based decision tree and probability metrics.
    Returns:
    - failure_probability (0 to 1.0)
    - likely_reason
    - confidence (High, Medium, Low)
    - recommended_action
    - is_anomaly
    - anomaly_explanation
    """
    status = transaction.final_status
    g_status = transaction.gateway_status.upper()
    b_status = transaction.bank_status.upper()
    m_status = transaction.merchant_status.upper()

    if status == "SUCCESS":
        return {
            "transaction_id": transaction.transaction_id,
            "failure_probability": 0.02,
            "likely_reason": "None (Successful Payment)",
            "confidence": "High",
            "recommended_action": "No intervention required.",
            "is_anomaly": False,
            "anomaly_explanation": None
        }

    if status == "DEBITED_NOT_CREDITED":
        return {
            "transaction_id": transaction.transaction_id,
            "failure_probability": 0.94,
            "likely_reason": "Gateway / Merchant Network Timeout post-debit",
            "confidence": "High",
            "recommended_action": "Verify transaction status with Bank API before initiating retry or merchant credit.",
            "is_anomaly": True,
            "anomaly_explanation": "Customer account debited without merchant credit acknowledgment."
        }

    if status == "DUPLICATE":
        return {
            "transaction_id": transaction.transaction_id,
            "failure_probability": 0.98,
            "likely_reason": "High frequency double submission or VPA replay attack",
            "confidence": "High",
            "recommended_action": "Block duplicate request and review transaction queue.",
            "is_anomaly": True,
            "anomaly_explanation": "Identical UPI reference and customer payload received in rapid succession."
        }

    if status == "FAILED":
        return {
            "transaction_id": transaction.transaction_id,
            "failure_probability": 0.88,
            "likely_reason": "Insufficient Funds or Incorrect UPI PIN / User Cancellation",
            "confidence": "High",
            "recommended_action": "Safe to retry payment. Customer account was not debited.",
            "is_anomaly": False,
            "anomaly_explanation": None
        }

    if status == "PENDING":
        return {
            "transaction_id": transaction.transaction_id,
            "failure_probability": 0.45,
            "likely_reason": "Bank Switch Congestion or Delayed NPCI Acknowledgment",
            "confidence": "Medium",
            "recommended_action": "Monitor bank status callback. Do not trigger forced refund yet.",
            "is_anomaly": transaction.amount > 20000,
            "anomaly_explanation": "Pending status on unusually high transaction amount." if transaction.amount > 20000 else None
        }

    return {
        "transaction_id": transaction.transaction_id,
        "failure_probability": 0.70,
        "likely_reason": "System Status Mismatch",
        "confidence": "Medium",
        "recommended_action": "Run 3-way reconciliation check.",
        "is_anomaly": True,
        "anomaly_explanation": "Inconsistent state between Gateway, Bank, and Merchant logs."
    }


def detect_system_anomalies(db: Session) -> List[Dict[str, Any]]:
    """
    Uses Pandas & Scikit-learn (IsolationForest) + rule-based heuristics to scan
    all transactions for anomalous spikes (e.g. merchant failure rate spikes, amount anomalies).
    Automatically logs AnomalyEvents to DB if found.
    """
    transactions = db.query(Transaction).all()
    if not transactions:
        return []

    # Build DataFrame
    data = []
    for t in transactions:
        data.append({
            "id": t.id,
            "transaction_id": t.transaction_id,
            "merchant_id": t.merchant_id,
            "merchant_name": t.merchant_name,
            "amount": t.amount,
            "final_status": t.final_status,
            "is_failed": 1 if t.final_status in ["FAILED", "DEBITED_NOT_CREDITED", "MISMATCH"] else 0,
            "is_pending": 1 if t.final_status == "PENDING" else 0,
            "timestamp": t.timestamp
        })

    df = pd.DataFrame(data)

    anomalies_found = []

    # 1. Scikit-learn IsolationForest on Amount & Failure Indicator
    if len(df) >= 5:
        X = df[["amount", "is_failed", "is_pending"]].values
        clf = IsolationForest(contamination=0.15, random_state=42)
        preds = clf.fit_predict(X)
        df["anomaly_score"] = preds

        outliers = df[df["anomaly_score"] == -1]
        for _, row in outliers.iterrows():
            txn_id = row["transaction_id"]
            amt = row["amount"]
            st = row["final_status"]

            explanation = f"IsolationForest flagged transaction {txn_id} (₹{amt:,.2f}, Status: {st}) as a statistical outlier."
            anomalies_found.append({
                "transaction_id": txn_id,
                "anomaly_type": "STATISTICAL_OUTLIER",
                "confidence": 0.89,
                "explanation": explanation
            })

    # 2. Group-by Merchant Failure Rate Spike Detection
    merchant_stats = df.groupby("merchant_id").agg(
        total_count=("id", "count"),
        failed_count=("is_failed", "sum"),
        merchant_name=("merchant_name", "first")
    ).reset_index()

    for _, m_row in merchant_stats.iterrows():
        m_id = m_row["merchant_id"]
        m_name = m_row["merchant_name"]
        t_cnt = m_row["total_count"]
        f_cnt = m_row["failed_count"]
        failure_rate = (f_cnt / t_cnt) if t_cnt > 0 else 0

        if t_cnt >= 3 and failure_rate >= 0.40:
            exp = f"Merchant {m_name} ({m_id}) has experienced {f_cnt} failures out of {t_cnt} recent transactions ({failure_rate*100:.1f}% failure rate), significantly above baseline."
            anomalies_found.append({
                "transaction_id": None,
                "anomaly_type": "HIGH_MERCHANT_FAILURE_RATE",
                "confidence": 0.94,
                "explanation": exp
            })

    # Save to AnomalyEvents table if not already existing
    for item in anomalies_found:
        existing = db.query(AnomalyEvent).filter(
            AnomalyEvent.explanation == item["explanation"]
        ).first()
        if not existing:
            an_event = AnomalyEvent(
                transaction_id=item["transaction_id"],
                anomaly_type=item["anomaly_type"],
                confidence=item["confidence"],
                explanation=item["explanation"]
            )
            db.add(an_event)
            
            # Optionally create alert for high-confidence anomalies
            alert = Alert(
                transaction_id=item["transaction_id"],
                severity="WARNING" if item["confidence"] < 0.90 else "CRITICAL",
                alert_type="AI_ANOMALY_DETECTED",
                message=item["explanation"],
                recommended_action="Inspect merchant gateway health and switch routing.",
                status="ACTIVE"
            )
            db.add(alert)

    db.commit()
    return anomalies_found
