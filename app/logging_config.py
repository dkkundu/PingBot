import logging
from logging.handlers import TimedRotatingFileHandler
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup a single logger with daily rotation"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, log_file),
        when="midnight",     # rotate at midnight
        interval=1,          # every 1 day
        backupCount=7,       # keep last 7 days
        encoding="utf-8",
        utc=False            # change to True if you want UTC rotation
    )
    file_handler.suffix = "%Y-%m-%d"  # adds date to rotated files
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    ))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    ))

    # Avoid duplicate handlers on reload
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Initialize separate loggers
flask_logger = setup_logger("FlaskApp", "app.log")
celery_logger = setup_logger("CeleryWorker", "celery.log")
telegram_logger = setup_logger("TelegramBot", "bot.log")
test_message_logger = setup_logger("TestMessages", "text_bot.log")
scheduled_alerts_logger = setup_logger("ScheduledAlerts", "scheduled_alerts.log")
