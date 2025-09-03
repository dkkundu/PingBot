from app.celery_config import celery


# ---------------- BEAT SCHEDULE ----------------
celery.conf.beat_schedule = {
    "check_scheduled_alerts": {
        "task": "app.notification_sender.tasks.check_scheduled_alerts",
        "schedule": 60.0,  # Run every 60 seconds
    }
}
