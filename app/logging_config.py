import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup a single logger with its own file"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_file),
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
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
flask_logger = setup_logger("FlaskApp", "flask_app.log")
celery_logger = setup_logger("CeleryWorker", "celery_worker.log")
telegram_logger = setup_logger("TelegramBot", "telegram_bot.log")
test_message_logger = setup_logger("TestMessages", "test_messages.log")
scheduled_alerts_logger = setup_logger("ScheduledAlerts", "scheduled_alerts.log")
