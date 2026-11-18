from src.services.recommendation_service import recommendation

def test_recommendation_uses_status_and_risk():
    result={"category":"High","probability":.8}
    assert "overdue" in recommendation(result,3,4,"OVERDUE").lower()
    assert "elevated" in recommendation(result,3,4,"PENDING").lower()
