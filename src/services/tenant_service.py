from datetime import date
from database.models import Tenant, Property

def list_tenants(s, owner_id=None):
    query=s.query(Tenant).join(Property, Tenant.property_id == Property.id).filter(Tenant.is_active.is_(True))
    if owner_id is not None: query=query.filter(Property.owner_id == owner_id)
    return query.order_by(Tenant.id).all()
def list_properties(s): return s.query(Property).order_by(Property.id).all()
def list_owned_properties(s, owner_id): return s.query(Property).filter_by(owner_id=owner_id).order_by(Property.id).all()
def create_property(s, name, address, total_units, owner_id=None):
    p=Property(property_name=name,address=address,total_units=total_units,owner_id=owner_id); s.add(p); s.commit(); return p
def update_tenant(s, tenant_id, owner_id=None, **changes):
    t=s.get(Tenant,tenant_id)
    if not t or (owner_id is not None and s.query(Property).filter_by(id=t.property_id,owner_id=owner_id).first() is None): raise ValueError("Tenant is not accessible to this owner.")
    for key,value in changes.items():
        if hasattr(t,key): setattr(t,key,value)
    s.commit(); return t
def deactivate_tenant(s, tenant_id):
    t=s.get(Tenant,tenant_id); t.is_active=False; s.commit(); return t
def create_tenant(s, name,email,phone,property_id,unit_id,rent,due_day=1, owner_id=None):
    prop=s.get(Property, property_id)
    if not prop or (owner_id is not None and prop.owner_id != owner_id): raise ValueError("Property is not accessible to this owner.")
    t=Tenant(tenant_name=name,email=email,phone=phone,property_id=property_id,unit_id=unit_id,monthly_rent=rent,due_day=due_day,lease_start_date=date.today()); s.add(t); s.commit(); return t
