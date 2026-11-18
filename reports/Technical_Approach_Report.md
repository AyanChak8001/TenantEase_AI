# TenantEase AI
## Technical Approach Report

**Cynbit AI/ML Engineer Intern Assessment**  
**Status:** Verified proof of concept  
**Runtime:** Python 3.11.9 in the project virtual environment  
**Prepared:** November 2026

---

## Contents

1. System architecture  
2. Technology stack  
3. Application architecture  
4. Database schema and relationships  
5. Synthetic dataset generation  
6. Feature engineering and target definition  
7. Leakage prevention  
8. Training and evaluation methodology  
9. Logistic Regression baseline  
10. Random Forest model  
11. Model comparison  
12. Risk thresholds  
13. Model explainability  
14. Rent lifecycle  
15. Notification simulation  
16. Payment verification  
17. Recommendation engine  
18. Streamlit dashboard  
19. Testing strategy  
20. Limitations and future improvements

## 1. System architecture

TenantEase AI is a single-process local application with boundaries between presentation, persistence, data science, and business services.

```text
Streamlit UI (app.py)
        |
        +--> Collection services --> SQLAlchemy --> SQLite
        |       |                     tenants, rent, payments,
        |       |                     notifications, predictions
        |
        +--> ML services --> Joblib pipeline --> risk + explanation
        |
        +--> Plotly analytics and owner recommendations
```

The UI calls services rather than embedding collection rules in page rendering. The database is local and persistent. The ML pipeline is trained offline and loaded for inference.

## 2. Technology stack

| Area | Technology | Implementation use |
|---|---|---|
| Language | Python 3.11+ | Application and ML code |
| UI | Streamlit | Six-section dashboard and demo clock |
| Persistence | SQLite + SQLAlchemy 2.1.9 | Local relational state |
| Data | Pandas, NumPy | Generation, validation, analytics |
| ML | scikit-learn 1.7.2 | Logistic Regression and Random Forest |
| Serialization | Joblib | Persisted preprocessing/model pipeline |
| Charts | Plotly | Dashboard and analytics visualizations |
| Testing | Pytest | 12 automated tests |

The active scikit-learn version is pinned exactly in `requirements.txt` to keep training and inference compatible.

## 3. Application architecture

- `app.py`: Streamlit layout, navigation, forms, charts, empty states, and service calls.
- `config/settings.py`: project paths, database URL, business configuration, and model version.
- `database/db.py`: SQLAlchemy engine, session factory, initialization, and isolated test sessions.
- `database/models.py`: relational schema and constraints.
- `database/seed.py`: clearly synthetic demo property and tenants.
- `src/data/`: synthetic generation and dataset validation.
- `src/ml/`: training, evaluation, prediction, and explanation.
- `src/services/`: tenant, rent, payment, notification, risk, and recommendation workflows.
- `tests/`: dataset, date, CRUD, payment, notification, risk, and recommendation tests.

## 4. Database schema and relationships

The schema contains six principal tables:

| Table | Purpose |
|---|---|
| `properties` | Property metadata and unit count |
| `tenants` | Synthetic tenant profile, rent, unit, and due day |
| `rent_records` | One monthly rent obligation per tenant |
| `payments` | Recorded payment and verification state |
| `notification_logs` | Simulated reminder and overdue delivery history |
| `prediction_logs` | Optional persisted risk predictions |

Relationships are enforced with foreign keys. `rent_records` has a unique `(tenant_id, rent_month)` constraint. Payment transaction references are unique. Notification logs have a unique `(tenant_id, rent_record_id, notification_type)` constraint, which supports idempotency.

## 5. Synthetic dataset generation

`src/data/generate_dataset.py` uses random seed 42 and generates 200 synthetic tenants with 28 cycles each, producing 5,600 rows. Tenant behavior profiles represent generally on-time, occasional-late, and frequently-late patterns with variation in rent, method, and delay.

All names, contacts, identifiers, and outcomes are synthetic. The records are not Cynbit customer data. A regression fix ensures small datasets generated inside tests do not overwrite the canonical 5,600-row CSV artifacts.

| Validation check | Result |
|---|---:|
| Rows | 5,600 |
| Tenants | 200 |
| Cycles per tenant | 28 |
| Missing values | 0 |
| Duplicate tenant-cycle records | 0 |
| Target classes | Both present |

## 6. Feature engineering and target definition

Features include `monthly_rent`, `tenancy_months`, `payment_method`, `previous_late_payments`, `average_delay_days`, `last_payment_delay`, `on_time_payment_rate`, `previous_payment_count`, and `days_until_due`.

The target `late_payment` is 1 when the eventual payment date is after the due date and 0 when it is on or before the due date. Historical features use prior cycles only. The current payment date and current delay are not features.

## 7. Leakage prevention

Every generated row declares `days_until_due=7`, representing the information boundary used for prediction. The training split is tenant- and time-isolated:

- Training: tenants 1–160, cycles 1–22, 3,520 rows.
- Test: tenants 161–200, cycles 23–28, 240 rows.

There is no tenant overlap, and the earliest test due date is later than the latest training due date. This is more conservative than randomly splitting repeated tenant histories. Measured performance is not a production guarantee.

## 8. Training and evaluation methodology

Numeric features use median imputation and standardization for Logistic Regression. Categorical payment method uses most-frequent imputation and one-hot encoding. Both estimators use reproducible random state 42 and class balancing.

Metrics include accuracy, precision, recall, F1, ROC-AUC, PR-AUC, Brier score, and confusion matrix. A majority-class baseline is included for context. Model selection prioritizes F1 and then PR-AUC rather than accuracy alone.

## 9. Logistic Regression baseline

| Metric | Result |
|---|---:|
| Accuracy | 0.6792 |
| Precision | 0.5692 |
| Recall | 0.7789 |
| F1 | 0.6578 |
| ROC-AUC | 0.7830 |
| PR-AUC | 0.6792 |
| Brier score | 0.2062 |

## 10. Random Forest model

The comparison model uses 180 estimators, maximum depth 8, minimum leaf size 3, class balancing, and random state 42.

| Metric | Result |
|---|---:|
| Accuracy | 0.7083 |
| Precision | 0.6016 |
| Recall | 0.7789 |
| F1 | 0.6789 |
| ROC-AUC | 0.7787 |
| PR-AUC | 0.6747 |
| Brier score | 0.2044 |

## 11. Model comparison

Random Forest was selected because it achieved the higher F1 score and slightly better Brier score. Logistic Regression had marginally higher ROC-AUC and PR-AUC. The majority baseline had accuracy 0.6042, F1 0.0000, ROC-AUC 0.5000, PR-AUC 0.3958, and Brier score 0.2399.

The differences are useful for this prototype, but neither model has been calibrated or validated on representative real-world data.

## 12. Risk thresholds

| Risk | Threshold |
|---|---:|
| Low | `< 0.30` |
| Medium | `0.30 to < 0.65` |
| High | `>= 0.65` |

These thresholds are configurable prototype decisions. They require calibration, policy review, and monitoring before operational use.

## 13. Model explainability

Prediction explanations reference historical late count, average delay, and on-time rate. The wording states that the indicators are associative and not causal. The dashboard presents explanations and recommendations alongside probability and actual rent status.

## 14. Rent lifecycle implementation

`generate_rent_records` creates one obligation per active tenant and month and is idempotent. `refresh_statuses` applies this state machine:

- Before due date: `UPCOMING`.
- Due date through the next three calendar days: `PENDING`.
- Starting on the fourth day after due date, which is the default fifth for a first-of-month due date: `OVERDUE`.
- Verified payment at any point: `PAID`.

The implementation handles month lengths through `safe_due_date`, including February and leap years. Demo-date changes only recalculate status; they do not rewrite payment timestamps.

## 15. Notification simulation

`run_notification_simulation` creates advance reminders and overdue alerts with a database uniqueness constraint and existence check. It stores messages and simulated delivery metadata but never sends external communications.

## 16. Payment verification

`record_payment` writes a pending payment. `verify_payment` changes the payment to `VERIFIED`, marks the associated rent record `PAID`, and preserves notification history. A notification alone never marks rent paid.

## 17. Recommendation engine

Recommendations are deterministic templates based on predicted category, historical late count, average delay, and current rent status. They are owner-facing decision support. The system does not send recommendations automatically to tenants.

## 18. Streamlit dashboard

The dashboard includes:

1. Dashboard overview with database-derived KPIs, collection trend, status distribution, recent payments, overdue queue, and high-risk summary.
2. Tenant management with search, add/edit forms, property/unit details, and rent history.
3. Rent & Payments with status tabs, generation, recording, and verification.
4. Notification Center with simulation, filters, messages, and delivery status.
5. AI Risk Intelligence with actual-history gating, probabilities, explanations, and recommendations.
6. Analytics with collection, payment delay, risk, and evaluation views.

All six pages executed with zero exceptions through Streamlit's testing API. A live server returned HTTP 200 during acceptance testing.

## 19. Testing strategy

The final suite contains 12 passing tests covering dataset reproducibility and validation, canonical-artifact preservation, date boundaries, tenant/property CRUD, rent generation, payment verification, grace-period and overdue detection, reminder scheduling and duplicate prevention, risk thresholds, saved-model prediction, and recommendation generation.

An isolated SQLite session is used for database tests. A separate controlled workflow verified five-tenant generation, reminders, pending/grace/overdue transitions, payment verification, notification preservation, and duplicate prevention.

## 20. Limitations and future improvements

The model is trained on synthetic data, the current demo database has no verified payment history, notifications are simulated, and no production authentication, payment-provider integration, message delivery, calibration, fairness audit, drift monitoring, or deployment infrastructure is included.

Recommended next steps are representative data collection with consent, temporal backtesting, probability calibration, threshold governance, fairness analysis, model monitoring, provider reconciliation, role-based access, audit export, and human approval workflows for communications.
