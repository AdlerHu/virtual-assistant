import os
import vertexai
from vertexai.generative_models import GenerativeModel


PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "asia-east1")

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel("gemini-1.5-flash")


def detect_intent(text: str) -> str:
    prompt = f"""
你是 Telegram Bot 的意圖分類器。

只能回傳以下其中一個 intent：
- restaurant_list：使用者想看餐廳清單、口袋名單、推薦餐廳、吃什麼、有哪些餐廳
- unknown：其他情況

使用者訊息：
{text}

只回傳 intent，不要解釋。
"""

    response = model.generate_content(prompt)
    intent = response.text.strip()

    if intent == "restaurant_list":
        return "restaurant_list"

    return "unknown"