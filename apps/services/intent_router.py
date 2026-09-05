import os
from enum import Enum

from google.cloud import firestore
from google.genai import types

from apps.features.alter_schedule import alter_schedule
from apps.features.english_practice import english_practice
from apps.features.esports import check_esports
from apps.features.followed_teams import (
    add_followed_team,
    check_followed_teams,
    remove_followed_team,
)
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

    CHECK_ESPORTS = "check_esports"
    CHECK_FOLLOWED_TEAMS = "check_followed_teams"
    ADD_FOLLOWED_TEAM = "add_followed_team"
    REMOVE_FOLLOWED_TEAM = "remove_followed_team"

    QUESTION_ANSWERING = "question_answering"
    TRANSLATION = "translation"
    ENGLISH_PRACTICE = "english_practice"
    UNKNOWN = "unknown"


def detect_intent(text: str) -> Intent:
    prompt = f"""
你是 Telegram Bot 的意圖分類器，用作使用者意圖的初步分類。

只能回傳以下其中一個 intent：

1. 使用者要求查看、列出餐廳名單，而沒有要求建議：
   check_restaurant_list

2. 使用者要求決定吃什麼、挑一家、選一家，且沒有明確要求名單以外的新店：
   what_to_eat

3. 使用者明確要求沒吃過、新店、名單外：
   surprise_me

4. 使用者想知道你是誰、有哪些功能、可以做什麼：
   self_introduction

5. 使用者想新增餐廳至餐廳名單：
   add_restaurant_list

6. 使用者想修改餐廳名單中既有餐廳的資料：
   alter_restaurant_list

7. 使用者想刪除餐廳名單中的餐廳：
   del_restaurant_list


8. 使用者要求建立新的提醒或行程：
   reminder

例如：
「明天上午10點提醒我回代理商」
「今天下午2點開會，10分鐘前提醒我」
「15分鐘後提醒我喝乳清蛋白」
「明天預定行程如下，10分鐘前提醒我：...」


9. 使用者想查看已建立的行程、提醒、安排或空檔：
   check_schedule

只要使用者是在詢問自己某一天、某一週或未來某個時間
已經安排了什麼事情，就判定為 check_schedule。

例如：
「我今天有什麼行程？」
「明天安排了什麼？」
「後天有什麼事？」
「29號有什麼行程？」
「29日有什麼安排？」
「9/27有什麼行程？」
「9月27日有什麼安排？」
「週三有什麼行程？」
「星期五有什麼事？」
「下週二有什麼行程？」
「下星期三有什麼安排？」
「本週有什麼行程？」
「這週有什麼安排？」
「下週有什麼行程？」
「我下午3點有沒有空檔？」


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


11. 使用者想查看自己關注的 LOL / 電競比賽：
    check_esports

這裡的「比賽」是指使用者目前關注的電競比賽，
可能包含 LCK、LOL 世界賽或其他已訂閱的賽事。

例如：
「今天有LOL比賽嗎？」
「今天有比賽嗎？」
「LCK今天有比賽嗎？」
「明天有LOL比賽嗎？」
「後天有比賽嗎？」
「週三有比賽嗎？」
「下週二有LOL比賽嗎？」
「本週有什麼比賽？」
「下週有哪些比賽？」
「世界賽明天有比賽嗎？」

只要使用者是在詢問比賽賽程，
而不是詢問自己的行程，就判定為 check_esports。


12. 使用者想查看自己目前關注哪些隊伍：
    check_followed_teams

例如：
「我現在有哪些關注隊伍？」
「我關注哪些隊伍？」
「我的關注名單有哪些？」
「LCK我關注哪些隊伍？」
「LCK關注名單有哪些？」
「LOL世界賽我關注哪些隊伍？」
「世界賽關注隊伍有哪些？」

如果使用者沒有指定 LCK 或世界賽，
仍然判定為 check_followed_teams。
實際要顯示哪個名單，由後續功能判斷。


13. 使用者想新增隊伍到自己的關注名單：
    add_followed_team

例如：
「關注隊伍加上KT」
「把KT加進關注名單」
「我要關注KT」
「幫我關注KT」
「LCK關注隊伍加上KT」
「世界賽關注隊伍加上G2」
「把T1加入世界賽關注名單」

不論使用者有沒有指定 LCK 或世界賽，
只要是在新增關注隊伍，就判定為 add_followed_team。
實際要新增到哪些名單，由後續功能判斷。


14. 使用者想從自己的關注名單移除隊伍：
    remove_followed_team

例如：
「把KT從關注名單移除」
「不要再關注KT」
「取消關注KT」
「LCK不要再關注KT」
「把G2從世界賽關注隊伍移除」
「世界賽不要再關注T1」

不論使用者有沒有指定 LCK 或世界賽，
只要是在移除關注隊伍，就判定為 remove_followed_team。
實際要從哪些名單移除，由後續功能判斷。


15. 使用者提出一般知識或資訊問題，並期待直接回答：
    question_answering

例如：
「為什麼美國的首都不是紐約？」
「GCP提供哪些 non-container 的運算服務？」


16. 使用者要求翻譯文字、句子、文章或文件：
    translation


17. 使用者要求進行英文口說、對話、面試或其他英文練習：
    english_practice


18. 其他情況，或無法理解使用者的要求：
    unknown


判斷時請特別區分：

1. 「讓我看餐廳名單」是 check_restaurant_list。

2. 「中午吃什麼好呢？」是 what_to_eat。

3. 「推薦一家名單以外的新餐廳」是 surprise_me。

4. 如果使用者只說「推薦餐廳」，
   沒有明確說要新店或名單以外，
   預設判定為 what_to_eat。

5. 「明天11點提醒我技術部雙週會」是 reminder，
   因為使用者正在建立新的行程。

6. 「技術部雙週會取消」是 alter_schedule，
   因為使用者正在操作既有行程。

7. 「跟同事吃飯改明天同樣時間」是 alter_schedule。

8. 「跟同事吃飯改到12點半」是 alter_schedule。

9. 「我明天有什麼行程？」是 check_schedule，
   因為使用者是在查看自己的行程。

10. 「今天有比賽嗎？」是 check_esports，
    不是 check_schedule。
    「比賽」、「LOL」、「LCK」、「世界賽」等電競語境
    優先判定為 check_esports。

11. 「LCK今天有比賽嗎？」是 check_esports。

12. 「我現在有哪些關注隊伍？」是 check_followed_teams。

13. 「LCK我關注哪些隊伍？」是 check_followed_teams。

14. 「世界賽我關注哪些隊伍？」是 check_followed_teams。

15. 「關注隊伍加上KT」是 add_followed_team。

16. 「世界賽關注隊伍加上G2」是 add_followed_team。

17. 「把KT從關注名單移除」是 remove_followed_team。

18. 「世界賽不要再關注G2」是 remove_followed_team。


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

        Intent.REMINDER: lambda: reminder(
            order=text,
            chat_id=chat_id,
            db=db,
        ),
        Intent.CHECK_SCHEDULE: lambda: check_schedule(
            order=text,
            chat_id=chat_id,
            db=db,
        ),
        Intent.ALTER_SCHEDULE: lambda: alter_schedule(
            order=text,
            chat_id=chat_id,
            db=db,
        ),

        Intent.CHECK_ESPORTS: lambda: check_esports(
            order=text,
            chat_id=chat_id,
            db=db,
        ),
        Intent.CHECK_FOLLOWED_TEAMS: lambda: check_followed_teams(
            order=text,
            chat_id=chat_id,
            db=db,
        ),
        Intent.ADD_FOLLOWED_TEAM: lambda: add_followed_team(
            order=text,
            chat_id=chat_id,
            db=db,
        ),
        Intent.REMOVE_FOLLOWED_TEAM: lambda: remove_followed_team(
            order=text,
            chat_id=chat_id,
            db=db,
        ),

        Intent.QUESTION_ANSWERING: lambda: question_answering(
            question=text
        ),
        Intent.TRANSLATION: translation,
        Intent.ENGLISH_PRACTICE: english_practice,
        Intent.UNKNOWN: unknown,
    }

    handler = routes.get(intent, unknown)

    return handler()
