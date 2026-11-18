from datetime import date
from database.models import PredictionLog
from src.ml.predict import predict
from src.ml.train import FEATURES
from config.settings import MODEL_VERSION

def predict_for_features(s, tenant_id, rent_record_id, features):
    result=predict(features); log=PredictionLog(tenant_id=tenant_id,rent_record_id=rent_record_id,risk_probability=result["probability"],risk_category=result["category"],model_version=MODEL_VERSION,prediction_date=date.today(),explanation=result["explanation"]); s.add(log); s.commit(); return result
