# TenantEase AI

TenantEase AI is a local proof of concept for intelligent rent collection, payment monitoring, simulated notifications, predictive late-payment risk, and owner-facing recommendations. It is designed for property owners and managers and uses synthetic data only. It does not represent confirmed Cynbit customer data or production capability.

## Features

- Monthly rent-obligation generation with tenant/month idempotency.
- Configurable due dates, documented grace period, and overdue detection.
- Pending payment recording followed by explicit verification and partial-payment reconciliation.
- Owner registration/login with Argon2 password hashing and owner-scoped property data.
- Event-driven scheduled notifications with simulated background delivery and duplicate prevention.
- Logistic Regression and Random Forest late-payment modeling.
- Tenant- and time-isolated evaluation.
- Risk thresholds, explanations, and deterministic recommendations.
- Six-section Streamlit SaaS dashboard with date simulation and an automatic notification worker.

## Architecture

`app.py` contains the Streamlit presentation, authentication flow, demo clock integration, and scheduler startup. `database/` contains SQLite/SQLAlchemy setup, models, migrations, and synthetic seeding. `src/data/` generates and validates data. `src/ml/` trains, evaluates, loads, and explains the model. `src/services/` contains authentication, tenant, rent, payment, notification, scheduler, financial, risk, and recommendation logic. `tests/` contains the automated suite.

## Technology stack

Python 3.11+, Streamlit, SQLite, SQLAlchemy, Pandas, NumPy, scikit-learn 1.7.2, Plotly, Joblib, Argon2-cffi, and Pytest.

## Dataset and model results

The reproducible dataset contains 5,600 synthetic records, 200 tenants, and 28 cycles per tenant. It has zero missing values and zero duplicate tenant-cycle records. Features are constructed from prior history at a seven-day pre-due-date information boundary.

The selected Random Forest was evaluated on a tenant- and time-isolated holdout:

| Metric | Result |
|---|---:|
| Accuracy | 0.7083 |
| Precision | 0.6016 |
| Recall | 0.7789 |
| F1 | 0.6789 |
| ROC-AUC | 0.7787 |
| PR-AUC | 0.6747 |
| Brier score | 0.2044 |

These are synthetic-data results and do not guarantee production performance.

## Database design

The SQLite database contains seven tables: `owners`, `properties`, `tenants`, `rent_records`, `payments`, `notification_logs`, and `prediction_logs`. Properties belong to owners; tenants belong to properties; rent records belong to tenants; payments belong to rent records; notifications belong to tenants/rent records; and predictions belong to tenants/rent records. Foreign keys and unique constraints enforce owner/property relationships, one rent obligation per tenant/month, unique transaction references, and idempotent notification types. Backend service queries scope operational data to the authenticated owner.

Owners register with a unique email and a password hashed by Argon2. Plaintext passwords are never stored. The current session stores the authenticated owner identity and protected pages require that identity before querying owner data. This is a local proof of concept, not a claim of production-grade identity infrastructure.

## Rent collection workflow

The default due day is the first. Unpaid rent is `PENDING` from the due date through the third grace day and becomes `OVERDUE` on the fifth. The assessment reminder convention maps December 1 to November 26 using the configured five-calendar-day subtraction. A recorded payment remains pending until verification. Financial totals sum only verified transactions: zero received is pending/overdue by date, a verified amount below rent is `PARTIALLY_PAID`, an exact amount is `PAID`, and an excess is retained as an overpayment flag. Outstanding balance is rent less verified receipts, and dashboard/analytics collection rate is verified collected amount divided by expected rent.

## Event-driven notifications

Notifications are created automatically from rent and payment events; owners do not need to click a notification simulator. Verifying a payment creates a scheduled `PARTIAL_PAYMENT_ALERT` or `FULL_PAYMENT_CONFIRMATION`. Partial messages include the rent amount, verified amount received, outstanding balance, and due date. Additional verified payments update a pending partial alert. When rent becomes fully paid, pending partial and overdue alerts are cancelled and a full-payment confirmation is scheduled.

The background worker creates `ADVANCE_REMINDER` events five calendar days before due date and `OVERDUE_ALERT` events for unpaid or partially paid obligations after the grace period. Payment-related notifications target 09:00 on the rent obligation's due date; if that time has already passed under the active application clock, they become immediately eligible. Payment-related notifications are scheduled for 09:00 on the rent obligation's due date; if that time has already passed under the active application clock, they become immediately eligible. Delivery is simulated locally through the lifecycle `SCHEDULED -> PROCESSING -> SENT_SIMULATED`; failures become `FAILED` and can be returned to `SCHEDULED` for retry. `sent_at` is populated only after processing reaches the scheduled time. Event creation and processing are owner-scoped, and `event_key` plus atomic status claims prevent duplicate events and deliveries.

The `ApplicationClock` uses the real local application clock for normal operation. In demo mode, the selected simulated date drives status evaluation, event scheduling, and delivery processing. If a notification’s planned time has already passed under the active clock, it is scheduled for immediate processing. Historical payment timestamps are never rewritten. The default timezone is `Asia/Kolkata`, and the worker polls every 15 seconds. APScheduler is used when importable; otherwise the standard-library background-worker fallback is used.

## Windows PowerShell setup

From the project directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`.env.example` documents an optional local database URL override. Copy it to `.env` only when needed; do not put passwords, API keys, or real tenant data in environment files.

If PowerShell blocks activation for the current process, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Generate data, train, and initialize the database

```powershell
python -m src.data.generate_dataset
python -m src.ml.train
python -c "from database.db import init_db; init_db(); from database.seed import seed_demo; seed_demo()"
```

The generated model is `models/rent_risk_model.pkl`; evaluation output is `reports/evaluation_results.json`. Small datasets used by tests do not overwrite the canonical 5,600-row artifacts.

## Start the application

```powershell
python -m streamlit run app.py --server.port 8505
```

Open `http://localhost:8505`.

## Test the project

```powershell
python -m compileall -q app.py config database src tests scripts reports/generate_pdfs.py
python -m pytest -v
```

The verified suite contains 46 passing tests. The suite covers authentication, owner isolation, CRUD, dataset validation, date boundaries, rent generation, verified and partial payments, financial aggregation, grace-period/overdue behavior, event-driven notification scheduling, real-versus-simulated clocks, December 19 overdue delivery, delivery claims, retries, cancellation, notification idempotency, saved-model prediction, risk thresholds, and recommendations.

## Separate demonstration database

The repeatable demo seed creates a separate local SQLite file and a synthetic owner account:

```powershell
python scripts/seed_demo_database.py
$env:TENANTEASE_DATABASE_URL = "sqlite:///demo/tenantease_demo.db"
python -m streamlit run app.py --server.port 8505
```

Local synthetic demo login (not a production credential):

- Email: `demo.owner@example.test`
- Password: `DemoOwner123!`

## Demonstration workflow

1. Start the app and use the sidebar **Initialize demo data** control.
2. Choose a simulated date and click **Generate selected month rent**.
3. Record a payment in **Rent & Payments**, then verify the partial payment.
4. Open Notification Center and confirm a scheduled `PARTIAL_PAYMENT_ALERT` was created automatically.
5. Verify an additional payment and confirm the pending message and outstanding amount update.
6. Complete the rent payment and confirm pending partial/overdue alerts are cancelled and a `FULL_PAYMENT_CONFIRMATION` is created.
7. Generate another unpaid obligation and advance the simulated date beyond its due date and grace period, such as December 19 for December 1 rent.
8. Confirm the `OVERDUE_ALERT` is automatically created and delivered under the simulated clock.
9. Use the Notification Center filters to inspect event creation, scheduled delivery, actual delivery, and status.
10. The AI Risk page scores only actual tenants with at least two verified payment cycles; otherwise it displays an insufficient-history message.

The demo clock affects status evaluation, notification scheduling, and simulated delivery processing. It does not modify historical payment timestamps.

## Repository hygiene

The local SQLite file (`*.db`), virtual environment, Python caches, test cache, logs, `.env` files, Streamlit secrets, and generated Joblib model files are ignored by Git. `.env.example` contains no secrets. Synthetic CSV data and reports remain available as project artifacts. No real tenant personal information is included; demo credentials are synthetic and local-only.

## Limitations and future work

This is a proof of concept. The model is synthetic-data trained and not production-calibrated. Notifications are simulated, payment-provider reconciliation is absent, and the local authentication/authorization implementation needs production hardening, secure secret/session management, audit controls, fairness review, drift monitoring, and deployment infrastructure. Payment gateway, real SMS/WhatsApp/email delivery, and production identity integrations are future work. Any production rollout should use representative consented data and human approval for tenant communications.
