from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class TransactionBase(BaseModel):
    transaction_id: str
    upi_reference: str
    customer_id: str
    merchant_id: str
    merchant_name: Optional[str] = "Flipkart India"
    amount: float
    gateway_status: str
    bank_status: str
    merchant_status: str

class TransactionCreate(TransactionBase):
    pass

class TransactionSimulateRequest(BaseModel):
    scenario: str # SUCCESS, FAILED, PENDING, DEBITED_NOT_CREDITED, DUPLICATE, RECONCILIATION_MISMATCH
    custom_amount: Optional[float] = None
    custom_merchant: Optional[str] = None

class RecoveryActionRequest(BaseModel):
    action_type: str # VERIFY_STATUS, MARK_INVESTIGATION, RETRY_TRANSACTION, REFUND_CUSTOMER, CREDIT_MERCHANT, RESOLVE
    reason: Optional[str] = "Manual recovery initiated via Control Center"
    idempotency_key: Optional[str] = None

class RecoveryActionResponse(BaseModel):
    id: int
    transaction_id: str
    action_type: str
    reason: str
    status: str
    idempotency_key: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ReconciliationRecordSchema(BaseModel):
    id: int
    transaction_id: str
    gateway_amount: Optional[float]
    bank_amount: Optional[float]
    merchant_amount: Optional[float]
    gateway_status: Optional[str]
    bank_status: Optional[str]
    merchant_status: Optional[str]
    reconciliation_result: str
    details: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertSchema(BaseModel):
    id: int
    transaction_id: Optional[str]
    severity: str
    alert_type: str
    message: str
    recommended_action: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AnomalyEventSchema(BaseModel):
    id: int
    transaction_id: Optional[str]
    anomaly_type: str
    confidence: float
    explanation: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionSchema(TransactionBase):
    id: int
    timestamp: datetime
    final_status: str
    failure_reason: Optional[str]
    recovery_status: str
    reconciliation_status: str
    created_at: datetime
    updated_at: datetime

    alerts: List[AlertSchema] = []
    anomalies: List[AnomalyEventSchema] = []
    recovery_actions: List[RecoveryActionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class AnalyticsSummary(BaseModel):
    total_transactions: int
    successful_payments: int
    failed_payments: int
    pending_payments: int
    recovery_required: int
    reconciliation_exceptions: int
    recovery_success_rate: float
    total_transaction_value: float
    success_rate_percentage: float

class AIAnalysisResponse(BaseModel):
    transaction_id: str
    failure_probability: float
    likely_reason: str
    confidence: str
    recommended_action: str
    is_anomaly: bool
    anomaly_explanation: Optional[str] = None
