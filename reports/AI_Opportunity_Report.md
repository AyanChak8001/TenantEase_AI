# TenantEase AI
## AI Opportunity Report

**Cynbit AI/ML Engineer Intern Assessment**
**Status:** Proposed product opportunity and verified local proof of concept
**Data classification:** Fully synthetic demonstration data
**Prepared:** November 2026

---

## Executive summary

TenantEase AI is a proposed property-management product opportunity combining rent-collection workflow automation with predictive payment monitoring. It addresses a recurring operating pattern: property teams track monthly obligations, send reminders, reconcile payments, and decide which unpaid accounts need attention.

The local proof of concept generates 5,600 synthetic rent-cycle records for 200 synthetic tenants, stores operational state in SQLite, applies a configurable reminder and three-day grace-period workflow, simulates notifications, records verified and partial payments, and compares Logistic Regression with Random Forest for late-payment risk. Random Forest achieved 0.7083 accuracy, 0.6016 precision, 0.7789 recall, 0.6789 F1, 0.7787 ROC-AUC, 0.6747 PR-AUC, and 0.2044 Brier score on a tenant- and time-isolated synthetic holdout.

These results demonstrate prototype feasibility only. They are not evidence of production performance, customer outcomes, or confirmed Cynbit capabilities.

## Company and industry context

Property management is a recurring-operations domain. Each month creates predictable obligations, expected payments, exceptions, reminders, and reconciliations. A product that makes this sequence visible and consistent can help owners and managers spend less time on manual status checking and more time on exceptions and respectful tenant communication.

This report frames TenantEase AI as a proposed opportunity for a Cynbit assessment. It does not assert company revenue, customer volume, existing product capability, or market statistics that were not provided.

## The property-management business problem

The core problem is maintaining a reliable, owner-scoped and auditable view of every rent obligation, its verified receipts, outstanding balance, and appropriate next action. An owner needs to know which obligations are upcoming, pending, partially paid, overdue, or paid; which reminders have already been sent; whether a transaction is recorded but unverified; and which tenants have historical late-payment indicators.

## Existing manual rent-collection challenges

Manual processes can create avoidable risk:

1. Reminder dates may be calculated inconsistently.
2. Grace periods may be applied differently from one cycle to another.
3. Repeated manual runs can create duplicate notifications.
4. A notification or pending transaction can be confused with a verified payment.
5. A partial receipt can be incorrectly treated as full settlement.
6. Owners may prioritize the most visible account rather than the highest-value exception.

The opportunity is workflow reliability plus decision support, not automated collection decisions.

## Proposed TenantEase AI opportunity

TenantEase AI can provide a focused extension with owner registration/login using Argon2 password hashing, owner-specific property data access, a monthly rent ledger, configurable due dates, a three-day grace period, verified payment aggregation, partial-payment and outstanding-balance accounting, idempotent simulated notifications, late-payment risk scoring, explainable indicators, owner-approved recommendations, and portfolio dashboards.

The implementation is a local proof of concept. Its authentication and owner isolation demonstrate the intended boundary but are not a claim of production-ready security controls.

## Automated monthly rent collection workflow

The implemented workflow is:

1. Generate one rent obligation per active tenant and month.
2. Schedule the configured advance reminder. The assessment convention represents December 1 as a November 26 reminder using a configurable five-calendar-day subtraction.
3. Keep an unpaid obligation pending on the due date and through the three-day grace period.
4. Mark an obligation overdue starting on the fifth day for the default first-of-month schedule.
5. Create an overdue alert only once per tenant, rent record, and notification type.
6. Record transactions as pending verification.
7. Sum all verified transactions: below rent is `PARTIALLY_PAID`, exact coverage is `PAID`, and excess is flagged for review.

The date simulator changes status evaluation only; it does not change historical payment timestamps.

## AI-based late-payment prediction

The proof of concept trains a binary classifier for `late_payment`. Features are restricted to information available seven days before the due date and include rent amount, tenancy length, payment method, previous late count, average historical delay, last delay, on-time rate, previous payment count, and days until due.

The selected Random Forest is decision support. It does not confirm default, determine tenant eligibility, or replace owner review. Results are based on synthetic data and a tenant- and time-isolated holdout.

## Explainable risk classification

| Category | Probability |
|---|---:|
| Low | below 0.30 |
| Medium | 0.30 to below 0.65 |
| High | 0.65 or above |

Explanations summarize historical late count, average delay, and on-time rate. They describe association, not causation. The dashboard distinguishes predicted risk from actual overdue status and requires sufficient verified history before producing a tenant-level score.

## Automated notification simulation

The notification engine stores recipient, message, scheduled time, simulated send time, type, and delivery status in `notification_logs`. It does not send email, SMS, WhatsApp, or other external messages. This is safe, deterministic, and auditable while leaving an extension point for owner-approved integrations.

## Expected operational benefits

If validated with representative operational data, the opportunity could support more consistent reminder timing, fewer duplicates, correct separation of receipts and balances, faster identification of overdue obligations, focused owner follow-up, and clearer collection trends. These are expected workflow benefits, not measured production outcomes.

## Business feasibility

The proof of concept is feasible for local deployment using Python, Streamlit, SQLite, SQLAlchemy, Pandas, NumPy, scikit-learn, Plotly, Joblib, Argon2, and Pytest. It needs no paid API, payment gateway, external messaging provider, or real tenant information.

## Risks and limitations

- The dataset is synthetic and may not represent real payment behavior.
- Model probabilities and thresholds are not production-calibrated.
- The evaluation is not prospective validation.
- Historical patterns can encode unfair or incomplete signals.
- Local authentication and owner isolation need production hardening.
- Notifications are simulated rather than delivered.
- Payment-gateway reconciliation and real email/SMS/WhatsApp integrations are not implemented.
- Demo tenants may lack sufficient verified history for scoring.

## Future opportunities

Potential next steps include probability calibration, prospective monitoring, drift detection, fairness review, payment-provider reconciliation, real messaging integrations, owner approval workflows, consent-aware communications, stronger role-based access, audit exports, portfolio forecasting, and a governed LLM message-drafting extension. Any future AI layer should remain grounded in stored facts and require human approval for outbound communication.

## Conclusion

TenantEase AI demonstrates a coherent product opportunity: pair deterministic, owner-scoped rent-collection workflow with explainable, conservative payment-risk prioritization. The model is a decision-support component, not an automated default decision-maker. Validation with representative, consented operational data is necessary before claims about real-world impact.
