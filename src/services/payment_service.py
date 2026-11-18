from datetime import date, datetime
from database.models import Payment, RentRecord, Tenant, Property
from src.services.financial_service import reconcile_rent_statuses

def _owned_rent(s, rent_record_id, owner_id):
    rent=s.query(RentRecord).join(Tenant, RentRecord.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id).filter(RentRecord.id == rent_record_id)
    if owner_id is not None: rent=rent.filter(Property.owner_id == owner_id)
    return rent.first()

def record_payment(s, rent_record_id, amount, payment_date, method, reference, owner_id=None):
    if not _owned_rent(s,rent_record_id,owner_id): raise ValueError("Rent record is not accessible to this owner.")
    p=Payment(rent_record_id=rent_record_id,amount=amount,payment_date=payment_date,payment_method=method,transaction_reference=reference,verification_status="PENDING"); s.add(p); s.commit(); return p
def verify_payment(s, payment_id, owner_id=None):
    p=s.get(Payment,payment_id); r=_owned_rent(s,p.rent_record_id,owner_id) if p else None
    if not p or not r: raise ValueError("Payment is not accessible to this owner.")
    p.verification_status="VERIFIED"; s.commit()
    reconcile_rent_statuses(s,date.today(),owner_id)
    return s.get(RentRecord,r.id)
