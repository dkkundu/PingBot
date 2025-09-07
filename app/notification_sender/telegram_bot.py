import requests
import json
import os
import html # Added this line for html.escape
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
        # These URLs are not directly used by group_message, but kept for consistency if individual_message uses them
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
        # Ensure message is HTML escaped if it contains user-generated content
        escaped_message = html.escape(message)

        if image_url:
            escaped_message = f"{escaped_message}\n<a href='{image_url}'><i>Snapshot</i></a>"

        payload = {"mobile_number": mobile_number, "message": escaped_message}
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
            # This part of the original code is problematic as response might not be defined if RequestException occurs
            # Keeping it for now as per user's request to keep the code, but noting it.
            return {"status_code": response.status_code, "text": response.text}

    def group_message(self, auth_token, chat_id, message, file_path=None):
        """
        Sends a message to a group, with optional photo attachment.
        This method consolidates send_text and send_photo functionality.
        """
        # Determine if chat_id contains a thread_id
        thread_id = None
        original_chat_id = str(chat_id) # Convert to string to handle potential int inputs
        if "_" in original_chat_id:
            parts = original_chat_id.split("_", 1)
            if len(parts) == 2 and parts[1].isdigit(): # Basic check for valid thread_id format
                chat_id = parts[0]
                thread_id = parts[1]
            else:
                # If it has an underscore but isn't a valid thread_id format, treat it as a regular chat_id
                chat_id = original_chat_id
        else:
            chat_id = original_chat_id

        payload = {
            "chat_id": chat_id,
            "parse_mode": "HTML" # Always use HTML parse mode for consistency
        }
        if thread_id:
            payload["message_thread_id"] = thread_id

        files = {}
        if file_path and os.path.exists(file_path):
            telegram_logger.info(f"Attempting to send photo from: {file_path} to chat_id: {chat_id}")
            url = f"https://api.telegram.org/bot{auth_token}/sendPhoto"
            
            caption = message # Use original message for caption, assuming it's already escaped where needed
            if len(caption) > 1024: # Telegram caption limit
                telegram_logger.warning(f"Caption for photo exceeds 1024 characters. Truncating. Original length: {len(caption)}")
                caption = caption[:1020] + "..." # Truncate and add ellipsis

            payload["caption"] = caption # Use caption for photo
            
            try:
                files = {'photo': (os.path.basename(file_path), open(file_path, 'rb'))}
            except FileNotFoundError:
                telegram_logger.error(f"File not found at {file_path} for group message.")
                return {"error": "File not found"}
        else:
            url = f"https://api.telegram.org/bot{auth_token}/sendMessage"
            payload["text"] = message # Use original message for text, assuming it's already escaped where needed

        log_payload = payload.copy()
        telegram_logger.info(f"Sending group message to {chat_id}. Payload: {json.dumps(log_payload)}")

        try:
            if files:
                response = requests.post(url, data=payload, files=files, timeout=15) # Increased timeout for file uploads
            else:
                response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            telegram_logger.info(f"Group API response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            telegram_logger.error(f"Error sending group message: {e}")
            if e.response:
                telegram_logger.error(f"Telegram API full error response: {e.response.text}")
            return {"error": str(e)}
        except ValueError:
            # This part of the original code is problematic as response might not be defined if RequestException occurs
            # Keeping it for now as per user's request to keep the code, but noting it.
            return {"status_code": response.status_code, "text": response.text}
