from datetime import date, datetime

import pytest

from database.models import NotificationLog, Owner, Payment, PredictionLog, Property, RentRecord, Tenant
from src.services.auth_service import hash_password, verify_password
from src.services.rent_service import generate_rent_records
from src.services.workspace_service import delete_tenant, reset_owner_workspace


def make_owner_workspace(session, label):
    owner = Owner(full_name=f"{label} Owner", email=f"{label.lower()}@example.test", password_hash=hash_password("SecurePassword123!"))
    session.add(owner); session.flush()
    prop = Property(property_name=f"{label} Property", address="Synthetic Road", total_units=2, owner_id=owner.id)
    session.add(prop); session.flush()
    tenant = Tenant(tenant_name=f"{label} Tenant", email=f"{label.lower()}.tenant@example.test", phone="+1", property_id=prop.id, unit_id="A-1", monthly_rent=20000, due_day=1, lease_start_date=date(2025,1,1))
    session.add(tenant); session.commit()
    rent = generate_rent_records(session, date(2026,1,1), owner.id)[0]
    return owner, prop, tenant, rent


def add_dependent_rows(session, tenant, rent, prefix):
    session.add_all([
        Payment(rent_record_id=rent.id, amount=1000, payment_date=rent.due_date, payment_method="UPI", transaction_reference=f"{prefix}-PAY"),
        NotificationLog(tenant_id=tenant.id, rent_record_id=rent.id, notification_type="ADVANCE_REMINDER", recipient=tenant.email, message="Synthetic", scheduled_at=datetime.now()),
        PredictionLog(tenant_id=tenant.id, rent_record_id=rent.id, risk_probability=0.5, risk_category="Medium", model_version="test", prediction_date=rent.due_date, explanation="Synthetic"),
    ])
    session.commit()


def test_reset_removes_one_owner_workspace_preserves_owner_and_other_owner(db_session):
    first, first_property, first_tenant, first_rent = make_owner_workspace(db_session, "First")
    second, second_property, second_tenant, second_rent = make_owner_workspace(db_session, "Second")
    add_dependent_rows(db_session, first_tenant, first_rent, "FIRST")
    add_dependent_rows(db_session, second_tenant, second_rent, "SECOND")
    original_hash = first.password_hash

    counts = reset_owner_workspace(db_session, first.id)

    assert counts == {"properties": 1, "tenants": 1, "rent_records": 1}
    assert db_session.get(Owner, first.id).password_hash == original_hash
    assert verify_password(original_hash, "SecurePassword123!")
    assert db_session.get(Property, first_property.id) is None
    assert db_session.get(Tenant, first_tenant.id) is None
    assert db_session.get(RentRecord, first_rent.id) is None
    assert db_session.get(Property, second_property.id) is not None
    assert db_session.get(Tenant, second_tenant.id) is not None
    assert db_session.get(RentRecord, second_rent.id) is not None
    assert db_session.query(Payment).filter_by(rent_record_id=second_rent.id).count() == 1
    assert db_session.query(NotificationLog).filter_by(rent_record_id=second_rent.id).count() == 1
    assert db_session.query(PredictionLog).filter_by(rent_record_id=second_rent.id).count() == 1


def test_repeated_reset_on_empty_workspace_is_safe(db_session):
    owner, _, _, _ = make_owner_workspace(db_session, "Empty")
    reset_owner_workspace(db_session, owner.id)
    counts = reset_owner_workspace(db_session, owner.id)
    assert counts == {"properties": 0, "tenants": 0, "rent_records": 0}
    assert db_session.get(Owner, owner.id) is not None


def test_tenant_deletion_removes_dependents_and_preserves_property(db_session):
    owner, prop, tenant, rent = make_owner_workspace(db_session, "Delete")
    add_dependent_rows(db_session, tenant, rent, "DELETE")

    counts = delete_tenant(db_session, tenant.id, owner.id)

    assert counts == {"tenants": 1, "rent_records": 1}
    assert db_session.get(Property, prop.id) is not None
    assert db_session.get(Tenant, tenant.id) is None
    assert db_session.get(RentRecord, rent.id) is None
    assert db_session.query(Payment).filter_by(rent_record_id=rent.id).count() == 0
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id).count() == 0
    assert db_session.query(PredictionLog).filter_by(rent_record_id=rent.id).count() == 0


def test_tenant_deletion_cannot_cross_owner_boundary(db_session):
    first, _, first_tenant, _ = make_owner_workspace(db_session, "Allowed")
    second, second_property, second_tenant, second_rent = make_owner_workspace(db_session, "Protected")

    with pytest.raises(ValueError, match="not accessible"):
        delete_tenant(db_session, second_tenant.id, first.id)

    assert db_session.get(Tenant, second_tenant.id) is not None
    assert db_session.get(Property, second_property.id) is not None
    assert db_session.get(RentRecord, second_rent.id) is not None
    assert db_session.get(Tenant, first_tenant.id) is not None


def test_reset_rolls_back_when_deletion_fails(db_session, monkeypatch):
    owner, prop, tenant, rent = make_owner_workspace(db_session, "Rollback")
    add_dependent_rows(db_session, tenant, rent, "ROLLBACK")

    def fail_flush():
        raise RuntimeError("synthetic deletion failure")

    monkeypatch.setattr(db_session, "flush", fail_flush)
    with pytest.raises(RuntimeError, match="synthetic deletion failure"):
        reset_owner_workspace(db_session, owner.id)

    assert db_session.get(Owner, owner.id) is not None
    assert db_session.get(Property, prop.id) is not None
    assert db_session.get(Tenant, tenant.id) is not None
    assert db_session.get(RentRecord, rent.id) is not None
    assert db_session.query(Payment).filter_by(rent_record_id=rent.id).count() == 1
    assert db_session.query(NotificationLog).filter_by(rent_record_id=rent.id).count() == 1
    assert db_session.query(PredictionLog).filter_by(rent_record_id=rent.id).count() == 1
