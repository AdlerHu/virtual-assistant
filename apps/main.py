import os
import requests
from flask import Flask, request
from google.cloud import firestore
from apps.services.intent_router import detect_intent
from features.self_introduction import self_introduction
from features.restaurants import check_list_restaurants, add_restaurant_list, alter_restaurant_list, del_restaurant_list, surprise_me
from features.reminder import reminder
from features.translation import translation
from features.english_practice import english_practice
from features.question_answering import question_answering
from features.unknown import unknown


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


@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    intent = detect_intent(text)

    if intent == "self_introduction":
        answer = self_introduction()
    elif intent == "check_restaurant_list":
        answer = check_list_restaurants(db)
    elif intent == "add_restaurant_list":
        answer = add_restaurant_list()
    elif intent == "alter_restaurant_list":
        answer = alter_restaurant_list()
    elif intent == "del_restaurant_list":
        answer = del_restaurant_list()
    elif intent == "surprise_me":
        answer = surprise_me()
    elif intent == "reminder":
        answer = reminder()
    elif intent == 'question_answering':
        answer = question_answering()
    elif intent == 'translation':
        answer = translation()
    elif intent == 'english_practice':
        answer = english_practice()
    else:
        answer = unknown()

    # if text == "/restaurants":
    #     answer = list_restaurants()
    # else:
    #     intent = detect_intent(text)

    #     if intent == "restaurant_list":
    #         answer = list_restaurants()
    #     else:
    #         answer = "可用功能：\n你可以說「想看餐廳名單」、「有什麼餐廳推薦」、「今天吃什麼」。"

    send_message(chat_id, answer)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
