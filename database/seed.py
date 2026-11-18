from datetime import date
from database.db import init_db, get_session
from database.models import Owner, Property, Tenant
from src.services.auth_service import hash_password

def seed_demo() -> None:
    init_db(); s = get_session()
    try:
        owner = s.query(Owner).filter_by(email="demo.owner@example.test").first()
        if not owner:
            owner = Owner(full_name="TenantEase Demo Owner", email="demo.owner@example.test", password_hash=hash_password("DemoOwner123!"), is_active=True)
            s.add(owner); s.flush()
        for existing in s.query(Property).filter(Property.owner_id.is_(None)).all(): existing.owner_id = owner.id
        if s.query(Tenant).count(): s.commit(); return
        p = Property(property_name="TenantEase Demo Homes", address="100 Example Avenue", total_units=20, owner_id=owner.id)
        s.add(p); s.flush()
        for i in range(1, 11):
            s.add(Tenant(tenant_name=f"Synthetic Tenant {i:03d}", email=f"tenant{i:03d}@example.test", phone=f"+91-90000-{i:04d}", property_id=p.id, unit_id=f"A-{i:02d}", monthly_rent=18000 + i * 750, due_day=1, lease_start_date=date(2023, 1, 1)))
        s.commit()
    finally: s.close()
