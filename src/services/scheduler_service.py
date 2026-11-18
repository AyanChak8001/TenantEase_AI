"""Process scheduled notification delivery in one application worker."""

import atexit
import threading
from datetime import timedelta

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only in offline environments
    APSCHEDULER_AVAILABLE = False

    class BackgroundScheduler:
        """Small compatibility worker used only when APScheduler is unavailable."""
        def __init__(self, timezone=None):
            self._stop = threading.Event()
            self._thread = None
            self.running = False

        def add_job(self, function, trigger, seconds, **kwargs):
            self._function = function
            self._seconds = seconds

        def start(self):
            self.running = True
            self._thread = threading.Thread(target=self._run, name="tenantease-notification-worker", daemon=True)
            self._thread.start()

        def _run(self):
            while not self._stop.wait(self._seconds):
                self._function()

        def shutdown(self, wait=False):
            self._stop.set()
            self.running = False
            if wait and self._thread:
                self._thread.join(timeout=2)

from config.settings import APPLICATION_TIMEZONE, NOTIFICATION_POLL_SECONDS
from database.db import get_session
from src.services.notification_service import ensure_scheduled_business_notifications, local_now, process_due_notifications

_scheduler = None
_lock = threading.Lock()


def _notification_job():
    session = get_session()
    try:
        now = local_now()
        ensure_scheduled_business_notifications(session, now)
        process_due_notifications(session, now)
    finally:
        session.close()


def start_scheduler():
    """Start the singleton background scheduler, returning the scheduler."""
    global _scheduler
    with _lock:
        if _scheduler is not None and _scheduler.running:
            return _scheduler
        _scheduler = BackgroundScheduler(timezone=APPLICATION_TIMEZONE)
        _scheduler.add_job(
            _notification_job,
            "interval",
            seconds=NOTIFICATION_POLL_SECONDS,
            id="tenantease-notification-worker",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )
        _scheduler.start()
        return _scheduler


def stop_scheduler():
    global _scheduler
    with _lock:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=False)
        _scheduler = None


atexit.register(stop_scheduler)
