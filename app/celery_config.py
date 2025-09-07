import os
from celery import Celery

# ---------------- INIT CELERY ----------------

using_redis_password = bool(int(os.getenv("USING_REDIS_PASSWORD")))

if using_redis_password:
    celery = Celery(
        "notification_app",
        broker=f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}",
        backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}"
    )
else:
    celery = Celery(
        "notification_app",
        broker=f"redis://:{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}",
        backend=f"redis://:{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}"
    )


# celery = Celery(a
#     "notification_app",
#     broker=os.getenv("CELERY_BROKER_URL"),
#     backend=os.getenv("CELERY_BACKEND_URL")
# )

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