import random
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Transaction, Alert
from ..schemas import TransactionSimulateRequest, TransactionSchema
from ..engines.failure_engine import evaluate_transaction_status
from ..engines.recon_engine import run_3way_reconciliation
from ..engines.ai_engine import detect_system_anomalies

router = APIRouter(prefix="/api/transactions/simulate", tags=["Simulator"])

MERCHANT_POOL = [
    {"id": "M101", "name": "Flipkart India"},
    {"id": "M102", "name": "Amazon Pay"},
    {"id": "M103", "name": "Swiggy Foods"},
    {"id": "M104", "name": "Zomato Media"},
    {"id": "M105", "name": "Uber Rides"},
]

@router.post("", response_model=TransactionSchema)
def simulate_transaction(req: TransactionSimulateRequest, db: Session = Depends(get_db)):
    """
    Simulates a live end-to-end UPI transaction scenario for presentation demos.
    Scenarios:
    - SUCCESS
    - FAILED
    - PENDING
    - DEBITED_NOT_CREDITED
    - DUPLICATE
    - RECONCILIATION_MISMATCH
    """
    m_info = random.choice(MERCHANT_POOL)
    if req.custom_merchant:
        m_info = {"id": f"M{random.randint(200, 999)}", "name": req.custom_merchant}

    amount = req.custom_amount if req.custom_amount else round(random.uniform(200.0, 5000.0), 2)
    next_seq = db.query(Transaction).count() + 10001
    t_id = f"TXN{next_seq}"
    upi_ref = f"UPI{random.randint(1000000000, 9999999999)}"
    cust_id = f"CUST_{random.randint(1000, 9999)}"

    scenario = req.scenario.upper()

    is_dup = False
    g_st = "SUCCESS"
    b_st = "SUCCESS"
    m_st = "SUCCESS"

    if scenario == "SUCCESS":
        g_st, b_st, m_st = "SUCCESS", "SUCCESS", "SUCCESS"

    elif scenario == "FAILED":
        g_st, b_st, m_st = "FAILED", "NOT_DEBITED", "NOT_CREDITED"

    elif scenario == "PENDING":
        g_st, b_st, m_st = "PENDING", "PENDING", "PENDING"

    elif scenario == "DEBITED_NOT_CREDITED":
        g_st, b_st, m_st = "TIMEOUT", "DEBITED", "NOT_CREDITED"

    elif scenario == "DUPLICATE":
        is_dup = True
        g_st, b_st, m_st = "SUCCESS", "SUCCESS", "SUCCESS"

    elif scenario == "RECONCILIATION_MISMATCH":
        g_st, b_st, m_st = "SUCCESS", "SUCCESS", "MISSING"

    else:
        raise HTTPException(status_code=400, detail=f"Unknown simulation scenario: {scenario}")

    # Run Failure Detection Engine
    final_st, fail_reason, recov_st, recon_st = evaluate_transaction_status(g_st, b_st, m_st, is_duplicate=is_dup)

    now = datetime.utcnow()
    new_txn = Transaction(
        transaction_id=t_id,
        upi_reference=upi_ref,
        customer_id=cust_id,
        merchant_id=m_info["id"],
        merchant_name=m_info["name"],
        amount=amount,
        timestamp=now,
        gateway_status=g_st,
        bank_status=b_st,
        merchant_status=m_st,
        final_status=final_st,
        failure_reason=fail_reason,
        recovery_status=recov_st,
        reconciliation_status=recon_st,
        created_at=now,
        updated_at=now
    )

    db.add(new_txn)
    db.commit()

    # Trigger alert if problematic
    if final_st == "DEBITED_NOT_CREDITED":
        alert = Alert(
            transaction_id=t_id,
            severity="CRITICAL",
            alert_type="DEBITED_NOT_CREDITED",
            message=f"SIMULATED ALERT: Customer debited ₹{amount} at Bank, but Merchant {m_info['name']} not credited due to Gateway timeout.",
            recommended_action="Verify transaction status before retrying.",
            status="ACTIVE",
            created_at=now
        )
        db.add(alert)
    elif final_st == "DUPLICATE":
        alert = Alert(
            transaction_id=t_id,
            severity="WARNING",
            alert_type="POSSIBLE_DUPLICATE",
            message=f"SIMULATED ALERT: Duplicate UPI reference {upi_ref} detected.",
            recommended_action="Block duplicate payment retry.",
            status="ACTIVE",
            created_at=now
        )
        db.add(alert)
    elif final_st == "RECONCILIATION_EXCEPTION":
        alert = Alert(
            transaction_id=t_id,
            severity="WARNING",
            alert_type="MERCHANT_MISSING",
            message=f"SIMULATED ALERT: Transaction missing from Merchant ledger.",
            recommended_action="Run 3-way reconciliation.",
            status="ACTIVE",
            created_at=now
        )
        db.add(alert)

    db.commit()

    # Automatically run 3-way reconciliation sync & anomaly scanning
    run_3way_reconciliation(db)
    detect_system_anomalies(db)

    db.refresh(new_txn)
    return new_txn
