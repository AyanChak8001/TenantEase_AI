"""Create reproducible synthetic rent-cycle data; it contains no customer data."""
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd
from config.settings import DATA_RAW_DIR, DATA_PROCESSED_DIR, RANDOM_SEED
from src.utils.date_utils import safe_due_date

FEATURES = ["monthly_rent","tenancy_months","payment_method","previous_late_payments","average_delay_days","last_payment_delay","on_time_payment_rate","previous_payment_count","days_until_due"]

def generate_dataset(n_tenants=200, cycles=28, seed=RANDOM_SEED):
    rng=np.random.default_rng(seed); rows=[]
    methods=["UPI","BANK_TRANSFER","CARD","CASH"]
    profiles=rng.choice([0,1,2], size=n_tenants, p=[.55,.3,.15])
    for t in range(n_tenants):
        rent=float(rng.integers(15000,60001)//500*500); prop=t//20+1; unit=f"{t%20+1:02d}"
        delays=[]; start=date(2022,1,1)
        for c in range(cycles):
            y=2023+(c//12); m=c%12+1; due=safe_due_date(y,m,1)
            observed_delays=delays[-6:]
            prev_late=sum(x>0 for x in observed_delays); avg=float(np.mean(observed_delays)) if observed_delays else 0.0; last=float(observed_delays[-1]) if observed_delays else 0.0
            on_time=1-(prev_late/len(observed_delays) if observed_delays else 0); method=str(rng.choice(methods,p=[.45,.3,.15,.1]))
            base={0:-1.8,1:-.5,2:.8}[profiles[t]] + .08*prev_late + .04*avg + rng.normal(0,.45)
            late=bool(rng.random() < (1/(1+np.exp(-base))))
            delay=int(rng.choice([1,2,3,4,5,7,10,14], p=[.25,.2,.15,.12,.1,.08,.06,.04])) if late else int(rng.choice([0,0,0,0,1], p=[.55,.2,.12,.08,.05]))
            payment_date=due+timedelta(days=delay)
            rows.append({"tenant_id":f"T{t+1:03d}","property_id":f"P{prop:03d}","unit_id":unit,"rent_cycle_id":f"T{t+1:03d}-{y:04d}{m:02d}","monthly_rent":rent,"tenancy_months":c+1,"payment_method":method,"previous_late_payments":prev_late,"average_delay_days":avg,"last_payment_delay":last,"on_time_payment_rate":on_time,"previous_payment_count":len(observed_delays),"days_until_due":7,"due_date":due,"payment_date":payment_date,"late_payment":int(payment_date>due)})
            delays.append(delay)
    df=pd.DataFrame(rows)
    # Small datasets are used by unit tests and callers exploring the generator;
    # they must not overwrite the canonical project artifacts.
    if n_tenants == 200 and cycles == 28:
        raw=DATA_RAW_DIR/"synthetic_rent_payments.csv"; processed=DATA_PROCESSED_DIR/"model_dataset.csv"; df.to_csv(raw,index=False); df.to_csv(processed,index=False)
    validate_dataset(df); return df

def validate_dataset(df):
    assert not df.isna().any().any(); assert not df.duplicated("rent_cycle_id").any(); assert set(df.late_payment.unique())=={0,1}; assert (pd.to_datetime(df.payment_date)>=pd.to_datetime(df.due_date)).all()

if __name__ == "__main__": print(generate_dataset().describe(include="all").to_string())
