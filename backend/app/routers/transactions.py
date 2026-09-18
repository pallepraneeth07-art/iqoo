import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import Transaction
from ..schemas import TransactionSchema, TransactionCreate
from ..engines.failure_engine import evaluate_transaction_status

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionSchema])
def get_transactions(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    merchant_id: Optional[str] = None,
    search: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    limit: int = 200
):
    query = db.query(Transaction)

    if status:
        query = query.filter(Transaction.final_status == status)

    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)

    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Transaction.transaction_id.like(search_pattern)) |
            (Transaction.upi_reference.like(search_pattern)) |
            (Transaction.customer_id.like(search_pattern)) |
            (Transaction.merchant_name.like(search_pattern))
        )

    transactions = query.order_by(Transaction.timestamp.desc()).limit(limit).all()
    return transactions

@router.get("/export/csv")
def export_transactions_csv(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).order_by(Transaction.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Transaction ID", "UPI Reference", "Customer ID", "Merchant ID", "Merchant Name",
        "Amount (INR)", "Timestamp", "Gateway Status", "Bank Status", "Merchant Status",
        "Final Status", "Failure Reason", "Recovery Status", "Reconciliation Status"
    ])

    for t in transactions:
        writer.writerow([
            t.transaction_id, t.upi_reference, t.customer_id, t.merchant_id, t.merchant_name,
            t.amount, t.timestamp.isoformat() if t.timestamp else "", t.gateway_status, t.bank_status, t.merchant_status,
            t.final_status, t.failure_reason or "", t.recovery_status, t.reconciliation_status
        ])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=upi_transactions_report.csv"
    return response

@router.get("/{id}", response_model=TransactionSchema)
def get_transaction_by_id(id: str, db: Session = Depends(get_db)):
    # Match by internal ID or transaction_id
    txn = db.query(Transaction).filter(
        (Transaction.transaction_id == id) | (Transaction.id == int(id) if id.isdigit() else False)
    ).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return txn

@router.post("", response_model=TransactionSchema)
def create_transaction(txn_data: TransactionCreate, db: Session = Depends(get_db)):
    final_st, fail_reason, recov_st, recon_st = evaluate_transaction_status(
        txn_data.gateway_status,
        txn_data.bank_status,
        txn_data.merchant_status
    )

    new_txn = Transaction(
        transaction_id=txn_data.transaction_id,
        upi_reference=txn_data.upi_reference,
        customer_id=txn_data.customer_id,
        merchant_id=txn_data.merchant_id,
        merchant_name=txn_data.merchant_name or "Merchant Partner",
        amount=txn_data.amount,
        gateway_status=txn_data.gateway_status,
        bank_status=txn_data.bank_status,
        merchant_status=txn_data.merchant_status,
        final_status=final_st,
        failure_reason=fail_reason,
        recovery_status=recov_st,
        reconciliation_status=recon_st,
        created_at=datetime.utcnow()
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    return new_txn
