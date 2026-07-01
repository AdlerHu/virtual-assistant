import os
import requests
from flask import Flask, request
from google.cloud import firestore
from services.intent_router import detect_intent


app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
PROJECT_ID = os.environ["PROJECT_ID"]

db = firestore.Client(project=PROJECT_ID)

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
        },
        timeout=10,
    )

def list_restaurants():
    docs = db.collection("restaurant_list").stream()

    rows = []
    for doc in docs:
        r = doc.to_dict()
        rows.append(
            f"{r.get('nickname', doc.id)}｜{r.get('fullname', '-')}｜{r.get('category', '-')}"
            f"｜${r.get('budget_min', '?')}-{r.get('budget_max', '?')}"
        )

    if not rows:
        return "目前沒有餐廳資料。"

    return "餐廳清單：\n\n" + "\n".join(rows)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if text == "/restaurants":
        answer = list_restaurants()
    else:
        intent = detect_intent(text)

        if intent == "restaurant_list":
            answer = list_restaurants()
        else:
            answer = "可用功能：\n你可以說「想看餐廳名單」、「有什麼餐廳推薦」、「今天吃什麼」。"

    send_message(chat_id, answer)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
