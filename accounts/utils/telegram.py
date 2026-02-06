import os
import requests
from django.conf import settings

def send_telegram_message(text):
    """
    Sends a message to a Telegram chat using the bot token and chat ID from settings.

    Args:
        text (str): The message text to send.

    Returns:
        dict: The JSON response from the Telegram API, or an error message if it fails.
    """
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)

    if not bot_token or not chat_id:
        return {"error": "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in settings."}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}