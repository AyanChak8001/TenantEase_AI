# TenantEase AI

TenantEase AI is a local proof of concept for intelligent rent collection, payment monitoring, simulated notifications, predictive late-payment risk, and owner-facing recommendations. It is designed for property owners and managers and uses synthetic data only. It does not represent confirmed Cynbit customer data or production capability.

## Features

- Monthly rent-obligation generation with tenant/month idempotency.
- Configurable due dates, documented grace period, and overdue detection.
- Pending payment recording followed by explicit verification.
- Simulated advance and overdue notifications with duplicate prevention.
- Logistic Regression and Random Forest late-payment modeling.
- Tenant- and time-isolated evaluation.
- Risk thresholds, explanations, and deterministic recommendations.
- Six-section Streamlit SaaS dashboard with date simulation.

## Architecture

`app.py` contains the Streamlit presentation layer. `database/` contains SQLite/SQLAlchemy setup, models, and synthetic seeding. `src/data/` generates and validates data. `src/ml/` trains, evaluates, loads, and explains the model. `src/services/` contains tenant, rent, payment, notification, risk, and recommendation logic. `tests/` contains the automated suite.

## Technology stack

Python 3.11+, Streamlit, SQLite, SQLAlchemy, Pandas, NumPy, scikit-learn 1.7.2, Plotly, Joblib, and Pytest.

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

The SQLite database contains `properties`, `tenants`, `rent_records`, `payments`, `notification_logs`, and `prediction_logs`. Foreign keys and unique constraints enforce tenant/property relationships, one rent obligation per tenant/month, unique transaction references, and idempotent notification types.

## Rent collection workflow

The default due day is the first. Unpaid rent is `PENDING` from the due date through the third grace day and becomes `OVERDUE` on the fifth. The assessment reminder convention maps December 1 to November 26 using the configured five-calendar-day subtraction. Verified payments transition rent to `PAID`; recording or notifying alone does not.

## Windows PowerShell setup

From the project directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

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
python -m compileall -q app.py config database src tests
python -m pytest -v
```

The verified suite contains 12 passing tests. Streamlit page execution was also verified programmatically for all six sections with zero exceptions.

## Demonstration workflow

1. Start the app and use the sidebar **Initialize demo data** control.
2. Choose a simulated date and click **Generate selected month rent**.
3. Use November 25 to show an upcoming obligation.
4. Use November 26 and run notification simulation to create advance reminders.
5. Use December 1 to show unpaid rent as pending.
6. Use December 3 to show the grace period still active.
7. Use December 5 to show overdue rent and the overdue alert.
8. Record a payment in **Rent & Payments**; it remains pending verification.
9. Verify it and confirm the rent status becomes `PAID` while notification history remains.
10. The AI Risk page scores only actual tenants with at least two verified payment cycles; otherwise it displays an insufficient-history message.

The date simulator changes status evaluation only. It does not modify historical payment timestamps.

## Repository hygiene

The local SQLite file (`*.db`), virtual environment, Python caches, test cache, logs, Streamlit secrets, and generated Joblib model files are ignored by Git. Synthetic CSV data and reports remain available as project artifacts. No credentials or real tenant personal information are included.

## Limitations and future work

This is a proof of concept. The model is synthetic-data trained and not production-calibrated. Notifications are simulated, payment-provider reconciliation is absent, and authentication, authorization, audit controls, fairness review, drift monitoring, and deployment infrastructure are future work. Any production rollout should use representative consented data and human approval for tenant communications.
