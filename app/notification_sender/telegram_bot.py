import requests
import json
import os
from dotenv import load_dotenv
from app.logging_config import telegram_logger

# Load environment variables
load_dotenv()

bot_group_api = os.getenv("BOT_GROUP_API")
bot_private_api = os.getenv("BOT_PRIVATE_API")

class TelegramBot:
    """
    A class to handle sending messages to Telegram.
    """
    def __init__(self):
        """
        Initializes the TelegramBot with the API URLs.
        """
        self.private_url = bot_private_api
        self.group_url = bot_group_api

    def individual_message(self, mobile_number, message, image_url=None, file_path=None):
        """
        Sends a message to an individual user.

        Args:
            mobile_number (str): The user's mobile number.
            message (str): The message to send.
            image_url (str, optional): The URL of an image to include.
            file_path (str, optional): The path to a file to send.

        Returns:
            dict: The JSON response from the API or an error dictionary.
        """
        if image_url:
            message = f"{message}\n<a href='{image_url}'><i>Snapshot</i></a>"

        payload = {"mobile_number": mobile_number, "message": message}
        if file_path:
            payload["file_path"] = file_path

        telegram_logger.info(f"Sending individual message to {mobile_number}. Payload: {json.dumps(payload)}")

        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.private_url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            telegram_logger.info(f"Individual API response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            telegram_logger.error(f"Error sending individual message: {e}")
            return {"error": str(e)}
        except ValueError:
            return {"status_code": response.status_code, "text": response.text}

    def group_message(self, auth_token, group_id, message, image_url=None, file_path=None):
       
        # The API token should be in the URL, not the payload
        url = f"https://api.telegram.org/bot{auth_token}/sendMessage"

        # Construct the payload with 'chat_id' and 'text'
        payload = {
            "chat_id": group_id,
            "text": message
        }

        # Handle file attachments (sendPhoto)
        files = {}
        if file_path:
            telegram_logger.info(f"Attempting to send photo from: {file_path} to chat_id: {group_id}")
            url = f"https://api.telegram.org/bot{auth_token}/sendPhoto"
            
            caption = message
            if len(caption) > 1024:
                telegram_logger.warning(f"Caption for photo exceeds 1024 characters. Truncating. Original length: {len(caption)}")
                caption = caption[:1020] + "..." # Truncate and add ellipsis

            payload = {
                "chat_id": group_id,
                "caption": caption
            }
            
            try:
                # Use a tuple for files to ensure proper multipart/form-data encoding
                # ('photo', file_object, 'image/jpeg') - mimetype is optional but good practice
                # requests will handle closing the file if passed this way
                files = {'photo': (os.path.basename(file_path), open(file_path, 'rb'))}
            except FileNotFoundError:
                telegram_logger.error(f"File not found at {file_path} for group message.")
                return {"error": "File not found"}

        # Handle thread_id if present
        thread_id = None
        if "_" in group_id: # Assuming group_id might contain thread_id like "group_id_thread_id"
            group_id, thread_id = group_id.split("_")
            payload["chat_id"] = group_id # Ensure chat_id is just the group_id
            if thread_id:
                payload["message_thread_id"] = thread_id # Correct parameter for threads

        # Adjust logging to reflect the correct payload
        log_payload = payload.copy()

        telegram_logger.info(f"Sending group message to {group_id}. Payload: {json.dumps(log_payload)}")

        headers = {"Content-Type": "application/json"}
        try:
            if files:
                response = requests.post(url, data=payload, files=files, timeout=10) # Use data for multipart/form-data with files
            else:
                response = requests.post(url, json=payload, timeout=10) # Use json for application/json
            response.raise_for_status()
            telegram_logger.info(f"Group API response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            telegram_logger.error(f"Error sending group message: {e}")
            return {"error": str(e)}
        except ValueError:
            return {"status_code": response.status_code, "text": response.text}