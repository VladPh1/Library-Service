import requests
from django.conf import settings


def send_telegram_message(message_text: str):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("Telegram TOKEN or CHAT_ID do not exist.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": message_text}

    try:
        requests.post(url, data=params)
    except Exception as e:
        print(f"Error send to Telegram: {e}")
