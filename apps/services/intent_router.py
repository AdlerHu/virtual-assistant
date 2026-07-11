import os
from enum import Enum

from google import genai
from google.genai import types


PROJECT_ID = os.environ.get(
    "PROJECT_ID",
    "skills-building-413521",
)
LOCATION = os.environ.get("LOCATION", "global")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=types.HttpOptions(api_version="v1"),
)


class Intent(str, Enum):
    SELF_INTRODUCTION = "self_introduction"
    CHECK_RESTAURANT_LIST = "check_restaurant_list"
    ADD_RESTAURANT_LIST = "add_restaurant_list"
    ALTER_RESTAURANT_LIST = "alter_restaurant_list"
    DEL_RESTAURANT_LIST = "del_restaurant_list"
    SURPRISE_ME = "surprise_me"
    REMINDER = "reminder"
    QUESTION_ANSWERING = "question_answering"
    TRANSLATION = "translation"
    ENGLISH_PRACTICE = "english_practice"
    UNKNOWN = "unknown"


def detect_intent(text: str) -> str:
    prompt = f"""
你是 Telegram Bot 的意圖分類器。

分類規則：
- self_introduction: 使用者想知道你有什麼功能
- check_restaurant_list: 查看餐廳清單或口袋名單
- add_restaurant_list: 新增餐廳至清單
- alter_restaurant_list: 修改餐廳清單中的資料
- del_restaurant_list: 刪除餐廳清單中的餐廳
- surprise_me: 推薦一間不在既有清單中的餐廳
- reminder: 要求在特定時間提醒某件事
- question_answering: 提出一般問題並期待答案
- translation: 要求翻譯
- english_practice: 要求進行英文口說練習
- unknown: 其他情況或無法理解

使用者訊息：
{text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="text/x.enum",
            response_schema=Intent,
        ),
    )

    intent = (response.text or "").strip()

    try:
        return Intent(intent).value
    except ValueError:
        print(f"Unexpected intent response: {intent!r}")
        return Intent.UNKNOWN.value
