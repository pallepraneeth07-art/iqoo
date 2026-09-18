from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Transaction, ReconciliationRecord, RecoveryAction
from ..schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("", response_model=Dict[str, Any])
def get_analytics_dashboard_data(db: Session = Depends(get_db)):
    txns = db.query(Transaction).all()
    
    total_txns = len(txns)
    successful = sum(1 for t in txns if t.final_status in ["SUCCESS", "RESOLVED"])
    failed = sum(1 for t in txns if t.final_status in ["FAILED", "REFUND_PENDING"])
    pending = sum(1 for t in txns if t.final_status == "PENDING")
    recovery_required = sum(1 for t in txns if t.final_status in ["DEBITED_NOT_CREDITED", "DUPLICATE", "MISMATCH"] or t.recovery_status == "RECOVERY_REQUIRED")
    
    recon_records = db.query(ReconciliationRecord).all()
    recon_exceptions = sum(1 for r in recon_records if r.reconciliation_result != "MATCHED")

    total_value = sum(t.amount for t in txns)
    
    # Recovery success rate
    resolved_count = sum(1 for t in txns if t.final_status == "RESOLVED" or t.recovery_status in ["RESOLVED", "REFUNDED"])
    recovery_success_rate = (resolved_count / recovery_required * 100) if recovery_required > 0 else 100.0

    success_rate = (successful / total_txns * 100) if total_txns > 0 else 0.0

    # 1. Failure Reasons Breakdown
    failure_reasons_map = {}
    for t in txns:
        if t.failure_reason:
            short_reason = t.failure_reason.split(".")[0]
            failure_reasons_map[short_reason] = failure_reasons_map.get(short_reason, 0) + 1
        elif t.final_status != "SUCCESS":
            st = t.final_status
            failure_reasons_map[st] = failure_reasons_map.get(st, 0) + 1

    failure_reasons_chart = [{"reason": k, "count": v} for k, v in failure_reasons_map.items()]

    # 2. Status Distribution
    status_counts = {}
    for t in txns:
        status_counts[t.final_status] = status_counts.get(t.final_status, 0) + 1

    status_chart = [{"status": k, "count": v} for k, v in status_counts.items()]

    # 3. Merchant performance
    merchant_map = {}
    for t in txns:
        m_name = t.merchant_name or t.merchant_id
        if m_name not in merchant_map:
            merchant_map[m_name] = {"total": 0, "successful": 0, "failed": 0, "value": 0.0}
        merchant_map[m_name]["total"] += 1
        merchant_map[m_name]["value"] += t.amount
        if t.final_status in ["SUCCESS", "RESOLVED"]:
            merchant_map[m_name]["successful"] += 1
        else:
            merchant_map[m_name]["failed"] += 1

    merchant_list = []
    for m_name, m_data in merchant_map.items():
        rate = (m_data["successful"] / m_data["total"] * 100) if m_data["total"] > 0 else 0
        merchant_list.append({
            "merchant_name": m_name,
            "total": m_data["total"],
            "successful": m_data["successful"],
            "failed": m_data["failed"],
            "total_value": round(m_data["value"], 2),
            "success_rate": round(rate, 1)
        })

    # 4. Volume & Value over time (grouped by date/hour)
    timeline_map = {}
    for t in txns:
        date_str = t.timestamp.strftime("%Y-%m-%d %H:00") if t.timestamp else "2026-09-16 00:00"
        if date_str not in timeline_map:
            timeline_map[date_str] = {"timestamp": date_str, "volume": 0, "success": 0, "failure": 0, "value": 0.0}
        timeline_map[date_str]["volume"] += 1
        timeline_map[date_str]["value"] += t.amount
        if t.final_status in ["SUCCESS", "RESOLVED"]:
            timeline_map[date_str]["success"] += 1
        else:
            timeline_map[date_str]["failure"] += 1

    timeline_chart = sorted(list(timeline_map.values()), key=lambda x: x["timestamp"])

    return {
        "summary": {
            "total_transactions": total_txns,
            "successful_payments": successful,
            "failed_payments": failed,
            "pending_payments": pending,
            "recovery_required": recovery_required,
            "reconciliation_exceptions": recon_exceptions,
            "recovery_success_rate": round(recovery_success_rate, 1),
            "total_transaction_value": round(total_value, 2),
            "success_rate_percentage": round(success_rate, 1)
        },
        "charts": {
            "failure_reasons": failure_reasons_chart,
            "status_distribution": status_chart,
            "merchant_performance": merchant_list,
            "timeline": timeline_chart
        }
    }
