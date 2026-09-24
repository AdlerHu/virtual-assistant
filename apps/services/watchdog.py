import os

import requests

TELEGRAM_BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_WEBHOOK_URL = 'https://virtual-assistant-hktcbvecsq-de.a.run.app/webhook'

def check_telegram_webhook() -> dict:
    response = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo",
        timeout=10,
    )
    response.raise_for_status()

    info = response.json()["result"]

    actual_url = info.get("url", "")
    expected_url = TELEGRAM_WEBHOOK_URL

    return {
        "healthy": actual_url == expected_url,
        "expected_url": expected_url,
        "actual_url": actual_url,
        "pending_update_count": info.get("pending_update_count", 0),
        "last_error_message": info.get("last_error_message"),
    }