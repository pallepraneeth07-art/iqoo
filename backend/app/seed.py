import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import User, Transaction, ReconciliationRecord, RecoveryAction, Alert, AnomalyEvent
from .engines.failure_engine import evaluate_transaction_status
from .engines.recon_engine import run_3way_reconciliation
from .engines.ai_engine import detect_system_anomalies

MERCHANTS = [
    {"id": "M101", "name": "Flipkart India"},
    {"id": "M102", "name": "Amazon Pay"},
    {"id": "M103", "name": "Swiggy Foods"},
    {"id": "M104", "name": "Zomato Media"},
    {"id": "M105", "name": "Uber Rides"},
    {"id": "M106", "name": "BookMyShow"},
    {"id": "M107", "name": "Reliance Retail"},
]

def seed_initial_data(db: Session):
    # Check if data already exists
    if db.query(Transaction).count() > 0:
        return

    print("Seeding initial 30+ UPI transactions and demo records...")

    # 1. Create Default Users
    admin_user = User(name="Operations Admin", email="admin@upi-control.internal", role="Admin")
    merchant_user = User(name="Merchant Manager", email="merchant@flipkart.com", role="Merchant")
    db.add_all([admin_user, merchant_user])
    db.commit()

    transactions = []
    base_time = datetime.utcnow() - timedelta(days=2)

    # Helper generator
    def create_txn(txn_num, g_st, b_st, m_st, is_dup=False, amt=None, m_idx=None):
        nonlocal base_time
        t_id = f"TXN10{txn_num:03d}"
        upi_ref = f"UPI{random.randint(1000000000, 9999999999)}"
        c_id = f"CUST_{random.randint(1000, 9999)}"
        m_info = MERCHANTS[m_idx if m_idx is not None else random.randint(0, len(MERCHANTS)-1)]
        amount = amt if amt else round(random.uniform(150, 4500), 2)
        
        # Advance timestamp randomly
        base_time += timedelta(minutes=random.randint(12, 120))

        final_st, fail_reason, recov_st, recon_st = evaluate_transaction_status(g_st, b_st, m_st, is_duplicate=is_dup)

        t = Transaction(
            transaction_id=t_id,
            upi_reference=upi_ref,
            customer_id=c_id,
            merchant_id=m_info["id"],
            merchant_name=m_info["name"],
            amount=amount,
            timestamp=base_time,
            gateway_status=g_st,
            bank_status=b_st,
            merchant_status=m_st,
            final_status=final_st,
            failure_reason=fail_reason,
            recovery_status=recov_st,
            reconciliation_status=recon_st,
            created_at=base_time,
            updated_at=base_time
        )
        return t

    counter = 1

    # A) 15 Successful Payments
    for i in range(15):
        t = create_txn(counter, "SUCCESS", "SUCCESS", "SUCCESS")
        transactions.append(t)
        counter += 1

    # B) 5 Clean Failed Payments (Bank NOT debited)
    for i in range(5):
        t = create_txn(counter, "FAILED", "NOT_DEBITED", "NOT_CREDITED")
        transactions.append(t)
        counter += 1

    # C) 3 Pending Payments
    for i in range(3):
        t = create_txn(counter, "PENDING", "PENDING", "PENDING")
        transactions.append(t)
        counter += 1

    # D) 3 Debited but Not Credited Payments (Critical Failure)
    for i in range(3):
        t = create_txn(counter, "TIMEOUT", "DEBITED", "NOT_CREDITED", amt=1250.00 + (i*500))
        transactions.append(t)
        counter += 1

    # E) 2 Duplicate Transactions
    for i in range(2):
        t = create_txn(counter, "SUCCESS", "SUCCESS", "SUCCESS", is_dup=True, amt=750.00)
        transactions.append(t)
        counter += 1

    # F) 2 Reconciliation Exceptions (Missing from merchant / status mismatch)
    for i in range(2):
        t = create_txn(counter, "SUCCESS", "SUCCESS", "MISSING", amt=2999.00)
        transactions.append(t)
        counter += 1

    db.add_all(transactions)
    db.commit()

    # Create alerts for critical & warning items
    for t in transactions:
        if t.final_status == "DEBITED_NOT_CREDITED":
            alert = Alert(
                transaction_id=t.transaction_id,
                severity="CRITICAL",
                alert_type="DEBITED_NOT_CREDITED",
                message=f"Customer debited ₹{t.amount} at Bank, but Merchant {t.merchant_name} not credited due to Gateway timeout.",
                recommended_action="Verify status via Recovery Center before retrying or refunding.",
                status="ACTIVE",
                created_at=t.timestamp
            )
            db.add(alert)
        elif t.final_status == "DUPLICATE":
            alert = Alert(
                transaction_id=t.transaction_id,
                severity="WARNING",
                alert_type="POSSIBLE_DUPLICATE",
                message=f"Potential duplicate transaction detected for UPI Reference {t.upi_reference}.",
                recommended_action="Block automatic re-execution.",
                status="ACTIVE",
                created_at=t.timestamp
            )
            db.add(alert)
        elif t.final_status == "RECONCILIATION_EXCEPTION":
            alert = Alert(
                transaction_id=t.transaction_id,
                severity="WARNING",
                alert_type="MERCHANT_RECORD_MISSING",
                message=f"Gateway & Bank marked success, but Merchant {t.merchant_name} record is missing.",
                recommended_action="Run 3-way reconciliation sync.",
                status="ACTIVE",
                created_at=t.timestamp
            )
            db.add(alert)

    db.commit()

    # Run automated reconciliation & anomaly scans on initial dataset
    run_3way_reconciliation(db)
    detect_system_anomalies(db)

    print("Seed complete: 30 transactions populated successfully.")
