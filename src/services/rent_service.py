from datetime import date
from sqlalchemy.exc import IntegrityError
from database.models import RentRecord, Tenant, Payment, Property
from src.utils.date_utils import safe_due_date, month_key
from src.services.financial_service import reconcile_rent_statuses

def generate_rent_records(s, cycle_date: date, owner_id=None):
    created=[]
    tenants=s.query(Tenant).join(Property, Tenant.property_id == Property.id).filter(Tenant.is_active.is_(True))
    if owner_id is not None: tenants=tenants.filter(Property.owner_id == owner_id)
    for t in tenants:
        due=safe_due_date(cycle_date.year,cycle_date.month,t.due_day); key=month_key(due)
        if not s.query(RentRecord).filter_by(tenant_id=t.id,rent_month=key).first():
            r=RentRecord(tenant_id=t.id,rent_month=key,rent_amount=t.monthly_rent,due_date=due,status="UPCOMING"); s.add(r); created.append(r)
    s.commit(); return created

def refresh_statuses(s, as_of: date, owner_id=None):
    return reconcile_rent_statuses(s,as_of,owner_id)
