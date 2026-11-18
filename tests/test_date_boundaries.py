from datetime import date
from src.utils.date_utils import safe_due_date

def test_month_boundaries():
    assert safe_due_date(2024,2,31)==date(2024,2,29)
    assert safe_due_date(2025,2,31)==date(2025,2,28)
    assert safe_due_date(2025,12,31)==date(2025,12,31)
