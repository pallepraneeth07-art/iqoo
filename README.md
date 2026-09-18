# 🛡️ UPI Transaction Control Center

An intelligent, real-time UPI transaction monitoring, failure detection, AI anomaly analysis, smart recovery, multi-party reconciliation, and interactive simulation platform built for modern fintech operations.

> **Disclaimer**: This application is a **prototype/simulation** for demonstration purposes. It uses simulated banking switch APIs and synthetic transaction telemetry. No real financial transactions or bank accounts are touched.

---

## 🌟 Key Features

1. **Rule-Based Failure Detection Engine**:
   - Classifies multi-system telemetry (Gateway, Core Bank Switch, Merchant Ledger).
   - Detects critical failure patterns such as **Debited but Not Credited**, **Missing Merchant Records**, and **Duplicate Replays**.

2. **Smart Recovery Center**:
   - Evaluates recovery risk levels (High, Medium, Low).
   - Idempotent recovery action execution (`Verify Status`, `Mark Investigation`, `Credit Merchant`, `Refund Customer`, `Resolve Exception`).
   - Prevents duplicate retry executions when a customer's account has already been debited.

3. **Smart 3-Way Reconciliation Engine**:
   - Automated matching across Gateway settlement logs, Bank Switch ledgers, and Merchant credit records.
   - Categorizes records into: `MATCHED`, `AMOUNT_MISMATCH`, `STATUS_MISMATCH`, `MISSING_FROM_BANK`, `MISSING_FROM_MERCHANT`, `DUPLICATE`, `TIMESTAMP_MISMATCH`, `UNRESOLVED`.

4. **AI Anomaly & Pattern Intelligence**:
   - Powered by **Scikit-Learn IsolationForest** anomaly detection models & Pandas pattern engines.
   - Identifies merchant failure rate spikes, velocity anomalies, and unusual transaction amounts.

5. **Interactive Demo Simulator**:
   - One-click scenario generators for live hackathon presentations:
     - `Generate Successful Payment`
     - `Generate Failed Payment`
     - `Generate Pending Payment`
     - `Generate Debited but Not Credited`
     - `Generate Duplicate`
     - `Generate Reconciliation Mismatch`

6. **Pre-Populated Initial Seed Data**:
   - Ships with **30+ pre-seeded transaction records** across all edge cases for instant visual analytics on startup.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS, Recharts, Lucide Icons, Vite
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic v2, Uvicorn
- **AI & Analytics**: Pandas, Scikit-Learn (`IsolationForest`), NumPy
- **Database**: SQLite (default zero-config out-of-the-box) with full PostgreSQL compatibility via `DATABASE_URL`

---

## 📂 Project Architecture

```
IQOO HACKTHON/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app entry point & CORS configuration
│   │   ├── database.py            # SQLAlchemy engine setup
│   │   ├── models.py              # ORM models (Transaction, RecRecord, RecoveryAction, Alert, Anomaly)
│   │   ├── schemas.py             # Pydantic request & response schemas
│   │   ├── seed.py                # Initial 30+ transactions seeding script
│   │   ├── engines/
│   │   │   ├── failure_engine.py  # Status evaluation & rule classifier
│   │   │   ├── recovery_engine.py # Idempotent recovery workflow execution
│   │   │   ├── recon_engine.py    # Gateway/Bank/Merchant 3-way reconciliation
│   │   │   └── ai_engine.py       # Scikit-learn ML anomaly detection & failure prediction
│   │   └── routers/
│   │       ├── transactions.py    # Transaction table, detail, & CSV export APIs
│   │       ├── simulator.py       # Live transaction simulator endpoint
│   │       ├── recovery.py        # Smart Recovery Center endpoints
│   │       ├── reconciliation.py  # 3-Way Reconciliation runner endpoints
│   │       ├── analytics.py       # KPI summaries & chart datasets
│   │       ├── alerts.py          # Alerts center management
│   │       └── anomalies.py       # AI anomaly feed endpoint
│   ├── requirements.txt
│   └── start_backend.py
├── frontend/
│   ├── src/
│   │   ├── components/            # KPICards, DashboardCharts, TransactionTable, Drawer, Recovery, Recon, Anomalies, Alerts, Simulator
│   │   ├── services/api.ts        # REST API client
│   │   ├── types/index.ts         # TypeScript definitions
│   │   ├── App.tsx                # Main view router & tab manager
│   │   ├── main.tsx
│   │   └── index.css              # Custom Tailwind fintech styling
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── run_app.bat                    # One-command Windows launcher
└── README.md
```

---

## 🚀 Quick Start & Installation

### Option 1: One-Command Launcher (Windows)
Double-click `run_app.bat` or execute in terminal:
```cmd
run_app.bat
```

### Option 2: Manual Terminal Startup

#### 1. Start Backend:
```bash
cd backend
pip install -r requirements.txt
python start_backend.py
```
*Backend API runs at*: `http://localhost:8000`  
*Interactive Swagger Documentation*: `http://localhost:8000/docs`

#### 2. Start Frontend:
```bash
cd frontend
npm install
npm run dev
```
*Control Center UI runs at*: `http://localhost:3000`

---

## 📡 REST API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/transactions` | Fetch filterable transaction list (search, status, merchant, amount) |
| `GET` | `/api/transactions/{id}` | Fetch detailed transaction record & system statuses |
| `GET` | `/api/transactions/export/csv` | Download transaction telemetry report in CSV format |
| `POST` | `/api/transactions/simulate` | Execute live scenario generator (`SUCCESS`, `FAILED`, `DEBITED_NOT_CREDITED`, etc.) |
| `POST` | `/api/recovery/analyze/{id}` | Execute Scikit-learn failure probability & AI advice analysis |
| `POST` | `/api/recovery/verify/{id}` | Verify core bank switch debit status |
| `POST` | `/api/recovery/execute/{id}` | Execute idempotent recovery action (`CREDIT_MERCHANT`, `REFUND`, `RESOLVE`) |
| `POST` | `/api/reconciliation/run` | Execute 3-way reconciliation runner across all records |
| `GET` | `/api/reconciliation/exceptions` | Fetch reconciliation mismatch & missing log exceptions |
| `GET` | `/api/analytics` | Fetch summary KPI metrics & Recharts dataset |
| `GET` | `/api/alerts` | Fetch active or resolved system alerts |
| `POST` | `/api/alerts/{id}/resolve` | Mark alert resolved |
| `GET` | `/api/anomalies` | Fetch IsolationForest AI anomaly detection feed |

---

## 🎬 14-Step Hackathon Demo Flow

1. **Open Application**: Navigate to `http://localhost:3000`.
2. **Inspect Dashboard**: Review the 8 KPI cards (*Total Txns, Success/Failure counts, Recovery Required, Reconciliation Exceptions, ₹ Total Value*).
3. **Explore Charts**: View real-time volume timelines, donut status distribution, failure cause breakdown, and merchant health matrices.
4. **Open Demo Simulator**: Click **[Run Demo Simulator]** in the top navigation bar.
5. **Generate Critical Failure**: Click **[Generate Debited but Not Credited]**.
6. **Watch Real-Time Execution Logs**: Observe the 6-step automated pipeline log creating the record, running failure rules, and pushing an alert.
7. **Notice Critical Alert Banner**: See the red critical alert banner appear instantly on top of the dashboard.
8. **Inspect Transaction Timeline**: Click the newly created transaction in the table to open the slide-over drawer.
9. **Review 3 System Statuses**: Observe `Gateway: TIMEOUT`, `Bank: DEBITED`, `Merchant: NOT_CREDITED` -> Final State: `DEBITED_NOT_CREDITED`.
10. **Run AI ML Analysis**: Click **[Run ML Analysis]** inside the drawer to view failure probability (94%) and AI advice.
11. **Open Recovery Center**: Click **Recovery Center** in the sidebar. Locate the transaction under High Risk.
12. **Execute Recovery**: Click **[Verify Status]** followed by **[Credit Merchant]** to resolve the debit discrepancy safely.
13. **Run 3-Way Reconciliation**: Navigate to **Reconciliation** tab and click **[Run Reconciliation]** to observe side-by-side Gateway vs Bank vs Merchant ledger parity.
14. **Check Dashboard Update**: Return to the Dashboard and verify that recovery success rate and total value reflect the resolved state.
