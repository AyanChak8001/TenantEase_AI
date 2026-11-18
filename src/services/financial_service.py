"""Single source of truth for rent balances and portfolio financial totals."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from sqlalchemy import func
from database.models import Payment, Property, RentRecord, Tenant

VERIFIED = "VERIFIED"

@dataclass(frozen=True)
class RentFinancials:
    rent_amount: float
    verified_total: float
    outstanding: float
    overpayment: float
    status: str
    is_overdue: bool

def verified_total(session, rent_record_id: int) -> float:
    value=session.query(func.coalesce(func.sum(Payment.amount), 0.0)).filter(Payment.rent_record_id == rent_record_id, Payment.verification_status == VERIFIED).scalar()
    return float(value or 0.0)

def calculate_rent_financials(rent: RentRecord, received: float, as_of: date) -> RentFinancials:
    amount=float(rent.rent_amount); received=float(received)
    outstanding=max(0.0, amount-received); overpayment=max(0.0, received-amount)
    is_overdue=as_of >= rent.due_date + timedelta(days=4)
    if received >= amount:
        status="PAID"
    elif received > 0:
        status="PARTIALLY_PAID"
    elif as_of < rent.due_date:
        status="UPCOMING"
    elif not is_overdue:
        status="PENDING"
    else:
        status="OVERDUE"
    return RentFinancials(amount,received,outstanding,overpayment,status,is_overdue and outstanding > 0)

def rent_financials(session, rent: RentRecord, as_of: date) -> RentFinancials:
    return calculate_rent_financials(rent, verified_total(session,rent.id), as_of)

def owned_rents(session, owner_id=None):
    query=session.query(RentRecord).join(Tenant, RentRecord.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id)
    if owner_id is not None: query=query.filter(Property.owner_id == owner_id)
    return query.order_by(RentRecord.due_date.desc()).all()

def reconcile_rent_statuses(session, as_of: date, owner_id=None):
    """Reconcile stored statuses against all verified transactions without deleting history."""
    changed=[]
    for rent in owned_rents(session,owner_id):
        summary=rent_financials(session,rent,as_of)
        if rent.status != summary.status:
            rent.status=summary.status; changed.append(rent.id)
        if summary.status == "PAID":
            payments=session.query(Payment).filter_by(rent_record_id=rent.id,verification_status=VERIFIED).order_by(Payment.payment_date.desc(),Payment.id.desc()).all()
            if payments: rent.paid_at=datetime.combine(payments[0].payment_date,datetime.min.time())
        else: rent.paid_at=None
    session.commit(); return changed

def portfolio_totals(session, owner_id, as_of: date):
    records=owned_rents(session,owner_id); summaries=[rent_financials(session,r,as_of) for r in records]
    expected=sum(x.rent_amount for x in summaries)
    collected=sum(x.verified_total for x in summaries)
    pending=sum(x.outstanding for x in summaries if not x.is_overdue)
    overdue=sum(x.outstanding for x in summaries if x.is_overdue)
    partial=sum(x.outstanding for x in summaries if x.status == "PARTIALLY_PAID")
    return {"records":records,"summaries":summaries,"expected":expected,"collected":collected,"pending":pending,"overdue":overdue,"partial":partial,"outstanding":pending+overdue,"collection_rate":(collected/expected*100 if expected else 0.0)}
