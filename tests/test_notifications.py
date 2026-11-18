from datetime import date, timedelta
from config.settings import REMINDER_OFFSET_DAYS
def test_business_reminder_date(): assert date(2025,12,1)-timedelta(days=REMINDER_OFFSET_DAYS)==date(2025,11,26)
