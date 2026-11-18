from src.ml.predict import risk_category
from src.ml.predict import predict
def test_thresholds(): assert risk_category(.29)=="Low"; assert risk_category(.30)=="Medium"; assert risk_category(.65)=="High"

def test_saved_model_prediction():
    result=predict({"monthly_rent":25000,"tenancy_months":10,"payment_method":"UPI","previous_late_payments":2,"average_delay_days":1.5,"last_payment_delay":2,"on_time_payment_rate":.8,"previous_payment_count":6,"days_until_due":7})
    assert 0 <= result["probability"] <= 1
    assert result["category"] in {"Low","Medium","High"}
