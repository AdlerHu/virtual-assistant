from datetime import datetime
from zoneinfo import ZoneInfo

from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from apps.services.ai_agent import Models, generate

TIMEZONE_NAME = "Asia/Taipei"
TIMEZONE = ZoneInfo(TIMEZONE_NAME)


class ParsedReminder(BaseModel):
    event_text: str = Field(
        min_length=1,
        description="行程或待辦事項內容",
    )

    event_at: datetime = Field(
        description="事件實際發生時間，必須包含時區",
    )

    notify_at: datetime = Field(
        description="實際發送提醒的時間，必須包含時區",
    )


class ParsedReminderList(BaseModel):
    reminders: list[ParsedReminder]


class ReminderParseError(Exception):
    """提醒內容解析失敗。"""


def parse_reminders(order: str) -> list[ParsedReminder]:
    """
    將自然語言解析成一筆或多筆提醒。

    支援：

    明天早上 10 點提醒我回信

    明天預定行程如下，15 分鐘前提醒我：
    1. 上午 8 點，回 ticket
    2. 上午 9 點，回代理商 email
    """

    order = order.strip()

    if not order:
        raise ReminderParseError("提醒內容不能為空。")

    now = datetime.now(TIMEZONE)

    prompt = f"""
你是 Telegram 個人助理的提醒與行程解析器。

目前時間：
{now.isoformat()}

使用者時區：
{TIMEZONE_NAME}

請將使用者訊息解析成一筆或多筆提醒。

每筆資料必須包含：

1. event_text
   事件或待辦事項本身。

2. event_at
   事件實際發生時間。

3. notify_at
   Telegram 應該發送提醒的時間。

規則：

1. event_text 不要包含「提醒我」、「請提醒我」等命令文字。

2. 如果使用者說：
   「明天上午 10 點提醒我回信」
   則 event_at 和 notify_at 都是明天上午 10 點。

3. 如果使用者說：
   「明天下午 2 點開會，15 分鐘前提醒我」
   則 event_at 是明天下午 2 點，
   notify_at 是明天下午 1 點 45 分。

4. 如果使用者在行程表開頭統一指定：
   「15 分鐘前提醒我」
   則所有行程都必須提前 15 分鐘提醒。

5. 如果沒有指定提前提醒時間，
   notify_at 必須等於 event_at。

6. 一段訊息可能包含一筆或多筆行程。
   不得遺漏任何一筆。

7. 「明天」、「後天」、「下週一」等相對日期，
   必須根據目前時間換算成實際日期。

8. 時間轉換：
   - 上午 8 點 = 08:00
   - 上午 11 點 = 11:00
   - 中午 12 點 = 12:00
   - 下午 2 點 = 14:00
   - 下午 5 點 = 17:00
   - 下午 7 點半 = 19:30
   - 晚上 9 點 = 21:00

9. event_at 和 notify_at 必須包含 +08:00 時區。

10. 不得自行增加使用者沒有提到的事件。

11. 「買小蘇打、漂白水」是一筆事件，
    不要因為頓號而拆成兩筆。

使用者訊息：

{order}
"""

    try:
        response = generate(
            model=Models.REMINDER_PARSER,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=ParsedReminderList,
            ),
        )
    except Exception as exc:
        raise ReminderParseError(
            "呼叫 AI 解析提醒時發生錯誤。"
        ) from exc

    response_text = (response.text or "").strip()

    if not response_text:
        raise ReminderParseError("AI 沒有回傳提醒資料。")

    try:
        parsed = ParsedReminderList.model_validate_json(
            response_text
        )
    except ValidationError as exc:
        raise ReminderParseError(
            "AI 回傳的提醒格式不正確。"
        ) from exc

    if not parsed.reminders:
        raise ReminderParseError("沒有辨識到任何提醒。")

    return [
        _normalize_reminder(item)
        for item in parsed.reminders
    ]


def _normalize_reminder(
    reminder: ParsedReminder,
) -> ParsedReminder:
    event_text = reminder.event_text.strip()

    if not event_text:
        raise ReminderParseError("提醒事項不能為空。")

    return ParsedReminder(
        event_text=event_text,
        event_at=_ensure_timezone(reminder.event_at),
        notify_at=_ensure_timezone(reminder.notify_at),
    )


def _ensure_timezone(value: datetime) -> datetime:
    """
    Gemini 沒回傳時區時，預設為台灣時間。
    有時區時則統一轉為台灣時間。
    """

    if value.tzinfo is None:
        return value.replace(tzinfo=TIMEZONE)

    return value.astimezone(TIMEZONE)
