import pandas as pd
from src.data.generate_dataset import FEATURES
from config.settings import DATA_PROCESSED_DIR

def load_dataset(path=DATA_PROCESSED_DIR/"model_dataset.csv"):
    return pd.read_csv(path, parse_dates=["due_date","payment_date"])

def validate_features(df):
    assert set(FEATURES).issubset(df.columns)
    assert not df[FEATURES].isna().any().any()
    assert (df.payment_date >= df.due_date).all()
    assert (df.days_until_due == 7).all(), "Features must be constructed seven days before due date"
    return True
