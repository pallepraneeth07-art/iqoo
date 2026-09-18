from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import ReconciliationRecord
from ..schemas import ReconciliationRecordSchema
from ..engines.recon_engine import run_3way_reconciliation

router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliation"])

@router.post("/run")
def trigger_reconciliation(db: Session = Depends(get_db)):
    summary = run_3way_reconciliation(db)
    return summary

@router.get("/records", response_model=List[ReconciliationRecordSchema])
def get_reconciliation_records(db: Session = Depends(get_db)):
    records = db.query(ReconciliationRecord).order_by(ReconciliationRecord.created_at.desc()).all()
    return records

@router.get("/exceptions", response_model=List[ReconciliationRecordSchema])
def get_reconciliation_exceptions(db: Session = Depends(get_db)):
    exceptions = db.query(ReconciliationRecord).filter(
        ReconciliationRecord.reconciliation_result != "MATCHED"
    ).order_by(ReconciliationRecord.created_at.desc()).all()
    return exceptions
