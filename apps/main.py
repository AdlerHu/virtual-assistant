import os
import requests
from flask import Flask, request
from apps.services.intent_router import intent_router


app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
        },
        timeout=10,
    )


@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    answer = intent_router(text)

    send_message(chat_id, answer)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
