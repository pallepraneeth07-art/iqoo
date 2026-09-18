from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import AnomalyEvent
from ..schemas import AnomalyEventSchema
from ..engines.ai_engine import detect_system_anomalies

router = APIRouter(prefix="/api/anomalies", tags=["Anomalies"])

@router.get("", response_model=List[AnomalyEventSchema])
def get_anomaly_events(db: Session = Depends(get_db)):
    # Trigger scanner to pick up fresh outliers
    detect_system_anomalies(db)

    anomalies = db.query(AnomalyEvent).order_by(AnomalyEvent.created_at.desc()).all()
    return anomalies
