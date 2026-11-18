"""Event-driven notification creation and simulated delivery."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from config.settings import APPLICATION_TIMEZONE, REMINDER_OFFSET_DAYS
from database.models import NotificationLog, Payment, Property, RentRecord, Tenant
from src.services.financial_service import rent_financials
from src.utils.clock import ApplicationClock

ADVANCE_REMINDER = "ADVANCE_REMINDER"
PARTIAL_PAYMENT_ALERT = "PARTIAL_PAYMENT_ALERT"
FULL_PAYMENT_CONFIRMATION = "FULL_PAYMENT_CONFIRMATION"
OVERDUE_ALERT = "OVERDUE_ALERT"
NOTIFICATION_TYPES = [ADVANCE_REMINDER, PARTIAL_PAYMENT_ALERT, FULL_PAYMENT_CONFIRMATION, OVERDUE_ALERT]
ACTIVE_STATUSES = ("SCHEDULED", "PROCESSING")
__all__ = [
    "ADVANCE_REMINDER",
    "PARTIAL_PAYMENT_ALERT",
    "FULL_PAYMENT_CONFIRMATION",
    "OVERDUE_ALERT",
    "NOTIFICATION_TYPES",
    "local_now",
    "create_payment_notifications",
    "ensure_scheduled_business_notifications",
    "run_notification_simulation",
    "process_due_notifications",
    "retry_failed_notification",
]


def local_now() -> datetime:
    """Return a real naive local timestamp consistent with SQLite fields."""
    return ApplicationClock.real().now()


def _scheduled_for_due_date(rent_record: RentRecord, now: datetime) -> datetime:
    """Use due-date 09:00 unless that time has passed, then deliver promptly."""
    return max(datetime.combine(rent_record.due_date, time(hour=9)), now)


def _owner_can_access(session, tenant: Tenant, owner_id: int | None) -> bool:
    query = session.query(Property).filter(Property.id == tenant.property_id)
    if owner_id is not None:
        query = query.filter(Property.owner_id == owner_id)
    return query.first() is not None


def _message(tenant, rent, notification_type, received=0.0, outstanding=0.0):
    if notification_type == PARTIAL_PAYMENT_ALERT:
        return f"Hello {tenant.tenant_name}, we have recorded your payment of INR {received:,.0f} against your monthly rent of INR {rent.rent_amount:,.0f}. Your remaining balance is INR {outstanding:,.0f}. Rent due date: {rent.due_date:%d %b %Y}. Thank you."
    if notification_type == FULL_PAYMENT_CONFIRMATION:
        return f"Hello {tenant.tenant_name}, we have received your full rent payment of INR {received:,.0f} for the rent due on {rent.due_date:%d %b %Y}. Thank you."
    if notification_type == OVERDUE_ALERT:
        return f"Hello {tenant.tenant_name}, our records indicate that an outstanding rent balance of INR {outstanding:,.0f}, due on {rent.due_date:%d %b %Y}, has not yet been recorded. Please contact your property manager if you have already completed the payment."
    return f"Hello {tenant.tenant_name}, this is a friendly reminder that your monthly rent of INR {rent.rent_amount:,.0f} is due on {rent.due_date:%d %b %Y}. Please ensure that your payment is completed on time. Thank you - TenantEase."


def _new_notification(session, tenant, rent, notification_type, message, scheduled_at, event_key, created_at):
    notification = NotificationLog(
        tenant_id=tenant.id,
        rent_record_id=rent.id,
        notification_type=notification_type,
        event_key=event_key,
        recipient=tenant.email,
        message=message,
        scheduled_at=scheduled_at,
        sent_at=None,
        delivery_status="SCHEDULED",
        created_at=created_at,
    )
    session.add(notification)
    return notification


def _existing_event(session, rent, notification_type):
    return session.query(NotificationLog).filter_by(
        tenant_id=rent.tenant_id,
        rent_record_id=rent.id,
        notification_type=notification_type,
    ).filter(NotificationLog.delivery_status != "CANCELLED").order_by(NotificationLog.id.desc()).first()


def _cancel_pending(session, rent, notification_types):
    session.query(NotificationLog).filter(
        NotificationLog.rent_record_id == rent.id,
        NotificationLog.notification_type.in_(notification_types),
        NotificationLog.delivery_status.in_(ACTIVE_STATUSES),
    ).update({"delivery_status": "CANCELLED"}, synchronize_session=False)


def create_payment_notifications(session, rent, payment: Payment, as_of: date | None = None, owner_id: int | None = None, now: datetime | None = None):
    """Create/update payment notifications after a verified payment.

    Pending partial notifications are updated in place. Sent notifications are
    immutable; a later partial event receives a new event key.
    """
    tenant = session.get(Tenant, rent.tenant_id)
    if not tenant or not _owner_can_access(session, tenant, owner_id):
        raise ValueError("Rent record is not accessible to this owner.")
    now = now or local_now()
    as_of = as_of or now.date()
    summary = rent_financials(session, rent, as_of)
    scheduled = _scheduled_for_due_date(rent, now)
    created = []
    if summary.status == "PARTIALLY_PAID":
        pending = session.query(NotificationLog).filter_by(
            tenant_id=tenant.id, rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT,
        ).filter(NotificationLog.delivery_status.in_(ACTIVE_STATUSES)).order_by(NotificationLog.id.desc()).first()
        message = _message(tenant, rent, PARTIAL_PAYMENT_ALERT, summary.verified_total, summary.outstanding)
        if pending:
            pending.message = message
            pending.scheduled_at = scheduled
        else:
            created.append(_new_notification(session, tenant, rent, PARTIAL_PAYMENT_ALERT, message, scheduled, f"partial-payment-{payment.id}", now))
        if summary.is_overdue:
            overdue = _existing_event(session, rent, OVERDUE_ALERT)
            if overdue is None:
                created.append(_new_notification(session, tenant, rent, OVERDUE_ALERT, _message(tenant, rent, OVERDUE_ALERT, outstanding=summary.outstanding), now, f"overdue-{rent.id}", now))
    elif summary.status == "PAID":
        _cancel_pending(session, rent, [PARTIAL_PAYMENT_ALERT, OVERDUE_ALERT])
        if _existing_event(session, rent, FULL_PAYMENT_CONFIRMATION) is None:
            created.append(_new_notification(session, tenant, rent, FULL_PAYMENT_CONFIRMATION, _message(tenant, rent, FULL_PAYMENT_CONFIRMATION, summary.verified_total), scheduled, f"full-payment-{payment.id}", now))
    session.commit()
    return created


def ensure_scheduled_business_notifications(session, now: datetime | None = None, owner_id: int | None = None):
    """Create advance and overdue events for all currently eligible obligations."""
    now = now or local_now()
    as_of = now.date()
    query = session.query(RentRecord).join(Tenant, RentRecord.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id)
    if owner_id is not None:
        query = query.filter(Property.owner_id == owner_id)
    created = []
    for rent in query.all():
        tenant = session.get(Tenant, rent.tenant_id)
        summary = rent_financials(session, rent, as_of)
        reminder_date = rent.due_date - timedelta(days=REMINDER_OFFSET_DAYS)
        if reminder_date <= as_of < rent.due_date and summary.outstanding > 0 and _existing_event(session, rent, ADVANCE_REMINDER) is None:
            planned = max(datetime.combine(reminder_date, time(hour=9)), now)
            created.append(_new_notification(session, tenant, rent, ADVANCE_REMINDER, _message(tenant, rent, ADVANCE_REMINDER), planned, f"advance-{rent.id}", now))
        if summary.is_overdue and _existing_event(session, rent, OVERDUE_ALERT) is None:
            created.append(_new_notification(session, tenant, rent, OVERDUE_ALERT, _message(tenant, rent, OVERDUE_ALERT, outstanding=summary.outstanding), now, f"overdue-{rent.id}", now))
    session.commit()
    return created


def run_notification_simulation(session, as_of, owner_id=None):
    """Backward-compatible deterministic helper for existing date-boundary tests.

    Production delivery is scheduler-driven; this helper only creates events at
    a supplied demonstration date and does not mark them as delivered.
    """
    return ensure_scheduled_business_notifications(session, datetime.combine(as_of, time(hour=12)), owner_id)


def process_due_notifications(session, now: datetime | None = None, owner_id: int | None = None, delivery=None):
    """Claim and deliver due simulated notifications exactly once per run."""
    now = now or local_now()
    query = session.query(NotificationLog).join(Tenant, NotificationLog.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id).filter(
        NotificationLog.delivery_status == "SCHEDULED", NotificationLog.scheduled_at <= now,
    )
    if owner_id is not None:
        query = query.filter(Property.owner_id == owner_id)
    due_ids = [row.id for row in query.order_by(NotificationLog.id).all()]
    delivered = []
    for notification_id in due_ids:
        claimed = session.query(NotificationLog).filter_by(id=notification_id, delivery_status="SCHEDULED").update({"delivery_status": "PROCESSING"}, synchronize_session=False)
        session.commit()
        if not claimed:
            continue
        notification = session.get(NotificationLog, notification_id)
        try:
            if delivery:
                delivery(notification)
            notification.delivery_status = "SENT_SIMULATED"
            notification.sent_at = now
            session.commit()
            delivered.append(notification)
        except Exception:
            notification.delivery_status = "FAILED"
            session.commit()
    return delivered


def retry_failed_notification(session, notification_id: int, owner_id: int | None = None):
    """Return one failed, owner-scoped notification to the scheduler queue."""
    query = session.query(NotificationLog).join(Tenant, NotificationLog.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id).filter(
        NotificationLog.id == notification_id, NotificationLog.delivery_status == "FAILED",
    )
    if owner_id is not None:
        query = query.filter(Property.owner_id == owner_id)
    notification = query.first()
    if notification is None:
        raise ValueError("Notification is not accessible or is not failed.")
    notification.delivery_status = "SCHEDULED"
    notification.sent_at = None
    session.commit()
    return notification
