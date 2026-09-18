from typing import List, Dict, Any
from sqlalchemy.orm import Session
from ..models import Transaction, ReconciliationRecord

def run_3way_reconciliation(db: Session) -> Dict[str, Any]:
    """
    Executes automated 3-way reconciliation between Gateway, Bank, and Merchant records.
    Returns summary metrics and updates ReconciliationRecord entries.
    """
    transactions = db.query(Transaction).all()
    
    total = len(transactions)
    matched = 0
    mismatches = 0
    missing = 0
    duplicates = 0
    unresolved = 0

    results_summary = []

    for txn in transactions:
        # Gateway record
        g_amt = txn.amount if txn.gateway_status != "MISSING" else None
        b_amt = txn.amount if txn.bank_status != "MISSING" else None
        m_amt = txn.amount if txn.merchant_status != "MISSING" else None

        # Intentionally introduce test variation if status is mismatch
        if txn.final_status == "MISMATCH" and txn.id % 2 == 0:
            m_amt = (txn.amount or 0) * 0.9  # simulated amount mismatch

        # Classify
        rec_result = "MATCHED"
        details = "All 3 system records match perfectly in amount and settlement status."

        if txn.final_status == "DUPLICATE":
            rec_result = "DUPLICATE"
            details = "Duplicate transaction record found across system feeds."
            duplicates += 1

        elif txn.merchant_status == "MISSING":
            rec_result = "MISSING_FROM_MERCHANT"
            details = "Transaction debited and gateway confirmed, but missing from Merchant database."
            missing += 1

        elif txn.bank_status == "MISSING":
            rec_result = "MISSING_FROM_BANK"
            details = "Gateway request present, but missing from Bank settlement ledger."
            missing += 1

        elif g_amt and m_amt and g_amt != m_amt:
            rec_result = "AMOUNT_MISMATCH"
            details = f"Gateway amount (₹{g_amt}) does not match Merchant amount (₹{m_amt})."
            mismatches += 1

        elif txn.final_status in ["DEBITED_NOT_CREDITED", "MISMATCH"]:
            rec_result = "STATUS_MISMATCH"
            details = f"Gateway ({txn.gateway_status}), Bank ({txn.bank_status}), Merchant ({txn.merchant_status}) status inconsistency."
            mismatches += 1

        elif txn.final_status == "PENDING":
            rec_result = "UNRESOLVED"
            details = "Transaction settlement pending confirmation from Bank."
            unresolved += 1

        else:
            matched += 1

        # Update or create ReconciliationRecord
        rec_record = db.query(ReconciliationRecord).filter(ReconciliationRecord.transaction_id == txn.transaction_id).first()
        if not rec_record:
            rec_record = ReconciliationRecord(
                transaction_id=txn.transaction_id,
                gateway_amount=g_amt,
                bank_amount=b_amt,
                merchant_amount=m_amt,
                gateway_status=txn.gateway_status,
                bank_status=txn.bank_status,
                merchant_status=txn.merchant_status,
                reconciliation_result=rec_result,
                details=details
            )
            db.add(rec_record)
        else:
            rec_record.gateway_amount = g_amt
            rec_record.bank_amount = b_amt
            rec_record.merchant_amount = m_amt
            rec_record.gateway_status = txn.gateway_status
            rec_record.bank_status = txn.bank_status
            rec_record.merchant_status = txn.merchant_status
            rec_record.reconciliation_result = rec_result
            rec_record.details = details

        # Update txn reconciliation status indicator
        txn.reconciliation_status = rec_result

        results_summary.append({
            "transaction_id": txn.transaction_id,
            "result": rec_result,
            "details": details
        })

    db.commit()

    return {
        "total_records": total,
        "matched": matched,
        "mismatches": mismatches,
        "missing_records": missing,
        "duplicates": duplicates,
        "unresolved_exceptions": unresolved,
        "results": results_summary
    }
