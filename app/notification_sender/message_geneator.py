import os
import html
import re
from datetime import datetime
import pytz

def get_messages(sample):
    cleaned_body = ""

    # Process the body text
    if sample.body:
        body = html.unescape(sample.body)
        body = body.replace('<br>', '\n').replace('<br/>', '\n')
        body = body.replace('</p>', '\n')
        # Remove any remaining HTML tags
        cleaned_body = re.sub(r'<[^<]+?>', '', body).strip()

    # Add the document name as an underlined clickable link with visible URL
    if sample.document_upload:
        media_base_url = os.getenv("MEDIA_BASE_URL") 
        doc_url = f"{media_base_url}/media/uploads/{sample.document_upload}"
        # HTML-escape the document name for display
        escaped_doc_name = html.escape(sample.document_upload)
        cleaned_body += f'\n\n----------------------------------------\n\n <a href="{doc_url}">🟢 Click here to download attachment </a>'

    LOCAL_TZ = pytz.timezone("Asia/Dhaka")
    now_local = datetime.now(LOCAL_TZ)
    formatted_time = now_local.strftime("%B %d, %Y at %I:%M %p")

    # HTML-escape title, formatted_time, and author
    escaped_title = html.escape(sample.title) if sample.title else "N/A"
    escaped_formatted_time = html.escape(formatted_time)
    escaped_author = html.escape(sample.sender_name) if sample.sender_name else "N/A"

    # Construct final message
    message = (
        f"📢 Announcement: {escaped_title}\n\n"
        f"🕒 Time: {escaped_formatted_time}\n\n"
        f"👤 Author: {escaped_author}\n\n"
        "----------------------------------------\n\n"
        f"📬 Message:\n\n{cleaned_body}"
    )

    return message