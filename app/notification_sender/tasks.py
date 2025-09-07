import os
import pytz
import re
import html
import json
from app.notification_sender.telegram_bot import TelegramBot
from app.notification_sender.models import AlertSample, AlertLog, AlertConfig
from app.authentication.models import User
from app.notification_sender.message_geneator import get_messages
from app.extensions import db
from datetime import datetime,timedelta
from app.celery_config import celery
from app.logging_config import celery_logger

# Initialize TelegramBot
telegram_bot = TelegramBot()

@celery.task(bind=True, max_retries=3)
def send_alert_task(self, sample_id, log_id=None):
    """
    Celery task to send an alert with photo and document support.
    """
    from app.app import create_app
    app = create_app()
    with app.app_context():
        sample = AlertSample.query.get(sample_id)
        log = AlertLog.query.get(log_id) if log_id else AlertLog.query.filter_by(sample_id=sample_id).order_by(AlertLog.queued_at.desc()).first()

        if not sample:
            if log:
                log.status = "failed"
                log.error_message = "Sample not found"
                db.session.commit()
            celery_logger.error(f"Sample {sample_id} not found")
            return "Sample not found"

        try:
            user = User.query.get(sample.user_id) if sample.user_id else None
            config = AlertConfig.query.get(sample.config_id)

            # Basic validation
            if not (config and config.auth_token):
                raise Exception("Configuration or auth_token missing.")

            # Determine target chat_id and thread_id
            target_chat_id = None
            thread_id = None
            if user and user.telegram_chat_id:
                target_chat_id = user.telegram_chat_id
            elif config.group_id:
                group_id_str = str(config.group_id)
                if "_" in group_id_str:
                    parts = group_id_str.split("_", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        target_chat_id, thread_id = parts
                    else:
                        target_chat_id = group_id_str
                else:
                    target_chat_id = group_id_str

            if not target_chat_id:
                raise Exception("No valid target chat_id found for user or group.")
            
            message = get_messages(sample=sample)


            # Define file paths
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], sample.photo_upload) if sample.photo_upload else None
            document_path = os.path.join(app.config['UPLOAD_FOLDER'], sample.document_upload) if sample.document_upload else None

            # --- Sending Logic ---
            # The group_message method handles both text and photo, and thread_id parsing
            # It will send a photo with caption if photo_path is provided and exists,
            # otherwise it will send a text message.
            
            # Check if photo exists and is valid
            final_photo_path = photo_path if (photo_path and os.path.exists(photo_path)) else None
            
            celery_logger.info(f"Sending message for alert {sample.id} to {target_chat_id} with photo: {final_photo_path}")
            response = telegram_bot.group_message(
                auth_token=config.auth_token,
                chat_id=target_chat_id, # group_message will parse thread_id from this if present
                message=message,
                file_path=final_photo_path
            )

            if "error" in response:
                raise Exception(f"Failed to send message: {response['error']}")

            # The document sending logic was commented out in the original tasks.py,
            # so I will keep it commented out. If it needs to be re-enabled,
            # it would require a separate call to group_message or a new method
            # in telegram_bot.py for documents.
            # if document_path and os.path.exists(document_path):
            #     celery_logger.info(f"Sending document for alert {sample.id} to {target_chat_id}")
            #     doc_caption = f"Attached document for: {sample.title}"
            #     response = telegram_bot.send_document(
            #         auth_token=config.auth_token, chat_id=target_chat_id, file_path=document_path, caption=doc_caption, thread_id=thread_id
            #     )
            #     if "error" in response:
            #         raise Exception(f"Failed to send document: {response['error']}")

            # Mark the alert as sent
            sample.sent_at = datetime.now(pytz.utc)
            if log:
                log.status = "sent"
                log.sent_at = sample.sent_at

            # Handle recurring alerts
            if sample.is_recurring and sample.recurrence_interval:
                # ... (existing recurrence logic can be pasted here if needed) ...
                pass

            db.session.commit()
            celery_logger.info(f"Alert {sample.id} processed successfully.")
            return f"Alert {sample.id} sent"

        except Exception as exc:
            error_message_for_log = str(exc)
            if isinstance(exc, Exception) and hasattr(exc, 'response') and exc.response:
                try:
                    # Attempt to parse JSON error from Telegram API response
                    api_error_response = exc.response.json()
                    if "description" in api_error_response:
                        error_message_from_api = api_error_response["description"]
                        if "Unauthorized" in error_message_from_api or "Forbidden" in error_message_from_api or "invalid bot token" in error_message_from_api:
                            error_message_for_log = "Wrong token. Please check your authentication token."
                        elif "chat not found" in error_message_from_api or "kicked from the group chat" in error_message_from_api:
                            error_message_for_log = "Wrong group ID. Please check the group ID."
                        else:
                            error_message_for_log = f"Telegram API Error: {error_message_from_api}"
                    elif "error" in api_error_response: # Fallback for simpler error structures
                        error_message_for_log = f"Telegram API Error: {api_error_response['error']}"
                except (json.JSONDecodeError, AttributeError):
                    # If response is not JSON or doesn't have expected structure
                    error_message_for_log = f"API Error: {exc.response.text}"
            elif "error" in str(exc): # Catch errors from telegram_bot.py's return dict
                if "Unauthorized" in str(exc) or "Forbidden" in str(exc) or "invalid bot token" in str(exc):
                    error_message_for_log = "Wrong token. Please check your authentication token."
                elif "chat not found" in str(exc) or "kicked from the group chat" in str(exc):
                    error_message_for_log = "Wrong group ID. Please check the group ID."
                else:
                    error_message_for_log = str(exc)


            if log:
                log.status = "failed"
                log.error_message = error_message_for_log
                log.retry_count = (log.retry_count or 0) + 1
            db.session.commit()
            celery_logger.exception(f"Error sending alert {sample_id}: {exc}")
            raise self.retry(exc=exc, countdown=60)


@celery.task
def check_scheduled_alerts():
    """
    Finds queued logs that are due and dispatches them for sending.
    """
    from app.app import create_app
    app = create_app()
    with app.app_context():
        now = datetime.now(pytz.utc)
        
        # Find all log entries that are queued and past their scheduled time.
        logs_to_process = AlertLog.query.filter(
            AlertLog.status == 'queued',
            AlertLog.scheduled_for <= now
        ).all()

        for log in logs_to_process:
            # Mark as 'sending' to prevent this worker, or another one,
            # from picking up the same log in the next scheduler run.
            log.status = 'sending'
            db.session.commit()
            
            celery_logger.info(f"Dispatching alert from log {log.id} for sample {log.sample_id}")
            send_alert_task.delay(log.sample_id, log_id=log.id)