import uuid
from datetime import datetime
from typing import Tuple, Any
from sqlalchemy.orm import Session
from ..models import Transaction, RecoveryAction, Alert

def execute_recovery_action(
    db: Session,
    transaction: Transaction,
    action_type: str,
    reason: str,
    idempotency_key: str = None
) -> Tuple[Any, bool, str]:
    """
    Executes a recovery action safely with idempotency.
    Supported action_types:
    - VERIFY_STATUS: Re-queries bank/gateway API mock.
    - RETRY_TRANSACTION: Safe retry if customer was not debited.
    - REFUND_CUSTOMER: Triggers simulated refund to customer account.
    - CREDIT_MERCHANT: Force credits merchant ledger after verifying debit.
    - MARK_INVESTIGATION: Places transaction in manual queue.
    - RESOLVE: Marks exception as resolved.
    """
    if not idempotency_key:
        idempotency_key = f"REC_{transaction.transaction_id}_{action_type}_{uuid.uuid4().hex[:8]}"

    # Check idempotency
    existing_action = db.query(RecoveryAction).filter(RecoveryAction.idempotency_key == idempotency_key).first()
    if existing_action:
        return existing_action, False, "Duplicate action ignored (idempotency key matched)"

    # Create action record
    action_record = RecoveryAction(
        transaction_id=transaction.transaction_id,
        action_type=action_type,
        reason=reason,
        status="IN_PROGRESS",
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow()
    )
    db.add(action_record)
    db.commit()

    message = ""
    # Process simulated logic
    if action_type == "VERIFY_STATUS":
        if transaction.final_status == "DEBITED_NOT_CREDITED":
            transaction.recovery_status = "VERIFICATION_PENDING"
            message = "Bank debited confirmed. Recommended next step: Execute CREDIT_MERCHANT or REFUND_CUSTOMER."
        else:
            message = "Transaction status verified with core banking gateway."

    elif action_type == "CREDIT_MERCHANT":
        transaction.merchant_status = "CREDITED"
        transaction.final_status = "RESOLVED"
        transaction.recovery_status = "RESOLVED"
        transaction.reconciliation_status = "MATCHED"
        message = "Merchant wallet/account successfully credited. Transaction resolved."

    elif action_type == "REFUND_CUSTOMER":
        transaction.final_status = "REFUND_PENDING"
        transaction.recovery_status = "REFUNDED"
        message = "Simulated refund initiated to customer's source account."

    elif action_type == "RETRY_TRANSACTION":
        if transaction.bank_status in ["DEBITED", "SUCCESS"]:
            action_record.status = "FAILED"
            db.commit()
            return action_record, False, "BLOCKED: Retry rejected because customer was already debited! Use VERIFY_STATUS or CREDIT_MERCHANT instead."
        transaction.final_status = "PENDING"
        transaction.recovery_status = "IN_PROGRESS"
        message = "New payment request initiated safely."

    elif action_type == "MARK_INVESTIGATION":
        transaction.recovery_status = "IN_PROGRESS"
        message = "Flagged for manual compliance & financial ops review."

    elif action_type == "RESOLVE":
        transaction.final_status = "RESOLVED"
        transaction.recovery_status = "RESOLVED"
        transaction.reconciliation_status = "MATCHED"
        message = "Transaction marked as resolved by operator."

    action_record.status = "COMPLETED"
    action_record.completed_at = datetime.utcnow()

    # Resolve related active alerts if transaction resolved
    if transaction.final_status in ["RESOLVED", "SUCCESS"]:
        alerts = db.query(Alert).filter(Alert.transaction_id == transaction.transaction_id, Alert.status == "ACTIVE").all()
        for alert in alerts:
            alert.status = "RESOLVED"

    db.commit()
    db.refresh(transaction)
    db.refresh(action_record)

    return action_record, True, message
