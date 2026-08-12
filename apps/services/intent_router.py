import os
from enum import Enum

from google.cloud import firestore
from google.genai import types

from apps.features.alter_schedule import alter_schedule
from apps.features.english_practice import english_practice
from apps.features.question_answering import question_answering
from apps.features.reminder import reminder
from apps.features.restaurant_list import (
    add_restaurant_list,
    alter_restaurant_list,
    check_restaurant_list,
    del_restaurant_list,
    surprise_me,
    what_to_eat,
)
from apps.features.schedule import check_schedule
from apps.features.self_introduction import self_introduction
from apps.features.translation import translation
from apps.features.unknown import unknown
from apps.services.ai_agent import Models, generate

PROJECT_ID = os.environ["PROJECT_ID"]
db = firestore.Client(project=PROJECT_ID)


class Intent(str, Enum):
    CHECK_RESTAURANT_LIST = "check_restaurant_list"
    WHAT_TO_EAT = "what_to_eat"
    SURPRISE_ME = "surprise_me"
    SELF_INTRODUCTION = "self_introduction"
    ADD_RESTAURANT_LIST = "add_restaurant_list"
    ALTER_RESTAURANT_LIST = "alter_restaurant_list"
    DEL_RESTAURANT_LIST = "del_restaurant_list"

    REMINDER = "reminder"
    CHECK_SCHEDULE = "check_schedule"
    ALTER_SCHEDULE = "alter_schedule"

    QUESTION_ANSWERING = "question_answering"
    TRANSLATION = "translation"
    ENGLISH_PRACTICE = "english_practice"
    UNKNOWN = "unknown"


def detect_intent(text: str) -> Intent:
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

8. 使用者要求建立新的提醒或行程：
   reminder

例如：
「明天上午10點提醒我回代理商」
「今天下午2點開會，10分鐘前提醒我」
「15分鐘後提醒我喝乳清蛋白」
「明天預定行程如下，10分鐘前提醒我：...」

9. 使用者想查看已建立的行程、提醒或空檔：
   check_schedule

例如：
「我今天有什麼行程？」
「明天安排了什麼？」
「我下午有什麼事？」
「我下午3點有沒有空檔？」
「8月15日有什麼行程？」

10. 使用者想修改或取消已經存在的行程或提醒：
    alter_schedule

包括：
- 取消既有行程
- 更改既有行程的日期
- 更改既有行程的時間
- 將既有行程延後或提前
- 修改既有行程的提醒設定

例如：
「技術部雙週會取消」
「取消今天的技術部雙週會」
「跟同事吃飯改明天同樣時間」
「跟同事吃飯改到12點半」
「明天的會議改到下午3點」
「看牙醫延後一個小時」
「技術部雙週會改成30分鐘前提醒我」

只要使用者是在操作一個已經存在的行程，
而不是建立新的行程，就判定為 alter_schedule。
  
11. 使用者提出一般知識或資訊問題，並期待直接回答。
  例如:
  「為什麼美國的首都不是紐約?」
  「GCP提供哪些 non-container 的運算服務?」
  question_answering

12. 使用者要求翻譯文字、句子、文章或文件。
  translation

13. 使用者要求進行英文口說、對話、面試或其他英文練習。
  english_practice

14. 其他情況，或無法理解使用者的要求。
  unknown

判斷時請特別區分：

1. 「讓我看餐廳名單」是 check_restaurant_list。
2. 「中午吃什麼好呢?」是 what_to_eat。
3. 「推薦一家名單以外的新餐廳」是 surprise_me。
4. 如果使用者只說「推薦餐廳」，沒有明確說要新店或名單以外，預設判定為 what_to_eat。
5. 「明天11點提醒我技術部雙週會」是 reminder，
   因為使用者正在建立新的行程。

6. 「技術部雙週會取消」是 alter_schedule，
   因為使用者正在操作既有行程。

7. 「跟同事吃飯改明天同樣時間」是 alter_schedule。

8. 「跟同事吃飯改到12點半」是 alter_schedule。

9. 「我明天有什麼行程？」是 check_schedule，
   因為使用者只是在查看行程，沒有修改。v

使用者訊息：
{text}

只回傳 intent，不要解釋，不要加入標點、Markdown 或其他文字。
"""

  response = generate(
    model=Models.INTENT_ROUTER,
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
    return Intent.UNKNOWN


def intent_router(text: str, chat_id: int):
  intent = detect_intent(text)

  routes = {
    Intent.SELF_INTRODUCTION: self_introduction,
    Intent.WHAT_TO_EAT: what_to_eat,
    Intent.CHECK_RESTAURANT_LIST: lambda: check_restaurant_list(db=db),
    Intent.ADD_RESTAURANT_LIST: add_restaurant_list,
    Intent.ALTER_RESTAURANT_LIST: alter_restaurant_list,
    Intent.DEL_RESTAURANT_LIST: del_restaurant_list,
    Intent.SURPRISE_ME: surprise_me,
    Intent.REMINDER: lambda: reminder(order=text, chat_id=chat_id, db=db),
    Intent.CHECK_SCHEDULE: lambda: check_schedule(order=text, chat_id=chat_id, db=db),
    Intent.ALTER_SCHEDULE: lambda: alter_schedule(order=text, chat_id=chat_id,db=db),
    Intent.QUESTION_ANSWERING: lambda: question_answering(question=text),
    Intent.TRANSLATION: translation,
    Intent.ENGLISH_PRACTICE: english_practice,
    Intent.UNKNOWN: unknown,
  }

  handler = routes.get(intent, unknown)

  return handler()

