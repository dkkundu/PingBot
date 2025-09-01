import os
import pytz
import re
from app.notification_sender.telegram_bot import TelegramBot
from app.notification_sender.models import AlertSample, AlertLog, AlertConfig
from app.authentication.models import User
from app.extensions import db
from datetime import datetime,timedelta
from app.celery_config import celery
from app.logging_config import celery_logger

# Initialize TelegramBot
telegram_bot = TelegramBot()

@celery.task(bind=True, max_retries=3)
def send_alert_task(self, sample_id, log_id=None):
    """
    Celery task to send an alert.

    Args:
        sample_id (int): The ID of the AlertSample to send.
        log_id (int, optional): The ID of the AlertLog to update.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        # Retrieve the sample and log from the database
        sample = AlertSample.query.get(sample_id)
        log = AlertLog.query.get(log_id) if log_id else (
            AlertLog.query.filter_by(sample_id=sample_id).order_by(AlertLog.queued_at.desc()).first()
        )

        # If sample is not found, log an error and update the log status
        if not sample:
            if log:
                log.status = "failed"
                log.error_message = "Sample not found"
                db.session.commit()
            celery_logger.error(f"Sample {sample_id} not found")
            return "Sample not found"

        try:
            # Retrieve user and config from the database
            user = User.query.get(sample.user_id) if sample.user_id else None
            config = AlertConfig.query.get(sample.config_id)

            # Construct the message
            # Remove <p> and </p> tags from sample.body
            cleaned_body = sample.body.replace('<p>', '').replace('</p>', '')
            celery_logger.info(f"Original cleaned_body: {cleaned_body}")
            celery_logger.info(f"sample.file_upload: {sample.file_upload}")

            # Remove any <img> tags from the message body, as Telegram's text messages
            # do not support embedded images (especially base64).
            cleaned_body = re.sub(r'<img[^>]+>', '', cleaned_body)
            celery_logger.info(f"cleaned_body after img tag removal: {cleaned_body}")

            # Get current time in LOCAL_TZ
            LOCAL_TZ = pytz.timezone("Asia/Dhaka") # Define LOCAL_TZ here
            now_local = datetime.now(LOCAL_TZ)
            formatted_time = now_local.strftime("%B %d, %Y at %I:%M %p")

            # Placeholder values for fields not directly available in AlertSample
            author = sample.sender_name if sample.sender_name else "N/A"
            status = "Unknown" # Or derive from sample.category if applicable

            message = f"""🔔 Alert

🕒 Time: {formatted_time}
📸 Author: {author}

----------------------------------------

📢 Message: {cleaned_body}"""

            celery_logger.info(f"Final message payload text: {message}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], sample.file_upload) if sample.file_upload else None

            response = None
            # Send the message if config and auth_token are available
            if config and config.auth_token:
                if user:
                    celery_logger.info(f"Sending individual message to {user.username}")
                    response = telegram_bot.individual_message(user.mobile_number, message, file_path=file_path)
                elif config.group_id:
                    if config.group_id == "None" or not config.group_id:
                        celery_logger.warning(f"Skipping group message for alert {sample.id}: group_id is not configured for {config.group_name}.")
                        response = {"error": "Group ID not configured"}
                    else:
                        celery_logger.info(f"Sending group message to {config.group_name}")
                        response = telegram_bot.group_message(config.auth_token, config.group_id, message, file_path=file_path)

            # Check the response from the Telegram API
            if response and "error" in response:
                raise Exception(response["error"])
            elif response and "status_code" in response and response["status_code"] != 200:
                raise Exception(f"API Error: {response['text']}")

            # Mark the alert as sent
            sample.sent_at = datetime.combine(sample.start_date, sample.start_time).replace(tzinfo=pytz.utc)
            if log:
                log.status = "sent"
                log.sent_at = sample.sent_at

            # Handle recurring alerts
            if sample.is_recurring and sample.recurrence_interval:
                next_send_datetime = datetime.combine(sample.start_date, sample.start_time).replace(tzinfo=pytz.utc)
                
                interval_str = sample.recurrence_interval.strip().lower()
                
                # Parse recurrence interval (e.g., "1d", "2h", "30m")
                match = re.match(r'(\d+)([dhms])', interval_str)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)
                    
                    if unit == 'd':
                        next_send_datetime += timedelta(days=value)
                    elif unit == 'h':
                        next_send_datetime += timedelta(hours=value)
                    elif unit == 'm':
                        next_send_datetime += timedelta(minutes=value)
                    elif unit == 's': # Although not in example, good to include
                        next_send_datetime += timedelta(seconds=value)
                else:
                    # Fallback for old 'daily', 'weekly', 'monthly' if still present
                    if interval_str == 'daily':
                        next_send_datetime += timedelta(days=1)
                    elif interval_str == 'weekly':
                        next_send_datetime += timedelta(weeks=1)
                    elif interval_str == 'monthly':
                        next_send_datetime += timedelta(days=30) # Approximation
                        
                # Update the sample for the next recurrence
                sample.start_date = next_send_datetime.date()
                sample.start_time = next_send_datetime.time()

            db.session.commit()
            celery_logger.info(f"Alert {sample.id} sent successfully.")
            return f"Alert {sample.id} sent"

        except Exception as exc:
            # If an error occurs, update the log and retry the task
            if log:
                log.status = "failed"
                log.error_message = str(exc)
                log.retry_count = (log.retry_count or 0) + 1
            db.session.commit()
            celery_logger.exception(f"Error sending alert {sample_id}: {exc}")
            raise self.retry(exc=exc, countdown=60)

@celery.task
def check_scheduled_alerts():
    """
    Celery task to check for scheduled alerts and send them.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        now = datetime.now(pytz.utc)
        # Get all alerts that are scheduled to be sent now or in the past
        # and are either not recurring OR are recurring and their current scheduled time has passed
        alerts_to_process = AlertSample.query.filter(
            (AlertSample.start_date <= now.date()) & (AlertSample.start_time <= now.time())
        ).all()

        for alert in alerts_to_process:
            # For non-recurring alerts, check if it has already been sent
            if not alert.is_recurring:
                log = AlertLog.query.filter_by(sample_id=alert.id, status="sent").first()
                if log:
                    continue # Skip if already sent and not recurring

            # For recurring alerts, we always send if their scheduled time has passed.
            # A new log entry will be created for each send.
            # The send_alert_task will update the AlertSample's next scheduled time.

            # Create a new log entry for each send attempt
            new_log = AlertLog(
                sample_id=alert.id,
                service_id=alert.service_id,
                config_id=alert.config_id,
                sender_id=alert.user_id, # Assuming user_id is sender_id for now
                company_name=alert.company_name,
                sender_name=alert.sender_name,
                audience="all", # Defaulting to all, adjust if needed
                status="queued",
                scheduled_for=datetime.combine(alert.start_date, alert.start_time).replace(tzinfo=pytz.utc)
            )
            db.session.add(new_log)
            db.session.commit() # Commit to get the log ID

            send_alert_task.delay(alert.id, log_id=new_log.id)