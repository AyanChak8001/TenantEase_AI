"""Create a safe, repeatable TenantEase browser-demo database.

Usage:
    python scripts/seed_demo_database.py

The database is written to demo/tenantease_demo.db and never touches the
default tenantease.db. All names, contacts, payments, and references are
synthetic.
"""
from datetime import date
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEMO_DIR = ROOT / "demo"
DEMO_DIR.mkdir(exist_ok=True)
DEMO_DB = DEMO_DIR / "tenantease_demo.db"
os.environ["TENANTEASE_DATABASE_URL"] = f"sqlite:///{DEMO_DB}"

from database.db import init_db  # noqa: E402
from database.models import Owner, Property, Tenant  # noqa: E402
from src.services.auth_service import hash_password  # noqa: E402
from src.services.notification_service import run_notification_simulation  # noqa: E402
from src.services.payment_service import record_payment, verify_payment  # noqa: E402
from src.services.rent_service import generate_rent_records, refresh_statuses  # noqa: E402


def main():
    if DEMO_DB.exists():
        DEMO_DB.unlink()
    init_db()
    session = __import__("database.db", fromlist=["get_session"]).get_session()
    try:
        owner = Owner(full_name="TenantEase Assessment Demo Owner", email="demo.owner@example.test", password_hash=hash_password("DemoOwner123!"), is_active=True)
        session.add(owner); session.flush()
        prop = Property(property_name="TenantEase Assessment Demo", address="100 Synthetic Avenue", total_units=8, owner_id=owner.id)
        session.add(prop)
        session.flush()
        profiles = [
            ("Demo On-Time Tenant", "on_time", 1),
            ("Demo Occasional Delay", "occasional", 1),
            ("Demo Frequent Delay", "frequent", 1),
            ("Demo Pending Tenant", "pending", 5),
            ("Demo Verified Tenant", "verified", 1),
            ("Demo No-History Tenant", "no_history", 1),
        ]
        tenants = []
        for index, (name, profile, due_day) in enumerate(profiles, 1):
            tenant = Tenant(tenant_name=name, email=f"demo{index}@example.test", phone=f"+91-90000-{index:04d}", property_id=prop.id, unit_id=f"D-{index:02d}", monthly_rent=20000 + index * 1000, due_day=due_day, lease_start_date=date(2025, 1, 1))
            session.add(tenant); session.flush(); tenants.append((tenant, profile))
        session.commit()

        cycles = [date(2026, month, 1) for month in (7, 8, 9, 10, 11)]
        for cycle in cycles:
            generate_rent_records(session, cycle)

        delays = {"on_time": [0, 0, 0, 0], "occasional": [0, 3, 0, 0], "frequent": [5, 6, 4, 7], "pending": [0, 0, 0, 0], "verified": [0, 0, 0, 0]}
        for tenant, profile in tenants:
            if profile == "no_history":
                continue
            history = session.query(__import__("database.models", fromlist=["RentRecord"]).RentRecord).filter_by(tenant_id=tenant.id).order_by(__import__("database.models", fromlist=["RentRecord"]).RentRecord.due_date).all()
            for position, delay in enumerate(delays[profile]):
                rent = history[position]
                payment_date = rent.due_date.fromordinal(rent.due_date.toordinal() + delay)
                payment = record_payment(session, rent.id, rent.rent_amount, payment_date, "UPI", f"DEMO-{tenant.id}-{position}")
                verify_payment(session, payment.id)
            if profile == "verified":
                current = history[-1]
                payment = record_payment(session, current.id, current.rent_amount, current.due_date, "BANK_TRANSFER", f"DEMO-{tenant.id}-current")
                verify_payment(session, payment.id)

        refresh_statuses(session, date(2026, 10, 27))
        run_notification_simulation(session, date(2026, 10, 27))
        refresh_statuses(session, date(2026, 11, 5))
        run_notification_simulation(session, date(2026, 11, 5))
        print(f"Created {DEMO_DB}")
        print("Demo date: 2026-11-05")
        print("Profiles: on-time, occasional delay, frequent delay, pending due-day-5, verified, and insufficient-history")
    finally:
        session.close()


if __name__ == "__main__":
    main()
