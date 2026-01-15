# core/notifier.py

import os
import requests

from config.env import env 
# =============================
# TELEGRAM CONFIG
# =============================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =============================
# SEND FUNCTION
# =============================

def send(message: str):
    """
    Sends a Telegram message.
    Safe to call from anywhere in the bot.
    Fails silently if Telegram is not configured.
    """
    if not BOT_TOKEN or not CHAT_ID:
        return  # Telegram not configured

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass
