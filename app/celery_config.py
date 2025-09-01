from celery import Celery

# ---------------- INIT CELERY ----------------
celery = Celery(
    "notification_app",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# ---------------- CONFIGURE TIMEZONE ----------------
celery.conf.update(
    timezone='UTC',
    enable_utc=True
)
