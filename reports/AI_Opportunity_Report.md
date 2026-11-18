# TenantEase AI
## AI Opportunity Report

**Cynbit AI/ML Engineer Intern Assessment**  
**Status:** Proof of concept  
**Data classification:** Fully synthetic demonstration data  
**Prepared:** November 2026

---

## Executive summary

TenantEase AI is a proposed property-management product opportunity that combines dependable rent-collection workflow automation with predictive payment monitoring. It addresses a recurring operational pattern: property teams track monthly obligations, send reminders, reconcile payments, and decide which unpaid accounts need attention.

The proof of concept demonstrates an offline, local implementation. It generates 5,600 synthetic rent-cycle records for 200 synthetic tenants, stores operational state in SQLite, applies a configurable reminder and grace-period workflow, simulates notifications, and compares Logistic Regression with Random Forest for late-payment risk. The selected Random Forest achieved 0.7083 accuracy, 0.6016 precision, 0.7789 recall, 0.6789 F1, 0.7787 ROC-AUC, 0.6747 PR-AUC, and 0.2044 Brier score on a tenant- and time-isolated synthetic holdout.

These results demonstrate technical feasibility of the prototype only. They are not evidence of production performance, customer outcomes, or confirmed Cynbit capabilities.

## Company and industry context

Property management is a recurring-operations domain. Each month creates a predictable sequence of obligations, expected payments, exceptions, reminders, and reconciliations. A product that makes this sequence visible and consistent can help owners and managers spend less time on manual status checking and more time on exceptions and respectful tenant communication.

This report frames TenantEase AI as a proposed opportunity for a Cynbit assessment. It does not assert company revenue, customer volume, existing product capability, or market statistics that were not provided.

## The property-management business problem

The core problem is not simply sending a reminder. It is maintaining a reliable, auditable view of every rent obligation and deciding what action is appropriate as the due date approaches.

For an owner or manager, the desired operating view includes:

- Which rent obligations are upcoming, pending, overdue, or paid.
- Which reminders have already been sent.
- Whether a payment is recorded but still unverified.
- Which tenants have historical indicators associated with late payment.
- Which follow-up is appropriate without unsupported assumptions about a tenant.

## Existing manual rent-collection challenges

Manual processes can create avoidable operational risk:

1. Reminder dates may be calculated inconsistently.
2. Grace periods may be applied differently from one cycle to another.
3. Repeated manual runs can create duplicate notifications.
4. A notification can be confused with a verified payment.
5. Owners may prioritize the most visible account rather than the highest-value exception.
6. Historical payment behavior may not be summarized before follow-up.

The opportunity is therefore workflow reliability plus decision support—not automated collection decisions.

## Proposed TenantEase AI opportunity

TenantEase AI can provide a focused SaaS extension for property managers:

- A monthly rent-obligation ledger.
- Configurable due dates and a documented grace period.
- Idempotent, simulated notification scheduling.
- Verified payment recording and status transitions.
- Historical late-payment risk scoring.
- Explainable indicators and owner-approved recommendations.
- A dashboard that makes collection health visible at portfolio level.

The product can start as a local proof of concept and later evolve toward controlled integrations with payment providers and communication systems.

## Automated monthly rent collection workflow

The implemented workflow is:

1. Generate one rent obligation per active tenant and month.
2. Schedule the configured advance reminder. The assessment convention represents December 1 as a November 26 reminder; the implementation uses a configurable five-calendar-day subtraction to reproduce that convention.
3. Keep an unpaid obligation pending on the due date and through the three-day grace period.
4. Mark the obligation overdue starting on the fifth day for the default first-of-month schedule.
5. Create an overdue alert only once per tenant, rent record, and notification type.
6. Record payments as pending verification.
7. Mark rent paid only after payment verification.

The date simulator exposes November 25, November 26, December 1, December 3, and December 5 as a demonstration sequence without changing historical payment timestamps.

## AI-based late-payment prediction

The proof of concept trains a binary classifier for `late_payment`. Features are restricted to information available seven days before the due date and include rent amount, tenancy length, payment method, previous late count, average historical delay, last delay, on-time rate, previous payment count, and days until due.

The evaluation compares Logistic Regression and Random Forest. It uses a tenant- and time-isolated holdout: training uses tenants 1–160 through their first 22 cycles, while testing uses tenants 161–200 on their final six cycles. No tenant appears in both partitions, and test due dates occur after training due dates.

## Explainable risk classification

Prototype categories are configurable:

| Category | Probability |
|---|---:|
| Low | below 0.30 |
| Medium | 0.30 to below 0.65 |
| High | 0.65 or above |

Explanations summarize historical late count, average delay, and on-time rate. They describe statistical association, not cause. The dashboard distinguishes predicted risk from actual overdue status and requires sufficient verified tenant history before producing a tenant-level score.

## Automated notification simulation

The notification engine is intentionally simulated. It stores recipient, message, scheduled time, simulated send time, type, and delivery status in `notification_logs`. It does not send email, SMS, WhatsApp, or other external messages. This makes the demonstration safe, deterministic, and auditable while leaving an extension point for owner-approved integrations.

## Expected operational benefits

If validated with representative operational data, the opportunity could support:

- More consistent reminder timing.
- Fewer duplicate notifications.
- Faster identification of overdue obligations.
- A clearer separation between recorded and verified payments.
- More focused owner follow-up.
- Better visibility into collection trends.

These are expected workflow benefits, not measured production outcomes from this prototype.

## Business feasibility

The proof of concept is feasible for local deployment. It uses Python, Streamlit, SQLite, SQLAlchemy, Pandas, NumPy, scikit-learn, Plotly, Joblib, and Pytest. It needs no paid API, API key, external messaging provider, or real tenant information.

The next feasibility questions are data access, consent and communication policy, payment reconciliation, identity and access management, model monitoring, and operational ownership of recommendations.

## Risks and limitations

- The dataset is synthetic and may not represent real payment behavior.
- Model probabilities and thresholds are not production-calibrated.
- The current evaluation is not prospective validation.
- Historical patterns can encode unfair or incomplete signals.
- The prototype does not authenticate users or enforce role-based access.
- Notifications are simulated rather than delivered.
- Payment-provider reconciliation is not implemented.
- Demo tenants may lack sufficient verified history for scoring.

## Future opportunities

Potential next steps include probability calibration, prospective monitoring, drift detection, fairness review, payment-provider reconciliation, owner approval workflows, consent-aware communications, role-based access, audit exports, portfolio-level forecasting, and a carefully governed LLM integration for message drafting. Any future AI layer should remain grounded in stored facts and require human approval for outbound communication.

## Conclusion

TenantEase AI demonstrates a coherent product opportunity: pair deterministic rent-collection workflow with explainable, conservative payment-risk prioritization. The strongest near-term value is operational consistency and visibility. The model is a decision-support component, not an automated default decision-maker. Validation with representative, consented operational data is the necessary next step before claims about real-world impact.
