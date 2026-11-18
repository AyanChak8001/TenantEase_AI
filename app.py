"""TenantEase AI Streamlit dashboard."""
from datetime import date
import json
import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import DATA_PROCESSED_DIR, MODEL_DIR, REPORT_DIR
from database.db import get_session, init_db
from database.models import NotificationLog, Owner, Payment, Property, RentRecord, Tenant
from database.seed import seed_demo
from src.data.generate_dataset import FEATURES
from src.ml.predict import predict
from src.services.notification_service import run_notification_simulation
from src.services.payment_service import record_payment, verify_payment
from src.services.recommendation_service import recommendation
from src.services.rent_service import generate_rent_records, refresh_statuses
from src.services.tenant_service import create_property, create_tenant, list_owned_properties, list_tenants, update_tenant
from src.services.auth_service import authenticate_owner, register_owner
from src.services.financial_service import owned_rents, portfolio_totals, rent_financials

st.set_page_config(page_title="TenantEase AI", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

def inject_styles():
    st.markdown("""
    <style>
    :root { --navy:#102D46; --secondary:#173F5F; --teal:#24B8A8; --bg:#F3F7FA; --text:#17324D; --muted:#647B90; --success:#15966E; --warning:#D99035; --danger:#DC5555; }
    .stApp { background:var(--bg); color:var(--text); }
    [data-testid="stSidebar"] { background:var(--navy); border-right:1px solid #244762; }
    [data-testid="stSidebar"] * { color:#F4FBFC !important; }
    [data-testid="stSidebar"] .stRadio > label { color:#B9D3DF !important; font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap:5px; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { border-radius:9px; padding:8px 10px; transition:background .15s ease; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background:#173F5F; }
    [data-testid="stSidebar"] .stButton button { border:1px solid #3F657E; background:#173F5F; color:#F4FBFC; border-radius:9px; }
    [data-testid="stSidebar"] .stButton button:hover { border-color:var(--teal); color:white; }
    .brand { padding:8px 0 20px; } .brand-mark { display:inline-flex; align-items:center; justify-content:center; width:38px; height:38px; margin-right:9px; border-radius:11px; background:var(--teal); color:var(--navy); font-weight:800; font-size:20px; box-shadow:0 5px 14px rgba(36,184,168,.2); }
    .brand-name { color:white; font-weight:750; font-size:21px; vertical-align:middle; } .brand-copy { color:#B9D3DF; font-size:12px; line-height:1.45; margin-top:9px; }
    .demo-pill { display:inline-block; padding:5px 9px; border:1px solid #5CD2C5; border-radius:999px; color:#DFF7F3; font-size:11px; font-weight:750; letter-spacing:.05em; }
    .page-kicker { color:#138A80; font-size:12px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; } .page-title { color:var(--text); font-size:32px; font-weight:760; margin:2px 0 3px; letter-spacing:-.02em; } .page-subtitle { color:var(--muted); margin-bottom:20px; font-size:15px; }
    .kpi { background:#FFFFFF; border:1px solid #E1EAF0; border-radius:15px; padding:16px 17px; min-height:122px; box-shadow:0 4px 16px rgba(23,50,77,.06); } .kpi-top { display:flex; align-items:center; justify-content:space-between; } .kpi-icon { width:30px; height:30px; display:flex; align-items:center; justify-content:center; border-radius:9px; background:#E5F7F4; font-size:16px; } .kpi-label { color:var(--muted); font-size:11px; font-weight:750; text-transform:uppercase; letter-spacing:.05em; } .kpi-value { color:var(--text); font-size:25px; font-weight:780; margin-top:12px; } .kpi-accent { height:3px; width:35px; background:var(--teal); border-radius:3px; margin-top:10px; }
    .empty { background:#F0FAF8; border:1px dashed #8ACFC6; border-radius:14px; padding:24px; color:#24565A; box-shadow:0 3px 12px rgba(23,50,77,.03); }
    .auth-shell { max-width:560px; margin:7vh auto 0; background:#FFFFFF; border:1px solid #E1EAF0; border-radius:18px; padding:34px 40px; box-shadow:0 12px 35px rgba(23,50,77,.10); }
    .auth-caption { color:var(--muted); font-size:14px; line-height:1.5; }
    div[data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E1EAF0; border-radius:14px; padding:12px 15px; box-shadow:0 3px 12px rgba(23,50,77,.04); }
    div[data-testid="stForm"] { border-color:#DDE8EE; border-radius:13px; background:#FFFFFF; }
    .stButton button[kind="primary"], button[data-testid="baseButton-primary"] { background:var(--teal); border-color:var(--teal); color:#FFFFFF; border-radius:9px; font-weight:700; }
    .stButton button[kind="primary"]:hover, button[data-testid="baseButton-primary"]:hover { background:#159C8E; border-color:#159C8E; }
    [data-testid="stDataFrame"] { border:1px solid #E1EAF0; border-radius:12px; overflow:hidden; }
    </style>
    """, unsafe_allow_html=True)

def money(value): return f"₹{value:,.0f}"
def header(kicker,title,subtitle): st.markdown(f'<div class="page-kicker">{kicker}</div><div class="page-title">{title}</div><div class="page-subtitle">{subtitle}</div>',unsafe_allow_html=True)
def kpi(label,value,icon="◈"): st.markdown(f'<div class="kpi"><div class="kpi-top"><div class="kpi-label">{label}</div><div class="kpi-icon">{icon}</div></div><div class="kpi-value">{value}</div><div class="kpi-accent"></div></div>',unsafe_allow_html=True)
def show_empty(message,detail): st.markdown(f'<div class="empty"><strong>✦ &nbsp;{message}</strong><br><span>{detail}</span></div>',unsafe_allow_html=True)
def tenant_name(s,tenant_id):
    t=s.get(Tenant,tenant_id); return t.tenant_name if t else f"Tenant #{tenant_id}"
def property_name(s,property_id):
    p=s.get(Property,property_id); return p.property_name if p else f"Property #{property_id}"
def rent_rows(s,records,as_of):
    rows=[]
    for r in records:
        summary=rent_financials(s,r,as_of)
        rows.append({"ID":r.id,"Tenant":tenant_name(s,r.tenant_id),"Month":r.rent_month,"Due date":r.due_date,"Rent amount":money(summary.rent_amount),"Verified received":money(summary.verified_total),"Remaining balance":money(summary.outstanding),"Status":summary.status,"Overpayment":money(summary.overpayment) if summary.overpayment else "-"})
    return rows

def owned_rent_records(s, owner_id):
    return owned_rents(s,owner_id)

def owned_payments(s, owner_id):
    return s.query(Payment).join(RentRecord, Payment.rent_record_id == RentRecord.id).join(Tenant, RentRecord.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id).filter(Property.owner_id == owner_id).order_by(Payment.created_at.desc()).all()

def owned_notifications(s, owner_id):
    return s.query(NotificationLog).join(Tenant, NotificationLog.tenant_id == Tenant.id).join(Property, Tenant.property_id == Property.id).filter(Property.owner_id == owner_id).order_by(NotificationLog.created_at.desc()).all()

def portfolio_risk_rows(s, owner_id):
    """Score real tenants only after at least two verified payment cycles."""
    if not (MODEL_DIR / "rent_risk_model.pkl").exists(): return [], 0
    rows, insufficient = [], 0
    for tenant in list_tenants(s, owner_id):
        rent_records=s.query(RentRecord).filter_by(tenant_id=tenant.id).order_by(RentRecord.due_date).all()
        verified=[]
        for rent in rent_records:
            payment=s.query(Payment).filter_by(rent_record_id=rent.id,verification_status="VERIFIED").first()
            if payment: verified.append((rent,payment))
        if len(verified)<2:
            insufficient += 1; continue
        delays=[(payment.payment_date-rent.due_date).days for rent,payment in verified]
        features={"monthly_rent":tenant.monthly_rent,"tenancy_months":max(1,(date.today().year-tenant.lease_start_date.year)*12+date.today().month-tenant.lease_start_date.month),"payment_method":verified[-1][1].payment_method,"previous_late_payments":sum(delay>0 for delay in delays),"average_delay_days":sum(max(0,delay) for delay in delays)/len(delays),"last_payment_delay":max(0,delays[-1]),"on_time_payment_rate":sum(delay<=0 for delay in delays)/len(delays),"previous_payment_count":len(delays),"days_until_due":7}
        result=predict(features); actual=rent_records[-1].status if rent_records else "NO_RENT_RECORD"
        rows.append({"Tenant":tenant.tenant_name,"Tenant ID":tenant.id,"Probability":result["probability"],"Risk":result["category"],"Prior late":features["previous_late_payments"],"Avg delay":features["average_delay_days"],"On-time rate":features["on_time_payment_rate"],"Actual status":actual,"Explanation":result["explanation"],"Recommendation":recommendation(result,features["previous_late_payments"],features["average_delay_days"],actual)})
    return rows, insufficient

def auth_screen(s):
    _, center, _ = st.columns([1, 1.35, 1])
    with center:
        st.markdown('<div class="auth-shell"><div class="brand"><span class="brand-mark">T</span><span class="brand-name">TenantEase AI</span></div><h2>Owner workspace</h2><div class="auth-caption">Manage your properties, rent cycles and payment intelligence from one secure workspace.</div></div>',unsafe_allow_html=True)
    _, form, _ = st.columns([1, 1.35, 1])
    with form:
        mode=st.radio("Account",["Sign in","Register"],horizontal=True)
    if mode=="Sign in":
        with form:
            with st.form("owner_login_form"):
                email=st.text_input("Email",placeholder="owner@example.com"); password=st.text_input("Password",type="password"); submit=st.form_submit_button("Sign in",type="primary",use_container_width=True)
                if submit:
                    owner=authenticate_owner(s,email,password)
                    if owner:
                        st.session_state.owner_id=owner.id; st.session_state.owner_name=owner.full_name; st.rerun()
                    else: st.error("Email or password is incorrect.")
            st.info("Demo account: demo.owner@example.test / DemoOwner123!")
    else:
        with form:
            with st.form("owner_register_form"):
                name=st.text_input("Full name"); email=st.text_input("Email"); password=st.text_input("Password",type="password",help="Use at least 10 characters."); confirm=st.text_input("Confirm password",type="password"); submit=st.form_submit_button("Create owner account",type="primary",use_container_width=True)
                if submit:
                    if password != confirm: st.error("Passwords do not match.")
                    else:
                        try: owner=register_owner(s,name,email,password); st.session_state.owner_id=owner.id; st.session_state.owner_name=owner.full_name; st.success("Account created."); st.rerun()
                        except ValueError as error: st.error(str(error))

def logout_owner():
    st.session_state.pop("owner_id",None)
    st.session_state.pop("owner_name",None)

def is_authenticated():
    return bool(st.session_state.get("owner_id"))

def sidebar(s,demo,owner):
    st.sidebar.markdown('<div class="brand"><span class="brand-mark">T</span><span class="brand-name">TenantEase</span><div class="brand-copy">AI-powered rent collection and payment intelligence for modern property teams.</div></div>',unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='color:#dff7f3;margin:8px 0 12px'>Signed in as <strong>{owner.full_name}</strong></div>",unsafe_allow_html=True)
    st.sidebar.markdown('<span class="demo-pill">● DEMO MODE</span>',unsafe_allow_html=True); st.sidebar.caption("The simulation clock affects status evaluation only. Historical timestamps remain unchanged.")
    selected=st.sidebar.date_input("Simulated current date",value=demo,key="demo_date_picker")
    st.sidebar.markdown("### Workspace"); page=st.sidebar.radio("Navigation",["Dashboard","Tenants","Rent & Payments","Notifications","AI Risk Intelligence","Analytics"],label_visibility="collapsed")
    st.sidebar.markdown("### Demo controls")
    if st.sidebar.button("Log out",use_container_width=True):
        logout_owner(); st.rerun()
    if st.sidebar.button("Initialize demo data",use_container_width=True): seed_demo(); st.sidebar.success("Synthetic demo tenants are ready.")
    if st.sidebar.button("Generate selected month rent",use_container_width=True):
        created=generate_rent_records(s,selected,owner.id); refresh_statuses(s,selected,owner.id); st.sidebar.success(f"{len(created)} new rent record(s); duplicates skipped."); st.rerun()
    with st.sidebar.expander("Demo workflow"): st.markdown("**Nov 25** upcoming · **Nov 26** reminder · **Dec 1** due · **Dec 3** grace · **Dec 5** overdue")
    return page,selected

def dashboard(s,demo,owner_id,owner_name):
    first_name=(owner_name or "Owner").strip().split()[0]
    header("Portfolio overview",f"Hello, {first_name}!",f"Here's what's happening with your properties today. Simulated date: {demo:%d %B %Y}.")
    financial=portfolio_totals(s,owner_id,demo); records=financial["records"]; tenants=len(list_tenants(s,owner_id))
    if not records: show_empty("Your portfolio is ready for its first rent cycle","Generate selected month rent from the sidebar to activate collection metrics, reminders and payment workflows."); return
    expected=financial["expected"]; collected=financial["collected"]; pending=financial["pending"]; overdue=financial["overdue"]
    cols=st.columns(6)
    for col,label,value,icon in zip(cols,["Active tenants","Expected rent","Collected","Outstanding pending","Outstanding overdue","Collection rate"],[tenants,money(expected),money(collected),money(pending),money(overdue),f"{financial['collection_rate']:.1f}%"],["♙","◫","✓","◷","!","%"]):
        with col: kpi(label,value,icon)
    st.write(""); left,right=st.columns([1.35,1])
    with left:
        st.markdown("#### Collection trend"); trend=pd.DataFrame([{"Month":r.rent_month,"Expected":summary.rent_amount,"Collected":summary.verified_total} for r,summary in zip(records,financial["summaries"])]).groupby("Month",as_index=False).sum().sort_values("Month")
        fig=px.bar(trend,x="Month",y=["Expected","Collected"],barmode="group",color_discrete_sequence=["#B8D9D6","#24B8A8"],labels={"value":"Amount (₹)","variable":""}); fig.update_layout(template="plotly_white",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#17324D",height=320,margin=dict(l=10,r=10,t=20,b=10),legend_title_text=""); st.plotly_chart(fig,use_container_width=True)
    with right:
        st.markdown("#### Payment status"); status_df=pd.DataFrame([{"Status":summary.status,"Count":1} for summary in financial["summaries"]]).groupby("Status",as_index=False).sum(); fig=px.pie(status_df,names="Status",values="Count",hole=.62,color="Status",color_discrete_map={"PAID":"#15966E","PARTIALLY_PAID":"#D99035","PENDING":"#D99035","OVERDUE":"#DC5555","UPCOMING":"#94A3B8"}); fig.update_layout(template="plotly_white",paper_bgcolor="rgba(0,0,0,0)",font_color="#17324D",height=320,margin=dict(l=10,r=10,t=20,b=10)); st.plotly_chart(fig,use_container_width=True)
    if (MODEL_DIR / "rent_risk_model.pkl").exists():
        portfolio_rows, insufficient = portfolio_risk_rows(s, owner_id)
        risk_rows = [{"Tenant": row["Tenant"], "Risk probability": f"{row['Probability']:.1%}", "Prior late payments": row["Prior late"], "Average delay": f"{row['Avg delay']:.1f} days"} for row in portfolio_rows if row["Risk"] == "High"]
        st.markdown("#### High-risk tenant summary")
        if risk_rows: st.dataframe(pd.DataFrame(risk_rows).sort_values("Risk probability", ascending=False), hide_index=True, use_container_width=True)
        elif insufficient: show_empty("More payment history is needed for risk scoring", f"{insufficient} active tenant(s) need at least two verified payment cycles before a prediction is shown.")
        else: show_empty("No high-risk predictions", "Continue standard reminders and monitor the AI Risk Intelligence page.")
    low,high=st.columns([1.3,1])
    with low:
        st.markdown("#### Priority overdue tenants"); rows=[{"Tenant":tenant_name(s,r.tenant_id),"Due":r.due_date,"Outstanding":money(summary.outstanding),"Days past due":max(0,(demo-r.due_date).days),"Status":summary.status} for r,summary in zip(records,financial["summaries"]) if summary.is_overdue]
        if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        else: show_empty("No active overdue rent","Verified payments and grace-period records are excluded from the priority queue.")
    with high:
        st.markdown("#### Recent payment activity"); payments=owned_payments(s,owner_id)[:6]; rows=[]
        for p in payments:
            r=s.get(RentRecord,p.rent_record_id); icon={"VERIFIED":"🟢","PENDING":"🟠","FAILED":"🔴"}.get(p.verification_status,"⚪"); rows.append({"Tenant":tenant_name(s,r.tenant_id),"Amount":money(p.amount),"Date":p.payment_date,"Status":f"{icon} {p.verification_status}"})
        if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        else: show_empty("No payments recorded yet","Payment activity will appear here after a payment is recorded.")

def tenants_page(s,owner_id,demo):
    header("Portfolio","Tenant management","Search tenants, review their current cycle and manage portfolio details."); tenants=list_tenants(s,owner_id); query=st.text_input("Search tenants",placeholder="Search by name, email or unit")
    if query: tenants=[t for t in tenants if query.lower() in f"{t.tenant_name} {t.email} {t.unit_id}".lower()]
    records=owned_rent_records(s,owner_id); display=[]
    for t in tenants:
        current=next((r for r in records if r.tenant_id==t.id),None); display.append({"ID":t.id,"Tenant":t.tenant_name,"Property":property_name(s,t.property_id),"Unit":t.unit_id,"Monthly rent":money(t.monthly_rent),"Due day":t.due_day,"Current status":current.status if current else "No rent generated"})
    st.dataframe(pd.DataFrame(display),hide_index=True,use_container_width=True)
    with st.expander("Add property"):
        with st.form("add_property_form"):
            property_name_input=st.text_input("Property name"); address=st.text_input("Address","Synthetic Avenue"); units=st.number_input("Total units",1,10000,10); property_submitted=st.form_submit_button("Create property")
            if property_submitted:
                if not property_name_input.strip() or not address.strip(): st.error("Property name and address are required.")
                else: create_property(s,property_name_input.strip(),address.strip(),int(units),owner_id); st.success("Property created."); st.rerun()
    with st.expander("Add tenant"):
        props=list_owned_properties(s,owner_id)
        with st.form("add_tenant_form"):
            name=st.text_input("Full name"); email=st.text_input("Email"); phone=st.text_input("Phone","+91-90000-0000"); unit=st.text_input("Unit","B-01"); rent=st.number_input("Monthly rent",1000.0,200000.0,20000.0,500.0); due=st.number_input("Due day",1,28,1); prop=st.selectbox("Property",props,format_func=lambda p:p.property_name,disabled=not props); submitted=st.form_submit_button("Create tenant")
            if submitted:
                if not name.strip() or "@" not in email or not unit.strip(): st.error("Enter a name, valid email and unit.")
                elif not props: st.error("Create a property before adding a tenant.")
                else: create_tenant(s,name.strip(),email.strip(),phone.strip(),prop.id,unit.strip(),rent,int(due),owner_id); st.success("Tenant created."); st.rerun()
    if tenants:
        selected=st.selectbox("Tenant detail",tenants,format_func=lambda t:f"{t.tenant_name} · Unit {t.unit_id}"); detail,history=st.columns([1,1.4])
        with detail:
            st.markdown("#### Tenant profile"); st.write(f"**{selected.tenant_name}**\n\n{selected.email}\n\n{selected.phone}")
            with st.form("edit_tenant_form"):
                rent=st.number_input("Monthly rent",1000.0,200000.0,float(selected.monthly_rent),500.0); due=st.number_input("Due day",1,28,int(selected.due_day)); save=st.form_submit_button("Save changes")
                if save: update_tenant(s,selected.id,owner_id=owner_id,monthly_rent=rent,due_day=int(due)); st.success("Tenant updated."); st.rerun()
        with history:
            st.markdown("#### Payment history"); rs=s.query(RentRecord).filter_by(tenant_id=selected.id).order_by(RentRecord.due_date.desc()).all()
            if rs: st.dataframe(pd.DataFrame(rent_rows(s,rs,demo)),hide_index=True,use_container_width=True)
            else: show_empty("No rent history","Generate a monthly rent cycle to begin tracking this tenant.")

def rent_page(s,demo,owner_id):
    header("Collections","Rent & payments","Generate obligations, monitor the collection queue and verify received payments.")
    if st.button("Generate selected month rent",type="primary"):
        created=generate_rent_records(s,demo,owner_id); refresh_statuses(s,demo,owner_id); st.success(f"{len(created)} new rent record(s) generated. Existing tenant-month records were skipped."); st.rerun()
    records=owned_rent_records(s,owner_id); tabs=st.tabs(["All","Upcoming","Pending","Partially paid","Overdue","Paid"])
    for tab,status in zip(tabs,[None,"UPCOMING","PENDING","PARTIALLY_PAID","OVERDUE","PAID"]):
        with tab:
            chosen=[r for r in records if status is None or r.status==status]
            if chosen: st.dataframe(pd.DataFrame(rent_rows(s,chosen,demo)),hide_index=True,use_container_width=True)
            else: show_empty(f"No {status.lower() if status else 'rent'} records","This queue will update as the simulated date and payment verification status change.")
    st.markdown("#### Record and verify a payment"); choices=[r for r in records if r.status!="PAID"]
    if choices:
        with st.form("payment_form"):
            selected=st.selectbox("Rent obligation",choices,format_func=lambda r:f"{tenant_name(s,r.tenant_id)} · {r.rent_month} · {money(r.rent_amount)}"); amount=st.number_input("Amount received",0.0,float(selected.rent_amount),500.0); method=st.selectbox("Payment method",["UPI","BANK_TRANSFER","CARD","CASH"]); ref=st.text_input("Transaction reference",f"DEMO-{selected.id}-{demo.isoformat()}"); paid_on=st.date_input("Payment date",demo); submit=st.form_submit_button("Record payment")
            if submit:
                if amount<=0 or not ref.strip(): st.error("Amount and transaction reference are required.")
                else: record_payment(s,selected.id,amount,paid_on,method,ref.strip(),owner_id); st.success("Payment recorded as pending verification."); st.rerun()
    rent_ids={r.id for r in records}; pending=[p for p in owned_payments(s,owner_id) if p.rent_record_id in rent_ids and p.verification_status=="PENDING"]
    if pending:
        st.markdown("#### Verification queue")
        for payment in pending:
            rent=s.get(RentRecord,payment.rent_record_id)
            if st.button(f"Verify {tenant_name(s,rent.tenant_id)} · {money(payment.amount)} · {payment.transaction_reference}",key=f"verify_{payment.id}"): verify_payment(s,payment.id,owner_id); st.success("Payment verified; rent marked PAID."); st.rerun()

def notifications_page(s,demo,owner_id):
    header("Communications","Notification center","Simulate owner-approved reminders and keep an auditable delivery history."); before=len(owned_notifications(s,owner_id))
    if st.button("Run notification simulation",type="primary"):
        created=run_notification_simulation(s,demo,owner_id)
        if created: st.success(f"{len(created)} notification(s) simulated.")
        else: st.info("No new notifications were required. Duplicate alerts were prevented.")
    logs=owned_notifications(s,owner_id)
    if not logs: show_empty("No notification activity yet","Run the simulation on November 26 or after an unpaid obligation reaches its overdue date."); return
    filters=st.multiselect("Filter notification types",["ADVANCE_REMINDER","PAYMENT_DUE","OVERDUE_ALERT"])
    if filters: logs=[n for n in logs if n.notification_type in filters]
    st.dataframe(pd.DataFrame([{"Tenant":tenant_name(s,n.tenant_id),"Type":n.notification_type,"Message":n.message,"Scheduled":n.scheduled_at,"Simulated sent":n.sent_at,"Delivery":n.delivery_status} for n in logs]),hide_index=True,use_container_width=True)

def risk_page(s,owner_id):
    header("Decision support","AI risk intelligence","Prioritize respectful follow-up using historical signals—not confirmed defaults.")
    if not (MODEL_DIR/"rent_risk_model.pkl").exists(): show_empty("Risk model is not trained","Run dataset generation and model training first."); return
    st.info("Predicted late-payment risk is separate from actual overdue status. Explanations show associations, not causation.")
    rows, insufficient = portfolio_risk_rows(s,owner_id)
    if not rows:
        show_empty("No tenant risk scores available yet", f"{insufficient} active tenant(s) need at least two verified payment cycles. Predictions are never invented from missing history.")
        return
    scored=pd.DataFrame(rows); left,right=st.columns([1,2]);
    with left:
        dist=scored.groupby("Risk",as_index=False).size().rename(columns={"size":"Tenants"}); fig=px.pie(dist,names="Risk",values="Tenants",hole=.6,color="Risk",color_discrete_map={"Low":"#15966E","Medium":"#D99035","High":"#DC5555"}); fig.update_layout(template="plotly_white",paper_bgcolor="rgba(0,0,0,0)",font_color="#17324D",height=300,margin=dict(l=5,r=5,t=5,b=5)); st.plotly_chart(fig,use_container_width=True)
    with right: st.metric("High-risk tenants",int((scored.Risk=="High").sum())); st.metric("Average predicted probability",f"{scored.Probability.mean():.1%}"); st.caption("Prototype thresholds: Low <30%, Medium 30–65%, High ≥65%.")
    st.dataframe(scored.sort_values("Probability",ascending=False),hide_index=True,use_container_width=True)

def analytics_page(s,owner_id,demo):
    header("Insights","Analytics","Understand collection performance, payment behavior and model quality in one place."); financial=portfolio_totals(s,owner_id,demo); records=financial["records"]
    if not records: show_empty("Analytics will appear after rent generation","Generate a rent cycle from the sidebar to populate portfolio charts."); return
    df=pd.DataFrame([{"Month":r.rent_month,"Status":summary.status,"Amount":summary.rent_amount,"Collected":summary.verified_total} for r,summary in zip(records,financial["summaries"])]); paid=df.groupby("Month",as_index=False).agg(Expected=("Amount","sum"),Collected=("Collected","sum")); paid["Collection %"]=paid.Collected/paid.Expected*100; a,b=st.columns(2)
    with a:
        fig=px.line(paid,x="Month",y="Collection %",markers=True,color_discrete_sequence=["#24B8A8"]); fig.update_layout(template="plotly_white",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#17324D",yaxis_title="Collection percentage"); st.plotly_chart(fig,use_container_width=True)
    with b:
        fig=px.bar(df.groupby("Status",as_index=False).agg(Amount=("Amount","sum")),x="Status",y="Amount",color="Status",color_discrete_map={"PAID":"#15966E","PARTIALLY_PAID":"#D99035","PENDING":"#D99035","OVERDUE":"#DC5555","UPCOMING":"#94A3B8"}); fig.update_layout(template="plotly_white",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#17324D"); st.plotly_chart(fig,use_container_width=True)
    payments=owned_payments(s,owner_id); delays=[]
    for payment in payments:
        rent=s.get(RentRecord,payment.rent_record_id); delays.append((payment.payment_date-rent.due_date).days)
    st.metric("Average payment delay",f"{sum(delays)/len(delays):.1f} days" if delays else "—")
    report=REPORT_DIR/"evaluation_results.json"
    if report.exists():
        st.markdown("#### Model evaluation")
        st.json(json.loads(report.read_text(encoding="utf-8")))

def main():
    inject_styles(); init_db(); seed_demo(); s=get_session()
    try:
        if not is_authenticated():
            auth_screen(s)
            return
        owner=s.get(Owner,st.session_state.owner_id)
        if not owner or not owner.is_active:
            st.session_state.pop("owner_id",None); st.session_state.pop("owner_name",None); st.rerun()
        if "demo_date" not in st.session_state: st.session_state.demo_date=date.today()
        page,demo=sidebar(s,st.session_state.demo_date,owner); st.session_state.demo_date=demo; refresh_statuses(s,demo,owner.id)
        if page=="Dashboard": dashboard(s,demo,owner.id,st.session_state.get("owner_name",owner.full_name))
        elif page=="Tenants": tenants_page(s,owner.id,demo)
        elif page=="Rent & Payments": rent_page(s,demo,owner.id)
        elif page=="Notifications": notifications_page(s,demo,owner.id)
        elif page=="AI Risk Intelligence": risk_page(s,owner.id)
        else: analytics_page(s,owner.id,demo)
    finally: s.close()

if __name__ == "__main__": main()
