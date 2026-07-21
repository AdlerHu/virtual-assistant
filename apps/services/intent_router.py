import os
from enum import Enum
from google import genai
from google.genai import types
from google.cloud import firestore
from apps.features.self_introduction import self_introduction
from apps.features.restaurant_list import what_to_eat, check_list_restaurants, add_restaurant_list, alter_restaurant_list, del_restaurant_list, surprise_me
from apps.features.reminder import reminder
from apps.features.translation import translation
from apps.features.english_practice import english_practice
from apps.features.question_answering import question_answering
from apps.features.unknown import unknown


PROJECT_ID = os.environ["PROJECT_ID"]
db = firestore.Client(project=PROJECT_ID)

LOCATION = os.environ.get("LOCATION", "global")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=types.HttpOptions(api_version="v1"),
)

ROUTES = {
    Intent.SELF_INTRODUCTION: self_introduction,
    Intent.WHAT_TO_EAT: what_to_eat,
    Intent.CHECK_RESTAURANT_LIST: check_list_restaurants,
    Intent.ADD_RESTAURANT_LIST: add_restaurant_list,
    Intent.ALTER_RESTAURANT_LIST: alter_restaurant_list,
    Intent.DEL_RESTAURANT_LIST: del_restaurant_list,
    Intent.SURPRISE_ME: surprise_me,
    Intent.REMINDER: reminder,
    Intent.QUESTION_ANSWERING: question_answering,
    Intent.TRANSLATION: translation,
    Intent.ENGLISH_PRACTICE: english_practice,
    Intent.UNKNOWN: unknown,
}


class Intent(str, Enum):
    CHECK_RESTAURANT_LIST = 'check_restaurant_list'
    WHAT_TO_EAT = 'what_to_eat'
    SURPRISE_ME = 'surprise_me'
    SELF_INTRODUCTION = 'self_introduction'
    ADD_RESTAURANT_LIST = 'add_restaurant_list'
    ALTER_RESTAURANT_LIST = 'alter_restaurant_list'
    DEL_RESTAURANT_LIST = 'del_restaurant_list'
    REMINDER = 'reminder'
    QUESTION_ANSWERING = 'question_answering'
    TRANSLATION = 'translation'
    ENGLISH_PRACTICE = 'english_practice'
    UNKNOWN = 'unknown'

def detect_intent(text: str) -> str:
    prompt = f"""
你是 Telegram Bot 的意圖分類器，用作使用者意圖的初步分類。

只能回傳以下其中一個 intent：

1. 使用者要求查看、列出名單，而沒有要求建議：
  check_restaurant_list

2. 使用者要求決定吃什麼、挑一家、選一家，且沒有明確要求名單以外的新店：
  what_to_eat

3. 使用者明確要求沒吃過、新店、名單外：
  surprise_me

4. 使用者想知道你是誰、有哪些功能、可以做什麼。
  self_introduction

5. 使用者想新增餐廳至餐廳名單。
  add_restaurant_list

6. 使用者想修改餐廳名單中既有餐廳的資料。
  alter_restaurant_list

7. 使用者想刪除餐廳名單中的餐廳。
  del_restaurant_list

8. 使用者要求在某個時間提醒他做某件事。
  reminder

9. 使用者提出一般知識或資訊問題，並期待直接回答。
  例如:
  「為什麼美國的首都不是紐約?」
  「GCP提供哪些 non-container 的運算服務?」
  question_answering

10. 使用者要求翻譯文字、句子、文章或文件。
  translation

11. 使用者要求進行英文口說、對話、面試或其他英文練習。
  english_practice

12. 其他情況，或無法理解使用者的要求。
  unknown

判斷時請特別區分：

1. 「讓我看餐廳名單」是 check_restaurant_list。
2. 「中午吃什麼好呢?」是 what_to_eat。
3. 「推薦一家名單以外的新餐廳」是 surprise_me。
4. 如果使用者只說「推薦餐廳」，沒有明確說要新店或名單以外，預設判定為 what_to_eat。

使用者訊息：
{text}

只回傳 intent，不要解釋，不要加入標點、Markdown 或其他文字。
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
        return Intent(intent)

    except ValueError:
        print(f"Unexpected intent response: {intent!r}")
        return Intent.UNKNOWN.value


def intent_router(text: str):
    intent = detect_intent(text)

    handler = ROUTES.get(intent, unknown)

    return handler(
        text=text,
        db=db,
    )