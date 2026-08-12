from datetime import datetime
from enum import Enum

from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from apps.services.ai_agent import Models, generate
from apps.services.time_service import (
    get_timezone,
    now_local,
)


class ScheduleAction(str, Enum):
    CANCEL = "cancel"
    RESCHEDULE = "reschedule"


class ParsedScheduleAlter(BaseModel):
    action: ScheduleAction

    event_text: str = Field(
        min_length=1,
        description="使用者要修改或取消的既有行程名稱",
    )

    target_date: datetime | None = Field(
        default=None,
        description=(
            "使用者有指定原行程日期時才填。"
            "沒有指定則為 null。"
        ),
    )

    target_time: str | None = Field(
        default=None,
        description=(
            "使用者有指定原行程時間時才填，"
            "24 小時制 HH:MM。"
        ),
    )

    new_time: str | None = Field(
        default=None,
        description=(
            "只修改時間而沒有修改日期時使用，"
            "24 小時制 HH:MM。"
        ),
    )

    new_event_at: datetime | None = Field(
        default=None,
        description=(
            "重新排程後的新事件時間。"
            "取消行程時必須為 null。"
        ),
    )

    keep_original_time: bool = Field(
        default=False,
        description=(
            "使用者說『明天同樣時間』之類的話時為 true。"
        ),
    )

    reminder_minutes_before: int | None = Field(
        default=None,
        ge=0,
        description=(
            "只有使用者明確指定新的提前提醒分鐘數時才填。"
            "沒有要求修改提醒設定時為 null。"
        ),
    )


class ScheduleAlterParseError(Exception):
    """修改行程內容解析失敗。"""


def parse_schedule_alter(
    order: str,
    timezone_name: str,
) -> ParsedScheduleAlter:

    order = order.strip()

    if not order:
        raise ScheduleAlterParseError(
            "修改行程內容不能為空。"
        )

    try:
        get_timezone(timezone_name)
    except Exception as exc:
        raise ScheduleAlterParseError(
            f"無效的時區：{timezone_name}"
        ) from exc

    now = now_local(timezone_name)

    prompt = f"""
你是 Telegram 個人助理的行程修改解析器。

目前時間：
{now.isoformat()}

使用者時區：
{timezone_name}

你的工作只是解析使用者想如何修改「已經存在的行程」。

action 只能是：

- cancel
- reschedule


欄位說明：

1. event_text

使用者想修改或取消的既有行程名稱。

例如：
「技術部雙週會取消」
event_text = 技術部雙週會

「跟同事吃飯改到12點半」
event_text = 跟同事吃飯


2. target_date

只有使用者明確指定「原本哪一天的行程」時才填。

例如：
「取消明天的技術部雙週會」

target_date = 明天的實際日期

如果只是：
「技術部雙週會取消」

target_date = null


3. target_time

只有使用者明確指定原本那筆行程的時間時才填。

例如：
「取消今天11點的會議」

target_time = "11:00"

如果沒有指定原本時間：
target_time = null


4. new_event_at

只有 reschedule 時使用。

如果使用者提供完整的新日期和時間，
請解析成 timezone-aware datetime。


5. keep_original_time

如果使用者只改日期，但明確說保留原本時間：

例如：
「跟同事吃飯改明天同樣時間」

則：

keep_original_time = true
new_event_at = 明天日期

注意：
此時 new_event_at 的時間部分不重要，
後續程式會保留原本行程的時間。


6. reminder_minutes_before

只有使用者明確要求修改提醒時間才填。

例如：
「跟同事吃飯改明天12點半，30分鐘前提醒我」

reminder_minutes_before = 30

如果使用者沒有提到新的提醒設定：

reminder_minutes_before = null

null 代表「保留原本提醒間隔」，
不是取消提醒。


判斷規則：

1.
「技術部雙週會取消」

action = cancel
event_text = 技術部雙週會


2.
「取消今天11點的技術部雙週會」

action = cancel
event_text = 技術部雙週會
target_date = 今天
target_time = 11:00


3.
「跟同事吃飯改明天同樣時間」

action = reschedule
event_text = 跟同事吃飯
keep_original_time = true
reminder_minutes_before = null


4.
「跟同事吃飯改到12點半」

action = reschedule
event_text = 跟同事吃飯
new_event_at = 今天 12:30
keep_original_time = false
reminder_minutes_before = null


5.
「跟同事吃飯改明天12點半」

action = reschedule
event_text = 跟同事吃飯
new_event_at = 明天 12:30
keep_original_time = false


6.
「跟同事吃飯改明天12點半，30分鐘前提醒我」

action = reschedule
event_text = 跟同事吃飯
new_event_at = 明天 12:30
reminder_minutes_before = 30


7. 如果只說「改到12點半」而沒有新日期，
預設日期是原行程所在日期，
不是今天。
因此 new_event_at 可以只表達時間，
後續程式會將它套用到原行程日期。

8. 不得自行推測使用者沒有指定的新提醒時間。

9. 所有 datetime 必須使用使用者時區
{timezone_name}。

使用者訊息：

{order}
"""

    try:
        response = generate(
            model=Models.SCHEDULE_ALTER_PARSER,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=ParsedScheduleAlter,
            ),
        )

    except Exception as exc:
        raise ScheduleAlterParseError(
            "呼叫 AI 解析行程修改時發生錯誤。"
        ) from exc

    response_text = (response.text or "").strip()

    if not response_text:
        raise ScheduleAlterParseError(
            "AI 沒有回傳修改行程資料。"
        )

    try:
        parsed = ParsedScheduleAlter.model_validate_json(
            response_text
        )

    except ValidationError as exc:
        raise ScheduleAlterParseError(
            "AI 回傳的修改行程格式不正確。"
        ) from exc

    return _normalize_schedule_alter(
        parsed=parsed,
        timezone_name=timezone_name,
    )


def _normalize_schedule_alter(
    parsed: ParsedScheduleAlter,
    timezone_name: str,
) -> ParsedScheduleAlter:

    event_text = parsed.event_text.strip()

    if not event_text:
        raise ScheduleAlterParseError(
            "找不到要修改的行程名稱。"
        )

    target_date = parsed.target_date
    new_event_at = parsed.new_event_at

    if target_date is not None:
        target_date = _ensure_timezone(
            target_date,
            timezone_name,
        )

    if new_event_at is not None:
        new_event_at = _ensure_timezone(
            new_event_at,
            timezone_name,
        )

    return ParsedScheduleAlter(
        action=parsed.action,
        event_text=event_text,
        target_date=target_date,
        target_time=parsed.target_time,
        new_event_at=new_event_at,
        keep_original_time=parsed.keep_original_time,
        reminder_minutes_before=(
            parsed.reminder_minutes_before
        ),
    )


def _ensure_timezone(
    value: datetime,
    timezone_name: str,
) -> datetime:

    timezone = get_timezone(timezone_name)

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone
        )

    return value.astimezone(
        timezone
    )