from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Transaction
from ..schemas import RecoveryActionRequest, RecoveryActionResponse, AIAnalysisResponse, TransactionSchema
from ..engines.recovery_engine import execute_recovery_action
from ..engines.ai_engine import analyze_transaction_intelligence

router = APIRouter(prefix="/api/recovery", tags=["Recovery Center"])

@router.get("/pending", response_model=List[TransactionSchema])
def get_recovery_pending_transactions(db: Session = Depends(get_db)):
    """Returns all transactions that require recovery intervention."""
    txns = db.query(Transaction).filter(
        Transaction.recovery_status.in_(["RECOVERY_REQUIRED", "VERIFICATION_PENDING", "IN_PROGRESS"])
    ).order_by(Transaction.timestamp.desc()).all()
    return txns

@router.post("/analyze/{id}", response_model=AIAnalysisResponse)
def analyze_recovery_transaction(id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(
        (Transaction.transaction_id == id) | (Transaction.id == int(id) if id.isdigit() else False)
    ).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    intel = analyze_transaction_intelligence(txn)
    return intel

@router.post("/verify/{id}")
def verify_transaction_status_endpoint(id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(
        (Transaction.transaction_id == id) | (Transaction.id == int(id) if id.isdigit() else False)
    ).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    action_record, success, message = execute_recovery_action(
        db=db,
        transaction=txn,
        action_type="VERIFY_STATUS",
        reason="Verification requested via Recovery Center"
    )

    return {
        "success": success,
        "message": message,
        "transaction_id": txn.transaction_id,
        "current_status": txn.final_status,
        "action_id": action_record.id
    }

@router.post("/execute/{id}")
def execute_recovery_action_endpoint(
    id: str,
    req: RecoveryActionRequest,
    db: Session = Depends(get_db)
):
    txn = db.query(Transaction).filter(
        (Transaction.transaction_id == id) | (Transaction.id == int(id) if id.isdigit() else False)
    ).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    action_record, success, message = execute_recovery_action(
        db=db,
        transaction=txn,
        action_type=req.action_type,
        reason=req.reason or "Recovery action executed",
        idempotency_key=req.idempotency_key
    )

    if not success and "BLOCKED" in message:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "transaction_id": txn.transaction_id,
        "new_status": txn.final_status,
        "recovery_status": txn.recovery_status,
        "action": RecoveryActionResponse.model_validate(action_record)
    }
