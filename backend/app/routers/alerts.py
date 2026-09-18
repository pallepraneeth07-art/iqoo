from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import Alert
from ..schemas import AlertSchema

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertSchema])
def get_alerts(
    db: Session = Depends(get_db),
    status: Optional[str] = "ACTIVE",
    severity: Optional[str] = None
):
    query = db.query(Alert)
    if status and status.upper() != "ALL":
        query = query.filter(Alert.status == status.upper())
    if severity:
        query = query.filter(Alert.severity == severity.upper())

    alerts = query.order_by(Alert.created_at.desc()).all()
    return alerts

@router.post("/{id}/resolve")
def resolve_alert(id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "RESOLVED"
    db.commit()
    db.refresh(alert)
    return {"message": "Alert resolved successfully", "alert_id": id}
