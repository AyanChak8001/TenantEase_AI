from datetime import date, timedelta
from config.settings import REMINDER_OFFSET_DAYS
from database.models import NotificationLog, Owner, Payment, Property, Tenant
from src.services.notification_service import PARTIAL_PAYMENT_ALERT, run_notification_simulation
from src.services.payment_service import record_payment, verify_payment
from src.services.rent_service import generate_rent_records
from src.utils.clock import ApplicationClock


def test_business_reminder_date():
    assert date(2025,12,1)-timedelta(days=REMINDER_OFFSET_DAYS)==date(2025,11,26)


def make_notification_rent(session, email="notification@example.test", owner=None, amount=25000):
    if owner is None:
        owner = Owner(full_name="Notification Owner", email=f"owner-{email}", password_hash="hash")
        session.add(owner); session.flush()
    prop = Property(property_name="Notification Property", address="Synthetic Road", total_units=1, owner_id=owner.id)
    session.add(prop); session.flush()
    tenant = Tenant(tenant_name="Notification Tenant", email=email, phone="+1", property_id=prop.id, unit_id="1", monthly_rent=amount, due_day=1, lease_start_date=date(2025,1,1))
    session.add(tenant); session.commit()
    return owner, generate_rent_records(session, date(2026,1,1), owner.id)[0]


def add_verified(session, rent, amount, reference, as_of=date(2026,1,1), owner_id=None):
    payment = record_payment(session, rent.id, amount, rent.due_date, "UPI", reference, owner_id)
    verify_payment(session, payment.id, owner_id, as_of=as_of, now=ApplicationClock.simulated(as_of).now())


def test_partial_payment_alert_uses_outstanding_balance(db_session):
    owner, rent = make_notification_rent(db_session)
    add_verified(db_session, rent, 500, "PARTIAL-NOTIFY-1", owner_id=owner.id)
    alert = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    assert "24,500" in alert.message
    assert "25,000" in alert.message


def test_partially_paid_obligation_gets_overdue_alert(db_session):
    owner, rent = make_notification_rent(db_session, email="overdue-notification@example.test")
    add_verified(db_session, rent, 500, "PARTIAL-OVERDUE-1", owner_id=owner.id)
    created = run_notification_simulation(db_session, date(2026,1,5), owner.id)
    assert any(n.notification_type == "OVERDUE_ALERT" for n in created)
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type="OVERDUE_ALERT").count() == 1


def test_fully_paid_obligation_gets_no_partial_or_overdue_alert(db_session):
    owner, rent = make_notification_rent(db_session, email="full-notification@example.test")
    add_verified(db_session, rent, 25000, "FULL-NOTIFY-1", owner_id=owner.id)
    run_notification_simulation(db_session, date(2026,1,5), owner.id)
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).count() == 0
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type="OVERDUE_ALERT").count() == 0


def test_repeated_partial_simulation_updates_without_duplicates(db_session):
    owner, rent = make_notification_rent(db_session, email="repeat-notification@example.test")
    add_verified(db_session, rent, 500, "REPEAT-NOTIFY-1", owner_id=owner.id)
    first = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    add_verified(db_session, rent, 500, "REPEAT-NOTIFY-2", owner_id=owner.id)
    run_notification_simulation(db_session, date(2026,1,2), owner.id)
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).count() == 1
    assert "24,000" in db_session.get(NotificationLog, first.id).message


def test_multiple_partial_payments_update_outstanding_balance(db_session):
    owner, rent = make_notification_rent(db_session, email="multi-notification@example.test")
    add_verified(db_session, rent, 500, "MULTI-NOTIFY-1", owner_id=owner.id)
    add_verified(db_session, rent, 10000, "MULTI-NOTIFY-2", owner_id=owner.id)
    alert = db_session.query(NotificationLog).filter_by(rent_record_id=rent.id, notification_type=PARTIAL_PAYMENT_ALERT).one()
    assert "14,500" in alert.message


def test_notification_owner_isolation(db_session):
    first, first_rent = make_notification_rent(db_session, email="first-notification@example.test")
    second, second_rent = make_notification_rent(db_session, email="second-notification@example.test")
    add_verified(db_session, first_rent, 500, "OWNER-NOTIFY-1", owner_id=first.id)
    add_verified(db_session, second_rent, 500, "OWNER-NOTIFY-2", owner_id=second.id)
    first_logs = run_notification_simulation(db_session, date(2026,1,5), first.id)
    assert all(log.tenant_id == first_rent.tenant_id for log in db_session.query(NotificationLog).filter_by(rent_record_id=first_rent.id).all())
    assert all(log.rent_record_id != second_rent.id for log in first_logs)
    assert db_session.query(NotificationLog).filter_by(rent_record_id=second_rent.id).count() == 1
