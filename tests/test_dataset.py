import pandas as pd
from src.data.generate_dataset import generate_dataset

def test_dataset_reproducible():
    a=generate_dataset(n_tenants=10,cycles=5); b=generate_dataset(n_tenants=10,cycles=5); pd.testing.assert_frame_equal(a,b)
def test_dataset_valid():
    d=generate_dataset(n_tenants=20,cycles=6); assert not d.isna().any().any(); assert not d.duplicated("rent_cycle_id").any(); assert set(d.late_payment)=={0,1}; assert (d.days_until_due==7).all()

def test_small_test_generation_preserves_canonical_artifact():
    generate_dataset(n_tenants=5,cycles=2)
    canonical=pd.read_csv("data/processed/model_dataset.csv")
    assert len(canonical)==5600
    assert canonical.tenant_id.nunique()==200
