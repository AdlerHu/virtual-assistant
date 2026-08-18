import os
from datetime import datetime
from typing import Any

import requests
from flask import Flask, jsonify, request

from apps.services.intent_router import intent_router

import traceback


app = Flask(__name__)


BOT_TOKEN = os.environ["BOT_TOKEN"]

TELEGRAM_API_BASE_URL = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)


@app.get("/")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": "virtual-assistant",
        }
    ), 200


@app.post("/webhook")
def telegram_webhook():
    """
    接收 Telegram webhook。
    """

    update = request.get_json(silent=True)

    if not isinstance(update, dict):
        return jsonify({"status": "ignored"}), 200

    message = update.get("message")

    if not isinstance(message, dict):
        return jsonify({"status": "ignored"}), 200

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text")

    if chat_id is None:
        return jsonify({"status": "ignored"}), 200

    if not isinstance(text, str) or not text.strip():
        try:
            send_message(
                chat_id=int(chat_id),
                text="目前只支援文字訊息。",
            )
        except Exception as exc:
            print(f"Failed to send message: {exc}")

        return jsonify({"status": "ok"}), 200

    text = text.strip()

    try:
        answer = intent_router(
            text=text,
            chat_id=int(chat_id),
        )

    except Exception as exc:
        print(
            "Intent router failed: "
            f"chat_id={chat_id}, "
            f"text={text!r}, "
            f"error={exc}"
        )

        traceback.print_exc()
        answer = "處理訊息時發生錯誤，請稍後再試。"

    try:
        send_message(
            chat_id=int(chat_id),
            text=answer,
        )

    except Exception as exc:
        print(
            "Telegram sendMessage failed: "
            f"chat_id={chat_id}, "
            f"error={exc}"
        )

    # 固定回傳 200，避免 Telegram 不斷重送相同 update。
    return jsonify({"status": "ok"}), 200


@app.post("/tasks/send-reminder")
def send_reminder_task():
    """
    Cloud Tasks 到達排程時間後呼叫此 endpoint。
    """

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            {
                "error": "Invalid JSON body",
            }
        ), 400

    chat_id = data.get("chat_id")
    reminder_text = data.get("reminder_text")
    event_at_raw = data.get("event_at")

    if chat_id is None:
        return jsonify(
            {
                "error": "Missing chat_id",
            }
        ), 400

    if (
        not isinstance(reminder_text, str)
        or not reminder_text.strip()
    ):
        return jsonify(
            {
                "error": "Missing reminder_text",
            }
        ), 400

    event_time = _format_event_time(event_at_raw)

    if event_time:
        telegram_text = (
            f"提醒：{event_time}\n"
            f"{reminder_text.strip()}"
        )
    else:
        telegram_text = (
            f"提醒：{reminder_text.strip()}"
        )

    try:
        send_message(
            chat_id=int(chat_id),
            text=telegram_text,
        )

    except Exception as exc:
        print(
            "Reminder delivery failed: "
            f"chat_id={chat_id}, "
            f"reminder_text={reminder_text!r}, "
            f"error={exc}"
        )

        # Cloud Tasks 收到非 2xx 後，會按照 queue 設定重試。
        return jsonify(
            {
                "error": "Telegram send failed",
            }
        ), 500

    return jsonify({"status": "sent"}), 200


def send_message(chat_id: int, text: str) -> None:
    """
    使用 Telegram Bot API 傳送文字訊息。
    """

    response = requests.post(
        f"{TELEGRAM_API_BASE_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
        },
        timeout=15,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API returned an error: {result}"
        )


def _format_event_time(
    event_at_raw: Any,
) -> str | None:
    """
    將 ISO 8601 時間轉成顯示格式。
    """

    if not isinstance(event_at_raw, str):
        return None

    try:
        event_at = datetime.fromisoformat(event_at_raw)
    except ValueError:
        return None

    return event_at.strftime("%m/%d %H:%M")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))

    app.run(
        host="0.0.0.0",
        port=port
    )