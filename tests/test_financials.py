from datetime import date

from database.models import Payment, Property, RentRecord, Tenant
from src.services.financial_service import portfolio_totals, rent_financials, verified_total
from src.services.payment_service import record_payment, verify_payment
from src.services.rent_service import generate_rent_records, refresh_statuses


def make_rent(session, amount=20000, due=date(2026, 1, 1), email="financial@example.test"):
    prop=Property(property_name="Financial Test Property",address="Synthetic Road",total_units=2); session.add(prop); session.flush()
    tenant=Tenant(tenant_name="Financial Test Tenant",email=email,phone="+1",property_id=prop.id,unit_id="1",monthly_rent=amount,due_day=due.day,lease_start_date=date(2025,1,1)); session.add(tenant); session.commit()
    return generate_rent_records(session,due)[0]


def verified_payment(session, rent, amount, reference):
    payment=record_payment(session,rent.id,amount,rent.due_date,"UPI",reference); verify_payment(session,payment.id); return payment


def test_no_payment_is_not_paid(db_session):
    rent=make_rent(db_session); refresh_statuses(db_session,date(2026,1,1)); assert rent.status=="PENDING"; assert verified_total(db_session,rent.id)==0


def test_partial_payment_is_accumulated_and_not_paid(db_session):
    rent=make_rent(db_session); verified_payment(db_session,rent,15000,"PARTIAL-1"); summary=rent_financials(db_session,rent,date(2026,1,1)); assert summary.status=="PARTIALLY_PAID"; assert summary.verified_total==15000; assert summary.outstanding==5000


def test_multiple_partial_payments_reach_full_payment(db_session):
    rent=make_rent(db_session); verified_payment(db_session,rent,5000,"MULTI-1"); verified_payment(db_session,rent,10000,"MULTI-2"); verified_payment(db_session,rent,5000,"MULTI-3"); summary=rent_financials(db_session,rent,date(2026,1,1)); assert summary.status=="PAID"; assert summary.verified_total==20000; assert summary.outstanding==0


def test_overpayment_is_flagged_and_history_preserved(db_session):
    rent=make_rent(db_session); verified_payment(db_session,rent,25000,"OVER-1"); summary=rent_financials(db_session,rent,date(2026,1,1)); assert summary.status=="PAID"; assert summary.overpayment==5000; assert db_session.query(Payment).count()==1


def test_pending_and_rejected_payments_are_excluded(db_session):
    rent=make_rent(db_session); record_payment(db_session,rent.id,15000,date(2026,1,1),"UPI","PENDING-1"); db_session.add(Payment(rent_record_id=rent.id,amount=5000,payment_date=date(2026,1,1),payment_method="UPI",transaction_reference="REJECTED-1",verification_status="REJECTED")); db_session.commit(); summary=rent_financials(db_session,rent,date(2026,1,1)); assert summary.verified_total==0; assert summary.status=="PENDING"


def test_overdue_partial_balance_is_classified_as_overdue(db_session):
    rent=make_rent(db_session); verified_payment(db_session,rent,15000,"OVERDUE-PARTIAL"); refresh_statuses(db_session,date(2026,1,5)); summary=rent_financials(db_session,rent,date(2026,1,5)); assert rent.status=="PARTIALLY_PAID"; assert summary.is_overdue; assert summary.outstanding==5000


def test_ayan_regression_and_portfolio_aggregation(db_session):
    prop=Property(property_name="Ayan Property",address="Synthetic Road",total_units=1); db_session.add(prop); db_session.flush(); tenant=Tenant(tenant_name="Ayan",email="ayan@example.test",phone="+1",property_id=prop.id,unit_id="A-1",monthly_rent=20000,due_day=1,lease_start_date=date(2025,1,1)); db_session.add(tenant); db_session.commit()
    december=generate_rent_records(db_session,date(2025,12,1))[0]; january=generate_rent_records(db_session,date(2026,1,1))[0]
    verified_payment(db_session,december,15000,"AYAN-DEC"); verified_payment(db_session,january,15000,"AYAN-JAN"); refresh_statuses(db_session,date(2026,1,5)); totals=portfolio_totals(db_session, None, date(2026,1,5)); ayan_records=[r for r in totals["records"] if r.tenant_id==tenant.id]; ayan_summaries=[rent_financials(db_session,r,date(2026,1,5)) for r in ayan_records]
    assert sum(x.rent_amount for x in ayan_summaries)==40000; assert sum(x.verified_total for x in ayan_summaries)==30000; assert sum(x.outstanding for x in ayan_summaries)==10000; assert all(x.status=="PARTIALLY_PAID" for x in ayan_summaries); assert sum(x.verified_total for x in ayan_summaries)/sum(x.rent_amount for x in ayan_summaries)*100==75


def test_multiple_owners_are_not_mixed_in_totals(db_session):
    from database.models import Owner
    first=Owner(full_name="First",email="first-fin@example.test",password_hash="hash"); second=Owner(full_name="Second",email="second-fin@example.test",password_hash="hash"); db_session.add_all([first,second]); db_session.flush(); p1=Property(property_name="First",address="A",total_units=1,owner_id=first.id); p2=Property(property_name="Second",address="B",total_units=1,owner_id=second.id); db_session.add_all([p1,p2]); db_session.flush(); t1=Tenant(tenant_name="One",email="one-fin@example.test",phone="+1",property_id=p1.id,unit_id="1",monthly_rent=10000,due_day=1,lease_start_date=date.today()); t2=Tenant(tenant_name="Two",email="two-fin@example.test",phone="+1",property_id=p2.id,unit_id="1",monthly_rent=30000,due_day=1,lease_start_date=date.today()); db_session.add_all([t1,t2]); db_session.commit(); generate_rent_records(db_session,date(2026,1,1),first.id); generate_rent_records(db_session,date(2026,1,1),second.id); first_totals=portfolio_totals(db_session,first.id,date(2026,1,1)); assert first_totals["expected"]==10000
