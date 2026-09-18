from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    role = Column(String(50), default="Admin")  # Admin or Merchant
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False) # e.g. TXN10001
    upi_reference = Column(String(50), index=True, nullable=False)               # e.g. UPI883492834
    customer_id = Column(String(50), index=True, nullable=False)                 # e.g. CUST_9041
    merchant_id = Column(String(50), index=True, nullable=False)                 # e.g. M102
    merchant_name = Column(String(100), nullable=True, default="Flipkart India")
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # 3-system statuses
    gateway_status = Column(String(20), nullable=False)  # SUCCESS, FAILED, PENDING, TIMEOUT
    bank_status = Column(String(20), nullable=False)     # SUCCESS, FAILED, PENDING, DEBITED, NOT_DEBITED
    merchant_status = Column(String(20), nullable=False) # SUCCESS, FAILED, PENDING, MISSING, CREDITED, NOT_CREDITED

    # Computed fields
    final_status = Column(String(30), nullable=False)    # SUCCESS, FAILED, PENDING, DEBITED_NOT_CREDITED, DUPLICATE, MISMATCH, REFUND_PENDING, RESOLVED
    failure_reason = Column(Text, nullable=True)
    recovery_status = Column(String(30), default="NOT_REQUIRED") # NOT_REQUIRED, RECOVERY_REQUIRED, VERIFICATION_PENDING, IN_PROGRESS, RESOLVED, REFUNDED
    reconciliation_status = Column(String(30), default="MATCHED") # MATCHED, UNMATCHED, EXCEPTION, RESOLVED

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reconciliation = relationship("ReconciliationRecord", back_populates="transaction", uselist=False)
    recovery_actions = relationship("RecoveryAction", back_populates="transaction")
    alerts = relationship("Alert", back_populates="transaction")
    anomalies = relationship("AnomalyEvent", back_populates="transaction")

class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    
    gateway_amount = Column(Float, nullable=True)
    bank_amount = Column(Float, nullable=True)
    merchant_amount = Column(Float, nullable=True)

    gateway_status = Column(String(20), nullable=True)
    bank_status = Column(String(20), nullable=True)
    merchant_status = Column(String(20), nullable=True)

    reconciliation_result = Column(String(30), nullable=False) # MATCHED, AMOUNT_MISMATCH, STATUS_MISMATCH, MISSING_FROM_BANK, MISSING_FROM_MERCHANT, DUPLICATE, TIMESTAMP_MISMATCH, UNRESOLVED
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="reconciliation")

class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False) # VERIFY_STATUS, MARK_INVESTIGATION, RETRY_TRANSACTION, REFUND_CUSTOMER, CREDIT_MERCHANT, RESOLVE
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="PENDING")   # PENDING, IN_PROGRESS, COMPLETED, FAILED
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="recovery_actions")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), ForeignKey("transactions.transaction_id"), nullable=True, index=True)
    severity = Column(String(20), nullable=False) # CRITICAL (🔴), WARNING (🟠), PENDING (🟡), INFO (🔵)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    status = Column(String(20), default="ACTIVE") # ACTIVE, RESOLVED, DISMISSED
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="alerts")

class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), ForeignKey("transactions.transaction_id"), nullable=True, index=True)
    anomaly_type = Column(String(50), nullable=False) # HIGH_FAILURE_RATE, VELOCITY_SPIKE, UNUSUAL_AMOUNT, REPEATED_TXN, PENDING_ACCUMULATION
    confidence = Column(Float, nullable=False)         # e.g., 0.87 -> 87%
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="anomalies")
