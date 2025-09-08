import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# ---------------- INIT CELERY ----------------

def str_to_bool(val: str) -> bool:
    return str(val).lower() in ("1", "true", "yes", "on")

using_redis_password = str_to_bool(os.getenv("USING_REDIS_PASSWORD", "false"))

if using_redis_password:
    celery = Celery(
        "notification_app",
        broker=f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}",
        backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}"
    )
else:
    celery = Celery(
    "notification_app",
    broker=f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}",
    backend=f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}"
)

    
    # celery = Celery(
    #     "notification_app",
    #     broker=f"redis://:{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}",
    #     backend=f"redis://:{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB')}"
    # )



# ---------------- CONFIGURE TIMEZONE ----------------
celery.conf.update(
    timezone=os.getenv("TZ", "UTC"),
    enable_utc=True,
    imports=('app.notification_sender.tasks',)
)

# ---------------- BEAT SCHEDULE ----------------
celery.conf.beat_schedule = {
    'check-scheduled-alerts-every-30-seconds': {
        'task': 'app.notification_sender.tasks.check_scheduled_alerts',
        'schedule': 30.0,
    },
}