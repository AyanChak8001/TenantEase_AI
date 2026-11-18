from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from database.models import NotificationLog, Tenant, RentRecord, Property
from config.settings import REMINDER_OFFSET_DAYS, OVERDUE_DAY
from src.services.financial_service import rent_financials

def _message(t,r,overdue=False,amount=None):
    amount = r.rent_amount if amount is None else amount
    if overdue: return f"Hello {t.tenant_name}, our records indicate that an outstanding rent balance of ₹{amount:,.0f}, due on {r.due_date:%d %b %Y}, has not yet been recorded. Please contact your property manager if you have already completed the payment."
    return f"Hello {t.tenant_name}, this is a friendly reminder that your monthly rent of ₹{r.rent_amount:,.0f} is due on {r.due_date:%d %b %Y}. Please ensure that your payment is completed on time. Thank you – TenantEase."

def run_notification_simulation(s, as_of, owner_id=None):
    created=[]
    records=s.query(RentRecord).join(Tenant, RentRecord.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id)
    if owner_id is not None: records=records.filter(Property.owner_id == owner_id)
    for r in records.all():
        t=s.get(Tenant,r.tenant_id)
        reminder=r.due_date-timedelta(days=REMINDER_OFFSET_DAYS)
        kind=None; scheduled=None; msg=None
        summary=rent_financials(s,r,as_of)
        if as_of>=reminder and as_of<r.due_date and summary.outstanding>0: kind="ADVANCE_REMINDER"; scheduled=datetime.combine(reminder,datetime.min.time()); msg=_message(t,r)
        if as_of>=r.due_date+timedelta(days=4) and summary.is_overdue: kind="OVERDUE_ALERT"; scheduled=datetime.combine(as_of,datetime.min.time()); msg=_message(t,r,True,summary.outstanding)
        if kind and not s.query(NotificationLog).filter_by(tenant_id=t.id,rent_record_id=r.id,notification_type=kind).first():
            n=NotificationLog(tenant_id=t.id,rent_record_id=r.id,notification_type=kind,recipient=t.email,message=msg,scheduled_at=scheduled,sent_at=datetime.now(),delivery_status="SENT_SIMULATED"); s.add(n); created.append(n)
    s.commit(); return created
