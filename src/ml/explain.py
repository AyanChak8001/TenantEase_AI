def explain_prediction(features, probability):
    factors=[]
    if features.get("previous_late_payments",0)>2: factors.append("multiple previous late payments")
    if features.get("average_delay_days",0)>2: factors.append("higher average historical delay")
    if features.get("on_time_payment_rate",1)<.8: factors.append("lower on-time payment rate")
    if not factors: factors.append("consistent historical payment indicators")
    return f"Risk probability {probability:.1%}; indicators considered: " + ", ".join(factors) + ". Feature importance indicates association, not causation."
