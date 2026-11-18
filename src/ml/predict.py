from pathlib import Path
import joblib
import pandas as pd
from config.settings import MODEL_DIR
from src.data.generate_dataset import FEATURES
from src.ml.explain import explain_prediction

def risk_category(p): return "Low" if p<.30 else "Medium" if p<.65 else "High"
def predict(features, model_path=MODEL_DIR/"rent_risk_model.pkl"):
    missing=[feature for feature in FEATURES if feature not in features]
    if missing: raise ValueError(f"Missing prediction features: {', '.join(missing)}")
    row={feature: features[feature] for feature in FEATURES}
    model=joblib.load(model_path)
    p=float(model.predict_proba(pd.DataFrame([row], columns=FEATURES))[0,1])
    p=max(0.0,min(1.0,p))
    return {"probability":p,"category":risk_category(p),"explanation":explain_prediction(row,p)}
