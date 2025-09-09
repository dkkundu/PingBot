import logging
from logging.handlers import TimedRotatingFileHandler
import os

LOGS_DIR = os.getenv('LOG_DIR_HOST', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)


if not os.path.exists(f'{LOGS_DIR}/app'):
    os.makedirs(f'{LOGS_DIR}/app')

if not os.path.exists(f'{LOGS_DIR}/celery'):
    os.makedirs(f'{LOGS_DIR}/celery')

if not os.path.exists(f'{LOGS_DIR}/bot'):
    os.makedirs(f'{LOGS_DIR}/bot')

if not os.path.exists(f'{LOGS_DIR}/alerts'):
    os.makedirs(f'{LOGS_DIR}/alerts')



def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup a single logger with daily rotation"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        os.path.join(LOGS_DIR, log_file),
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
flask_logger = setup_logger("FlaskApp", "app/app.log")
celery_logger = setup_logger("CeleryWorker", "celery/celery.log")
telegram_logger = setup_logger("TelegramBot", "bot/bot.log")
test_message_logger = setup_logger("TestMessages", "bot/text_bot.log")
scheduled_alerts_logger = setup_logger("ScheduledAlerts", "alerts/scheduled_alerts.log")
