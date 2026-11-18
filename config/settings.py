from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODEL_DIR = ROOT_DIR / "models"
REPORT_DIR = ROOT_DIR / "reports"
LOG_DIR = ROOT_DIR / "logs"
DB_PATH = ROOT_DIR / "tenantease.db"
DATABASE_URL = os.getenv("TENANTEASE_DATABASE_URL", f"sqlite:///{DB_PATH}")
RANDOM_SEED = 42
DEFAULT_DUE_DAY = 1
REMINDER_OFFSET_DAYS = 5  # Business convention: Dec 1 reminder is Nov 26.
GRACE_PERIOD_DAYS = 3
OVERDUE_DAY = 5
MODEL_VERSION = "1.0.0"
APPLICATION_TIMEZONE = os.getenv("TENANTEASE_TIMEZONE", "Asia/Kolkata")
NOTIFICATION_POLL_SECONDS = 15
for _p in (DATA_RAW_DIR, DATA_PROCESSED_DIR, MODEL_DIR, REPORT_DIR, LOG_DIR):
    _p.mkdir(parents=True, exist_ok=True)
