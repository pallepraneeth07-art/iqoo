import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import engine, Base, SessionLocal
from .seed import seed_initial_data
from .routers import (
    transactions,
    simulator,
    recovery,
    reconciliation,
    analytics,
    alerts,
    anomalies
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables & seed initial data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="UPI Transaction Control Center API",
    description="Simulated intelligent UPI transaction control system, anomaly detection, smart recovery & reconciliation engine.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(transactions.router)
app.include_router(simulator.router)
app.include_router(recovery.router)
app.include_router(reconciliation.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(anomalies.router)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "system": "UPI Transaction Control Center API",
        "environment": "SIMULATION_PROTOTYPE_DEMO"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
