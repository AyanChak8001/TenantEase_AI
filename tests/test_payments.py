from datetime import date
from database.db import Base, engine, get_session
from database.models import Tenant, Property, RentRecord
from src.services.rent_service import generate_rent_records
from src.services.payment_service import record_payment, verify_payment

def test_payment_verification(db_session):
 s=db_session; p=Property(property_name="P",address="A",total_units=1); s.add(p); s.flush(); t=Tenant(tenant_name="Synthetic",email="x@example.test",phone="x",property_id=p.id,unit_id="1",monthly_rent=1000,due_day=1,lease_start_date=date.today()); s.add(t); s.commit(); r=generate_rent_records(s,date(2025,1,1))[0]; pay=record_payment(s,r.id,1000,date(2025,1,1),"UPI","x1"); assert r.status=="UPCOMING"; verify_payment(s,pay.id); assert r.status=="PAID"
