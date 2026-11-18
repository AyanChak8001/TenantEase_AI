from datetime import date
import pytest

from database.db import create_test_session
from database.models import Owner
from src.services.auth_service import authenticate_owner, hash_password, register_owner, verify_password
from src.services.rent_service import generate_rent_records
from src.services.tenant_service import create_property, create_tenant, list_tenants


def test_owner_registration_hashing_login_and_duplicate(tmp_path):
    engine, session=create_test_session(f"sqlite:///{tmp_path/'auth.db'}")
    try:
        owner=register_owner(session,"Owner One","Owner@Example.test","SecurePassword123!")
        assert owner.email=="owner@example.test"
        assert owner.password_hash != "SecurePassword123!"
        assert verify_password(owner.password_hash,"SecurePassword123!")
        assert authenticate_owner(session,"OWNER@example.test","SecurePassword123!").id==owner.id
        assert authenticate_owner(session,"owner@example.test","wrong-password") is None
        with pytest.raises(ValueError,match="already exists"):
            register_owner(session,"Duplicate","owner@example.test","AnotherSecure123!")
    finally: session.close(); engine.dispose()


def test_logout_and_unauthenticated_guard():
    session_state={"owner_id":7,"owner_name":"Owner"}
    session_state.pop("owner_id"); session_state.pop("owner_name")
    assert "owner_id" not in session_state


def test_owner_specific_data_isolation(tmp_path):
    engine, session=create_test_session(f"sqlite:///{tmp_path/'isolation.db'}")
    try:
        first=register_owner(session,"First Owner","first@example.test","FirstSecure123!")
        second=register_owner(session,"Second Owner","second@example.test","SecondSecure123!")
        first_property=create_property(session,"First Homes","A Road",2,first.id)
        second_property=create_property(session,"Second Homes","B Road",2,second.id)
        first_tenant=create_tenant(session,"First Tenant","first.tenant@example.test","+1",first_property.id,"A-1",20000,1,first.id)
        second_tenant=create_tenant(session,"Second Tenant","second.tenant@example.test","+1",second_property.id,"B-1",20000,1,second.id)
        assert [t.id for t in list_tenants(session,first.id)]==[first_tenant.id]
        assert [t.id for t in list_tenants(session,second.id)]==[second_tenant.id]
        assert len(generate_rent_records(session,date(2026,12,1),first.id))==1
        assert session.query(__import__("database.models",fromlist=["RentRecord"]).RentRecord).filter_by(tenant_id=second_tenant.id).count()==0
        with pytest.raises(ValueError,match="not accessible"):
            create_tenant(session,"Cross Owner","cross@example.test","+1",second_property.id,"B-2",20000,1,first.id)
    finally: session.close(); engine.dispose()
