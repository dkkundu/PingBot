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

def redact_token_from_url(url, token):
    if token and token in url:
        return url.replace(token, "[REDACTED_AUTH_TOKEN]")
    return url

class TelegramBot2:
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
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:# <--- This line
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
            else: # Assume it's a document if not a recognized image type
                telegram_logger.info(f"Attempting to send document from: {file_path} to chat_id: {chat_id}")
                url = f"https://api.telegram.org/bot{auth_token}/sendDocument"
                
                caption = message # Use original message for caption, assuming it's already escaped where needed
                if len(caption) > 1024: # Telegram caption limit
                    telegram_logger.warning(f"Caption for document exceeds 1024 characters. Truncating. Original length: {len(caption)}")
                    caption = caption[:1020] + "..." # Truncate and add ellipsis

                payload["caption"] = caption # Use caption for document
                
                try:
                    files = {'document': (os.path.basename(file_path), open(file_path, 'rb'))}
                except FileNotFoundError:
                    telegram_logger.error(f"File not found at {file_path} for group message.")
                    return {"error": "File not found"}
        else:
            url = f"https://api.telegram.org/bot{auth_token}/sendMessage"
            payload["text"] = message # Use original message for text, assuming it's already escaped where needed

        log_payload = payload.copy()
        telegram_logger.info(f"Sending group message to {chat_id}. URL: {redact_token_from_url(url, auth_token)}. Payload: {json.dumps(log_payload)}")

        try:
            if files:
                response = requests.post(url, data=payload, files=files, timeout=15) # Increased timeout for file uploads
            else:
                response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            telegram_logger.info(f"Group API response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            telegram_logger.error(f"Error sending group message to {redact_token_from_url(url, auth_token)}: {e}")
            if e.response:
                telegram_logger.error(f"Telegram API full error response: {e.response.text}")
            return {"error": str(e)}
        except ValueError:
            # This part of the original code is problematic as response might not be defined if RequestException occurs
            # Keeping it for now as per user's request to keep the code, but noting it.
            return {"status_code": response.status_code, "text": response.text}

    def send_document(self, auth_token, chat_id, file_path, caption=None, thread_id=None):
        """
        Sends a document to a group or individual chat.
        """
        url = f"https://api.telegram.org/bot{auth_token}/sendDocument"
        
        payload = {
            "chat_id": chat_id,
            "parse_mode": "HTML"
        }
        if caption:
            payload["caption"] = caption
        if thread_id:
            payload["message_thread_id"] = thread_id

        try:
            with open(file_path, 'rb') as f:
                files = {'document': (os.path.basename(file_path), f)}
                telegram_logger.info(f"Sending document from: {file_path} to chat_id: {chat_id}. URL: {redact_token_from_url(url, auth_token)}")
                response = requests.post(url, data=payload, files=files, timeout=30) # Increased timeout for file uploads
                response.raise_for_status()
                telegram_logger.info(f"Document API response: {response.text}")
                return response.json()
        except FileNotFoundError:
            telegram_logger.error(f"File not found at {file_path} for sending document.")
            return {"error": "File not found"}
        except requests.exceptions.RequestException as e:
            telegram_logger.error(f"Error sending document to {redact_token_from_url(url, auth_token)}: {e}")
            if e.response:
                telegram_logger.error(f"Telegram API full error response: {e.response.text}")
            return {"error": str(e)}
        except Exception as e:
            telegram_logger.error(f"An unexpected error occurred while sending document: {e}")
            return {"error": str(e)}



class TelegramBot:

    def __init__(self):
        self.url = bot_private_api
        self.group_url = bot_group_api

    def individual_message(self, mobile_number, message, image_url=None, file_path=None):
        if image_url:
            message = message + "\n" + "<a href='" + image_url + "'><i>Snapshot</i></a>"
        payload = {
            'mobile_number': mobile_number,
            'message': message}
        if file_path:
            payload['file_path'] = file_path
        payload = json.dumps(payload)
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request(
            "POST", self.url, headers=headers, data=payload, timeout=10)
        print(response.json())

    def group_message(self, auth_token, group_id, message, images_path=None):
        thread_id = None
        if '_' in group_id:
            group_id, thread_id = group_id.split('_', 1)

        payload = {
            "api_token": auth_token,
            "group_id": group_id,
            "message": message
        }
        if images_path:
            payload['file_path'] = images_path
        if thread_id:
            payload['thread_id'] = thread_id

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                self.group_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )

            # Log raw response for debugging
            telegram_logger.debug(f"Telegram response status={response.status_code}, text={response.text}")

            try:
                return response.json()
            except ValueError:
                telegram_logger.error(f"Non-JSON response from Telegram API: {response.text}")
                return {
                    "ok": False,
                    "error": "Invalid JSON response",
                    "status_code": response.status_code,
                    "raw": response.text
                }

        except requests.RequestException as e:
            telegram_logger.error(f"Telegram request failed: {str(e)}")
            return {"ok": False, "error": str(e)}