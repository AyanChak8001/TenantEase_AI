from datetime import date, datetime

from database.models import NotificationLog
from src.services.notification_service import (
    FULL_PAYMENT_CONFIRMATION,
    OVERDUE_ALERT,
    PARTIAL_PAYMENT_ALERT,
    process_due_notifications,
    retry_failed_notification,
    ensure_scheduled_business_notifications,
)
from src.services.payment_service import record_payment, verify_payment
from src.services.rent_service import generate_rent_records
from src.services import scheduler_service
from src.utils.clock import ApplicationClock

from tests.test_notifications import add_verified, make_notification_rent


def future_rent(session, email):
    owner, rent = make_notification_rent(session, email=email)
    rent.due_date = date(2026, 1, 3)
    session.commit()
    return owner, rent


def test_payment_notification_is_scheduled_for_due_date_at_nine(db_session):
    owner, rent = future_rent(db_session, "scheduled@example.test")
    add_verified(db_session, rent, 500, "SCHEDULED-1", as_of=date(2026, 1, 1), owner_id=owner.id)
    notification = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    assert notification.scheduled_at == datetime(2026, 1, 3, 9, 0)
    assert notification.sent_at is None
    assert notification.delivery_status == "SCHEDULED"


def test_second_partial_payment_updates_pending_notification(db_session):
    owner, rent = future_rent(db_session, "update-scheduled@example.test")
    add_verified(db_session, rent, 500, "UPDATE-1", as_of=date(2026, 1, 1), owner_id=owner.id)
    add_verified(db_session, rent, 10000, "UPDATE-2", as_of=date(2026, 1, 1), owner_id=owner.id)
    notifications = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).all()
    assert len(notifications) == 1
    assert "14,500" in notifications[0].message
    assert notifications[0].delivery_status == "SCHEDULED"


def test_full_payment_cancels_partial_and_schedules_confirmation(db_session):
    owner, rent = future_rent(db_session, "full-scheduled@example.test")
    add_verified(db_session, rent, 500, "FULL-1", as_of=date(2026, 1, 1), owner_id=owner.id)
    payment = record_payment(db_session, rent.id, 24500, rent.due_date, "UPI", "FULL-2", owner.id)
    verify_payment(db_session, payment.id, owner.id, as_of=date(2026, 1, 1), now=ApplicationClock.simulated(date(2026, 1, 1)).now())
    partial = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    confirmation = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=FULL_PAYMENT_CONFIRMATION).one()
    assert partial.delivery_status == "CANCELLED"
    assert confirmation.delivery_status == "SCHEDULED"
    assert confirmation.scheduled_at == datetime(2026, 1, 3, 9, 0)


def test_due_notifications_are_processed_once_and_future_stays_scheduled(db_session):
    owner, rent = future_rent(db_session, "process-scheduled@example.test")
    add_verified(db_session, rent, 500, "PROCESS-1", as_of=date(2026, 1, 1), owner_id=owner.id)
    assert process_due_notifications(db_session, datetime(2026, 1, 2, 10), owner.id) == []
    notification = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    assert notification.delivery_status == "SCHEDULED"
    assert len(process_due_notifications(db_session, datetime(2026, 1, 3, 9), owner.id)) == 1
    assert process_due_notifications(db_session, datetime(2026, 1, 3, 10), owner.id) == []
    assert db_session.get(NotificationLog, notification.id).delivery_status == "SENT_SIMULATED"


def test_failed_delivery_can_be_retried(db_session):
    owner, rent = future_rent(db_session, "retry-scheduled@example.test")
    add_verified(db_session, rent, 500, "RETRY-1", as_of=date(2026, 1, 1), owner_id=owner.id)

    def fail(_notification):
        raise RuntimeError("synthetic delivery failure")

    assert process_due_notifications(db_session, datetime(2026, 1, 3, 9), owner.id, fail) == []
    notification = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    assert notification.delivery_status == "FAILED"
    retry_failed_notification(db_session, notification.id, owner.id)
    assert db_session.get(NotificationLog, notification.id).delivery_status == "SCHEDULED"
    assert len(process_due_notifications(db_session, datetime(2026, 1, 3, 10), owner.id)) == 1


def test_scheduler_processing_is_owner_scoped(db_session):
    first, first_rent = future_rent(db_session, "scheduler-first@example.test")
    second, second_rent = future_rent(db_session, "scheduler-second@example.test")
    add_verified(db_session, first_rent, 500, "OWNER-SCHED-1", as_of=date(2026, 1, 1), owner_id=first.id)
    add_verified(db_session, second_rent, 500, "OWNER-SCHED-2", as_of=date(2026, 1, 1), owner_id=second.id)
    delivered = process_due_notifications(db_session, datetime(2026, 1, 3, 9), first.id)
    assert len(delivered) == 1
    first_log = db_session.query(NotificationLog).filter_by(rent_record_id=first_rent.id).one()
    second_log = db_session.query(NotificationLog).filter_by(rent_record_id=second_rent.id).one()
    assert first_log.delivery_status == "SENT_SIMULATED"
    assert second_log.delivery_status == "SCHEDULED"


def test_partially_paid_overdue_notification_is_scheduled(db_session):
    owner, rent = make_notification_rent(db_session, email="overdue-scheduled@example.test")
    add_verified(db_session, rent, 500, "OVERDUE-SCHED-1", as_of=date(2026, 1, 5), owner_id=owner.id)
    overdue = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=OVERDUE_ALERT).one()
    assert overdue.delivery_status == "SCHEDULED"
    assert "24,500" in overdue.message


def test_scheduler_start_is_singleton():
    scheduler_service.stop_scheduler()
    first = scheduler_service.start_scheduler()
    second = scheduler_service.start_scheduler()
    try:
        assert first is second
        assert first.running
    finally:
        scheduler_service.stop_scheduler()


def test_december_19_simulated_clock_generates_and_delivers_unpaid_overdue(db_session):
    owner, november = make_notification_rent(db_session, email="december-clock@example.test", amount=20000)
    november.rent_month = "2026-11"
    november.due_date = date(2026, 11, 1)
    db_session.commit()
    december = generate_rent_records(db_session, date(2026, 12, 1), owner.id)[0]
    simulated_now = ApplicationClock.simulated(date(2026, 12, 19)).now()

    created = ensure_scheduled_business_notifications(db_session, simulated_now, owner.id)
    delivered = process_due_notifications(db_session, simulated_now, owner.id)
    december_alerts = [n for n in delivered if n.rent_record_id == december.id and n.notification_type == OVERDUE_ALERT]

    assert len(december_alerts) == 1
    alert = december_alerts[0]
    assert alert.created_at == simulated_now
    assert alert.scheduled_at == simulated_now
    assert alert.sent_at == simulated_now
    assert alert.delivery_status == "SENT_SIMULATED"
    assert "20,000" in alert.message
    assert any(n.rent_record_id == november.id for n in created)
    assert alert.rent_record_id != november.id


def test_december_19_simulated_clock_handles_partially_paid_overdue(db_session):
    owner, rent = make_notification_rent(db_session, email="december-partial-clock@example.test")
    rent.due_date = date(2026, 12, 1)
    rent.rent_month = "2026-12"
    db_session.commit()
    add_verified(db_session, rent, 5000, "DECEMBER-PARTIAL-CLOCK", as_of=date(2026, 12, 19), owner_id=owner.id)
    simulated_now = ApplicationClock.simulated(date(2026, 12, 19)).now()
    ensure_scheduled_business_notifications(db_session, simulated_now, owner.id)
    delivered = process_due_notifications(db_session, simulated_now, owner.id)
    overdue = [n for n in delivered if n.rent_record_id == rent.id and n.notification_type == OVERDUE_ALERT]
    assert len(overdue) == 1
    assert "20,000" in overdue[0].message


def test_full_payment_cancels_simulated_pending_overdue_alert(db_session):
    owner, rent = make_notification_rent(db_session, email="december-full-clock@example.test")
    rent.due_date = date(2026, 12, 1)
    rent.rent_month = "2026-12"
    db_session.commit()
    simulated_now = ApplicationClock.simulated(date(2026, 12, 19)).now()
    ensure_scheduled_business_notifications(db_session, simulated_now, owner.id)
    payment = record_payment(db_session, rent.id, 25000, rent.due_date, "UPI", "DECEMBER-FULL-CLOCK", owner.id)
    verify_payment(db_session, payment.id, owner.id, as_of=date(2026, 12, 19), now=simulated_now)
    overdue = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=OVERDUE_ALERT).one()
    assert overdue.delivery_status == "CANCELLED"
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=FULL_PAYMENT_CONFIRMATION).one().delivery_status == "SCHEDULED"


def test_simulated_and_real_clocks_do_not_deliver_future_december_event_early(db_session):
    owner, rent = make_notification_rent(db_session, email="clock-boundary@example.test")
    rent.due_date = date(2026, 12, 1)
    rent.rent_month = "2026-12"
    db_session.commit()
    real_now = ApplicationClock.real().now()
    ensure_scheduled_business_notifications(db_session, real_now, owner.id)
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=OVERDUE_ALERT).count() == 0
    simulated_now = ApplicationClock.simulated(date(2026, 12, 19)).now()
    assert process_due_notifications(db_session, simulated_now, owner.id) == []
    ensure_scheduled_business_notifications(db_session, simulated_now, owner.id)
    assert len(process_due_notifications(db_session, simulated_now, owner.id)) == 1
