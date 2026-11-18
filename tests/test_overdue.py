from datetime import date
from database.db import Base, engine, get_session
from database.models import Tenant, Property
from src.services.rent_service import generate_rent_records, refresh_statuses
from src.services.notification_service import run_notification_simulation

def test_grace_and_overdue(db_session):
 s=db_session; p=Property(property_name="P",address="A",total_units=1); s.add(p); s.flush(); s.add(Tenant(tenant_name="Synthetic",email="x@example.test",phone="x",property_id=p.id,unit_id="1",monthly_rent=1000,due_day=1,lease_start_date=date.today())); s.commit(); r=generate_rent_records(s,date(2025,1,1))[0]; refresh_statuses(s,date(2025,1,3)); assert r.status=="PENDING"; refresh_statuses(s,date(2025,1,5)); assert r.status=="OVERDUE"; assert len(run_notification_simulation(s,date(2025,1,5)))==1; assert len(run_notification_simulation(s,date(2025,1,5)))==0

def test_advance_reminder_scheduling(db_session):
 s=db_session; p=Property(property_name="P",address="A",total_units=1); s.add(p); s.flush(); s.add(Tenant(tenant_name="Synthetic",email="x@example.test",phone="x",property_id=p.id,unit_id="1",monthly_rent=1000,due_day=1,lease_start_date=date.today())); s.commit(); generate_rent_records(s,date(2025,1,1)); assert run_notification_simulation(s,date(2024,12,26))==[]; logs=run_notification_simulation(s,date(2024,12,27)); assert len(logs)==1; assert logs[0].notification_type=="ADVANCE_REMINDER"
