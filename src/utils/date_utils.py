from calendar import monthrange
from datetime import date

def month_key(d: date) -> str: return d.strftime("%Y-%m")
def safe_due_date(year: int, month: int, due_day: int) -> date:
    return date(year, month, min(due_day, monthrange(year, month)[1]))
def next_month(d: date) -> date:
    return date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)
