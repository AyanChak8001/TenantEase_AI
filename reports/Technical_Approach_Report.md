# TenantEase AI
## Technical Approach Report

**Cynbit AI/ML Engineer Intern Assessment**
**Status:** Verified local proof of concept
**Runtime:** Python 3.11.9 in the project virtual environment
**Prepared:** November 2026

---

## Contents

1. System architecture  2. Technology stack  3. Application architecture  4. Database schema and relationships  5. Owner authentication and isolation  6. Synthetic dataset generation  7. Feature engineering and target definition  8. Leakage prevention  9. Training and evaluation methodology  10. Model comparison  11. Risk thresholds and explainability  12. Rent lifecycle and financial accounting  13. Notification simulation  14. Payment verification  15. Recommendation engine  16. Streamlit dashboard  17. Testing strategy  18. Limitations and future improvements

## 1. System architecture

TenantEase AI is a single-process local application with boundaries between presentation, authentication, persistence, data science, and business services.

```text
Streamlit UI (app.py)
        |
        +--> Auth + collection services --> SQLAlchemy --> SQLite
        |       |                          owners, properties, tenants,
        |       |                          rent, payments, notifications,
        |       |                          predictions
        |
        +--> ML services --> Joblib pipeline --> risk + explanation
        +--> Plotly analytics and owner recommendations
```

## 2. Technology stack

| Area | Technology | Implementation use |
|---|---|---|
| Language | Python 3.11+ | Application and ML code |
| UI | Streamlit | Six-section dashboard and demo clock |
| Persistence | SQLite + SQLAlchemy 2.1.9 | Local relational state |
| Data | Pandas, NumPy | Generation, validation, analytics |
| ML | scikit-learn 1.7.2 | Logistic Regression and Random Forest |
| Serialization | Joblib | Persisted preprocessing/model pipeline |
| Password hashing | Argon2-cffi | Owner password hashes |
| Charts | Plotly | Dashboard and analytics visualizations |
| Testing | Pytest | 23 automated tests |

The active scikit-learn version is pinned exactly in `requirements.txt` to keep training and inference compatible.

## 3. Application architecture

`app.py` handles Streamlit layout, authentication, navigation, forms, charts, and service calls. `config/` holds paths and business settings. `database/` holds SQLAlchemy setup, models, migration compatibility, and synthetic seeding. `src/data/` generates/validates data, `src/ml/` trains/evaluates/loads/explains the model, and `src/services/` contains authentication, tenant, rent, payment, financial, notification, risk, and recommendation workflows.

## 4. Database schema and relationships

The schema contains seven principal tables:

| Table | Purpose |
|---|---|
| `owners` | Owner identity, unique email, Argon2 password hash, active state |
| `properties` | Property metadata, unit count, and owner foreign key |
| `tenants` | Synthetic tenant profile, rent, unit, and due day |
| `rent_records` | One monthly rent obligation per tenant |
| `payments` | Recorded payment amount and verification state |
| `notification_logs` | Simulated reminder and overdue delivery history |
| `prediction_logs` | Optional persisted risk prediction records |

Properties belong to owners; tenants belong to properties; rent records belong to tenants; payments belong to rent records; notifications reference tenants/rent records; predictions reference tenants/rent records. `rent_records` has a unique `(tenant_id, rent_month)` constraint. Payment transaction references are unique. Notification logs have a unique `(tenant_id, rent_record_id, notification_type)` constraint.

## 5. Owner authentication and isolation

Registration validates a unique email and stores only an Argon2 password hash. Login verifies the supplied password with `argon2.PasswordHasher`; logout clears the authenticated owner session. Protected dashboard sections require an authenticated owner.

Properties carry `owner_id`. Tenant, rent, payment, notification, financial, and risk queries derive ownership through the property relationship rather than trusting an owner ID supplied by a form. This prevents normal service paths from reading or mutating another ownerâ€™s records. Production deployment would still require hardened session, secret, transport, audit, recovery, and role-management controls.

## 6. Synthetic dataset generation

`src/data/generate_dataset.py` uses random seed 42 and generates 200 synthetic tenants with 28 cycles each, producing 5,600 rows. Profiles represent generally on-time, occasional-late, and frequently-late behavior with rent, method, and delay variation. All names, contacts, identifiers, and outcomes are synthetic and not Cynbit customer data.

| Validation check | Result |
|---|---:|
| Rows | 5,600 |
| Tenants | 200 |
| Cycles per tenant | 28 |
| Missing values | 0 |
| Duplicate tenant-cycle records | 0 |
| Target classes | Both present |

## 7. Feature engineering and target definition

Features include `monthly_rent`, `tenancy_months`, `payment_method`, `previous_late_payments`, `average_delay_days`, `last_payment_delay`, `on_time_payment_rate`, `previous_payment_count`, and `days_until_due`. The target `late_payment` is 1 when eventual payment is after due date and 0 when on or before it. Current payment date, delay, and outcome are excluded from features.

## 8. Leakage prevention

Rows use a seven-day pre-due information boundary. Training uses tenants 1-160 and cycles 1-22 (3,520 rows); testing uses tenants 161-200 and cycles 23-28 (240 rows). There is no tenant overlap, and test due dates are later than training due dates. This conservative synthetic evaluation is not a production guarantee.

## 9. Training and evaluation methodology

Numeric features use median imputation and standardization for Logistic Regression. Payment method uses most-frequent imputation and one-hot encoding. Both estimators use random state 42 and class balancing. Metrics include accuracy, precision, recall, F1, ROC-AUC, PR-AUC, Brier score, and confusion matrix. Selection prioritizes F1 and then PR-AUC rather than accuracy alone.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.6792 | 0.5692 | 0.7789 | 0.6578 | 0.7830 | 0.6792 | 0.2062 |
| Random Forest | 0.7083 | 0.6016 | 0.7789 | 0.6789 | 0.7787 | 0.6747 | 0.2044 |

Random Forest was selected because it achieved the higher F1 and slightly better Brier score. Logistic Regression had marginally higher ROC-AUC and PR-AUC. The majority baseline had accuracy 0.6042, F1 0.0000, ROC-AUC 0.5000, PR-AUC 0.3958, and Brier score 0.2399.

## 10. Model comparison

The selected Random Forest uses 180 estimators, maximum depth 8, minimum leaf size 3, class balancing, and random state 42. Both models use the same feature schema and preprocessing. The saved artifact is trained with the pinned scikit-learn version.

## 11. Risk thresholds and explainability

| Risk | Threshold |
|---|---:|
| Low | `< 0.30` |
| Medium | `0.30 to < 0.65` |
| High | `>= 0.65` |

Thresholds are configurable prototype decisions and require calibration, policy review, and monitoring. Explanations reference historical late count, average delay, and on-time rate. They state association, not causation; risk is distinct from actual overdue status.

## 12. Rent lifecycle and financial accounting

`generate_rent_records` creates one obligation per active tenant and month and is idempotent. `financial_service.py` is the shared calculation layer used by dashboard, analytics, rent views, and notification status checks.

For each obligation, `verified_total` sums only payments with `verification_status == VERIFIED`. Pending and rejected transactions are excluded. Outstanding balance is rent less verified receipts, floored at zero, with excess retained as an overpayment flag. Zero receipt is `PENDING` or `OVERDUE` by date; a positive receipt below rent is `PARTIALLY_PAID`; equal or greater verified total is `PAID`. Unpaid rent is pending through the three grace days and overdue from the fifth for the default first-of-month schedule.

The same service calculates expected rent, verified collected rent, pending balance, overdue balance, partial balance, total outstanding, and collection rate. Collection rate is verified collected amount divided by expected rent, never the full face value of obligations marked paid. Simulated dates do not rewrite historical timestamps.

## 13. Notification simulation

`run_notification_simulation` creates advance reminders and overdue alerts with a database uniqueness constraint and existence check. It never sends external communications. Alerts include outstanding overdue balances, including partially paid obligations, and are idempotent.

## 14. Payment verification

`record_payment` writes a pending transaction after owner-scope validation. `verify_payment` changes that transaction to `VERIFIED`, then recalculates the obligation from all verified transactions. A partial verified transaction therefore produces `PARTIALLY_PAID`; it does not mark the entire obligation `PAID`. Only a fully covered obligation becomes `PAID`. History and transaction references are preserved.

## 15. Recommendation engine

Recommendations are deterministic templates based on predicted category, historical late count, average delay, and current rent status. They are owner-facing decision support and are not sent automatically to tenants.

## 16. Streamlit dashboard

The six sections are Dashboard, Tenants, Rent & Payments, Notifications, AI Risk Intelligence, and Analytics. They provide owner-scoped KPIs, verified collection trends, status distributions, transaction activity, CRUD forms, payment verification, notification simulation, gated risk predictions, explanations, recommendations, and evaluation views. Financial figures use the centralized financial service, and predicted risk is shown separately from actual overdue status.

## 17. Testing strategy

The final suite contains 23 passing tests covering dataset reproducibility/validation, canonical-artifact preservation, date boundaries, tenant/property CRUD, owner registration/login/logout/isolation, rent generation, no/partial/full/over payments, pending/rejected exclusion, financial aggregation and duplicate-join prevention, grace-period and overdue behavior, reminder idempotency, risk thresholds, saved-model prediction, and recommendations.

The financial regression scenario with two INR 20,000 obligations and INR 15,000 verified receipts per obligation reconciles to expected INR 40,000, collected INR 30,000, outstanding INR 10,000, and 75% collection. Database tests use isolated SQLite sessions.

`prediction_logs` supports persisted prediction records, but the current dashboardâ€™s display-time risk scoring is not a complete audit log of every rendered prediction. This is a known limitation.

## 18. Limitations and future improvements

The model is synthetic-data trained and not production-calibrated. Notifications are simulated, payment-provider integration and real email/SMS/WhatsApp delivery are absent, and local authentication needs production hardening. Future work includes representative consented data, temporal backtesting, calibration, threshold governance, fairness analysis, monitoring, provider reconciliation, stronger role-based access, audit export, prediction-log policy, and human approval for communications.
