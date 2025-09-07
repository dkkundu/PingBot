import os
from celery import Celery

# ---------------- INIT CELERY ----------------
celery = Celery(
    "notification_app",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend=os.getenv("CELERY_BACKEND_URL")
)

# ---------------- CONFIGURE TIMEZONE ----------------
celery.conf.update(
    timezone=os.getenv("TZ", "UTC"),
    enable_utc=True
)

# ---------------- BEAT SCHEDULE ----------------
celery.conf.beat_schedule = {
    'check-scheduled-alerts-every-minute': {
        'task': 'app.notification_sender.tasks.check_scheduled_alerts',
        'schedule': 60.0,
    },
}