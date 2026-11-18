from datetime import date
from database.models import Property
from src.services.tenant_service import create_property, create_tenant, list_tenants, update_tenant, deactivate_tenant

def test_tenant_and_property_crud(db_session):
    p=create_property(db_session,"Synthetic Homes","Example Road",4)
    t=create_tenant(db_session,"Synthetic Tenant","x@example.test","+91-90000-0000",p.id,"A-01",20000,1)
    assert len(list_tenants(db_session))==1
    update_tenant(db_session,t.id,monthly_rent=22000); assert db_session.get(type(t),t.id).monthly_rent==22000
    deactivate_tenant(db_session,t.id); assert list_tenants(db_session)==[]
