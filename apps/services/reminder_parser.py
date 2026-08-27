from datetime import datetime

from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from apps.services.ai_agent import Models, generate
from apps.services.time_service import (
    get_timezone,
    now_local,
)

import re

from datetime import datetime, time, timedelta

from apps.services.time_service import (
    get_timezone,
    now_local,
)


WEEKDAY_MAP = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}


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


def parse_reminders(
    order: str,
    timezone_name: str,
) -> list[ParsedReminder]:
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

    try:
        timezone = get_timezone(timezone_name)
    except Exception as exc:
        raise ReminderParseError(
            f"無效的時區：{timezone_name}"
        ) from exc

    now = now_local(timezone_name)

    prompt = f"""
你是 Telegram 個人助理的提醒與行程解析器。

目前時間：
{now.isoformat()}

使用者時區：
{timezone_name}

目前 UTC offset：
{now.strftime("%z")}

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
   而沒有指定提前多久提醒，
   則：
   event_at = 明天上午 10 點
   notify_at = 明天上午 9 點 45 分。

3. 如果使用者說：
   「明天下午 2 點開會，15 分鐘前提醒我」
   則 event_at 是明天下午 2 點，
   notify_at 是明天下午 1 點 45 分。

4. 如果使用者在行程表開頭統一指定：
   「15 分鐘前提醒我」
   則所有行程都必須提前 15 分鐘提醒。

5. 如果沒有指定提前提醒時間，
   notify_at 預設為 event_at 的 15 分鐘前。

6. 如果使用者說：
   「15 分鐘後提醒我做某事」
   則這裡的「15 分鐘後」是在指定事件時間，
   不是「提前 15 分鐘提醒」。

   因此：
   event_at = 現在時間 + 15 分鐘
   notify_at = event_at

7. 一段訊息可能包含一筆或多筆行程。
   不得遺漏任何一筆。

8. 「明天」、「後天」、「下週一」等相對日期，
   必須根據目前時間換算成實際日期。

9. 時間轉換：
   - 上午 8 點 = 08:00
   - 上午 11 點 = 11:00
   - 中午 12 點 = 12:00
   - 下午 2 點 = 14:00
   - 下午 5 點 = 17:00
   - 下午 7 點半 = 19:30
   - 晚上 9 點 = 21:00

10. event_at 和 notify_at 必須使用使用者目前時區
    {timezone_name}
    所對應的 UTC offset。

11. 不得自行增加使用者沒有提到的事件。

12. 「買小蘇打、漂白水」是一筆事件，
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
        raise ReminderParseError(
            "AI 沒有回傳提醒資料。"
        )

    try:
        parsed = ParsedReminderList.model_validate_json(
            response_text
        )

    except ValidationError as exc:
        raise ReminderParseError(
            "AI 回傳的提醒格式不正確。"
        ) from exc

    if not parsed.reminders:
        raise ReminderParseError(
            "沒有辨識到任何提醒。"
        )

    return [
        _normalize_reminder(
            reminder=item,
            timezone_name=timezone_name,
        )
        for item in parsed.reminders
    ]


def _normalize_reminder(
    reminder: ParsedReminder,
    timezone_name: str,
) -> ParsedReminder:
    event_text = reminder.event_text.strip()

    if not event_text:
        raise ReminderParseError(
            "提醒事項不能為空。"
        )

    return ParsedReminder(
        event_text=event_text,
        event_at=_ensure_timezone(
            reminder.event_at,
            timezone_name,
        ),
        notify_at=_ensure_timezone(
            reminder.notify_at,
            timezone_name,
        ),
    )


def _ensure_timezone(
    value: datetime,
    timezone_name: str,
) -> datetime:
    """
    Gemini 沒有回傳 timezone 時，
    視為使用者目前的 local time。

    已包含 timezone 時，
    轉成使用者目前 timezone。
    """

    timezone = get_timezone(timezone_name)

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone
        )

    return value.astimezone(
        timezone
    )

def parse_schedule_range(
    order: str,
    timezone_name: str,
) -> tuple[datetime, datetime, str]:
    """
    將自然語言中的日期範圍解析成：

    start_at
    end_at
    label

    規則：
    - 一週從週日開始
    - 只查今天與未來
    - 「週二」代表最近一個尚未過去的週二
    - 「下週二」代表下一個 calendar week 的週二
    - 「29號」預設本月
    - 「9/27」預設今年
    """

    timezone = get_timezone(timezone_name)
    now = now_local(timezone_name)

    order = order.strip()

    # --------------------------------------------------
    # 1. 今天 / 明天 / 後天
    # --------------------------------------------------

    if "後天" in order:
        target_date = (
            now.date()
            + timedelta(days=2)
        )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label="後天",
        )

    if "明天" in order:
        target_date = (
            now.date()
            + timedelta(days=1)
        )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label="明天",
        )

    if "今天" in order:
        return _build_day_range(
            target_date=now.date(),
            timezone=timezone,
            label="今天",
        )

    # --------------------------------------------------
    # 2. 下週二 / 下星期二 / 下禮拜二
    #
    # 必須放在一般「週二」前面，
    # 否則 regex 可能先吃到後面的「週二」。
    # --------------------------------------------------

    next_weekday_match = re.search(
        r"下(?:週|星期|禮拜)"
        r"([一二三四五六日天])",
        order,
    )

    if next_weekday_match:
        weekday_text = (
            next_weekday_match.group(1)
        )

        weekday = WEEKDAY_MAP[
            weekday_text
        ]

        target_date = _get_next_weekday_date(
            now=now,
            weekday=weekday,
        )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label=f"下週{weekday_text}",
        )

    # --------------------------------------------------
    # 3. 本週 / 這週
    #
    # 一週定義：
    # Sunday ~ Saturday
    #
    # 因為不查過去，
    # start_at 直接從「現在」開始。
    # --------------------------------------------------

    if (
        "本週" in order
        or "這週" in order
    ):
        this_sunday = _get_this_sunday(
            now
        )

        next_sunday = (
            this_sunday
            + timedelta(days=7)
        )

        start_at = now

        end_at = datetime.combine(
            next_sunday,
            time.min,
            tzinfo=timezone,
        )

        return (
            start_at,
            end_at,
            "本週",
        )

    # --------------------------------------------------
    # 4. 下週
    #
    # 查下一個 Sunday 00:00
    # 到再下一個 Sunday 00:00。
    # --------------------------------------------------

    if "下週" in order:
        this_sunday = _get_this_sunday(
            now
        )

        next_sunday = (
            this_sunday
            + timedelta(days=7)
        )

        following_sunday = (
            next_sunday
            + timedelta(days=7)
        )

        start_at = datetime.combine(
            next_sunday,
            time.min,
            tzinfo=timezone,
        )

        end_at = datetime.combine(
            following_sunday,
            time.min,
            tzinfo=timezone,
        )

        return (
            start_at,
            end_at,
            "下週",
        )

    # --------------------------------------------------
    # 5. 9/27 或 9-27
    # 預設今年
    # --------------------------------------------------

    slash_date_match = re.search(
        r"(?<!\d)"
        r"(\d{1,2})"
        r"\s*[/\-]\s*"
        r"(\d{1,2})"
        r"(?!\d)",
        order,
    )

    if slash_date_match:
        month = int(
            slash_date_match.group(1)
        )

        day = int(
            slash_date_match.group(2)
        )

        try:
            target_date = now.date().replace(
                month=month,
                day=day,
            )

        except ValueError as exc:
            raise ValueError(
                f"無效日期：{month}/{day}"
            ) from exc

        if target_date < now.date():
            raise ValueError(
                "目前只支援查詢今天與未來行程。"
            )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label=f"{month}/{day}",
        )

    # --------------------------------------------------
    # 6. 9月27日 / 9月27號
    # 預設今年
    # --------------------------------------------------

    month_day_match = re.search(
        r"(\d{1,2})"
        r"\s*月\s*"
        r"(\d{1,2})"
        r"\s*[日號]",
        order,
    )

    if month_day_match:
        month = int(
            month_day_match.group(1)
        )

        day = int(
            month_day_match.group(2)
        )

        try:
            target_date = now.date().replace(
                month=month,
                day=day,
            )

        except ValueError as exc:
            raise ValueError(
                f"無效日期：{month}月{day}日"
            ) from exc

        if target_date < now.date():
            raise ValueError(
                "目前只支援查詢今天與未來行程。"
            )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label=f"{month}月{day}日",
        )

    # --------------------------------------------------
    # 7. 29號 / 29日
    # 預設本月
    # --------------------------------------------------

    day_match = re.search(
        r"(?<!\d)"
        r"(\d{1,2})"
        r"\s*[號日]",
        order,
    )

    if day_match:
        day = int(
            day_match.group(1)
        )

        try:
            target_date = now.date().replace(
                day=day
            )

        except ValueError as exc:
            raise ValueError(
                f"本月沒有 {day} 號。"
            ) from exc

        if target_date < now.date():
            raise ValueError(
                "這個日期已經過去了。"
            )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label=f"{day}號",
        )

    # --------------------------------------------------
    # 8. 週二 / 星期二 / 禮拜二
    #
    # 代表最近一個尚未過去的指定 weekday。
    #
    # 如果今天正好是週二，
    # 則查今天。
    # --------------------------------------------------

    weekday_match = re.search(
        r"(?:週|星期|禮拜)"
        r"([一二三四五六日天])",
        order,
    )

    if weekday_match:
        weekday_text = (
            weekday_match.group(1)
        )

        weekday = WEEKDAY_MAP[
            weekday_text
        ]

        target_date = (
            _get_upcoming_weekday_date(
                now=now,
                weekday=weekday,
            )
        )

        return _build_day_range(
            target_date=target_date,
            timezone=timezone,
            label=f"週{weekday_text}",
        )

    # --------------------------------------------------
    # 9. 沒有解析到日期
    #
    # 目前維持原本行為：
    # 預設今天。
    # --------------------------------------------------

    return _build_day_range(
        target_date=now.date(),
        timezone=timezone,
        label="今天",
    )


def _build_day_range(
    target_date,
    timezone,
    label: str,
) -> tuple[datetime, datetime, str]:
    """
    建立單日查詢區間：

    target date 00:00
    ~
    next date 00:00
    """

    start_at = datetime.combine(
        target_date,
        time.min,
        tzinfo=timezone,
    )

    next_date = (
        target_date
        + timedelta(days=1)
    )

    end_at = datetime.combine(
        next_date,
        time.min,
        tzinfo=timezone,
    )

    return (
        start_at,
        end_at,
        label,
    )


def _get_this_sunday(
    now: datetime,
):
    """
    找到目前 calendar week 的週日。

    Python weekday():
    Mon = 0
    Tue = 1
    ...
    Sun = 6

    我們的 week：
    Sun → Sat
    """

    days_since_sunday = (
        now.weekday() + 1
    ) % 7

    return (
        now.date()
        - timedelta(
            days=days_since_sunday
        )
    )


def _get_upcoming_weekday_date(
    now: datetime,
    weekday: int,
):
    """
    找最近一個尚未過去的 weekday。

    例如今天週四：

    查「週六」
    → 這週六

    查「週三」
    → 下一個週三

    今天如果就是週三：
    → 今天
    """

    days_ahead = (
        weekday - now.weekday()
    ) % 7

    return (
        now.date()
        + timedelta(
            days=days_ahead
        )
    )


def _get_next_weekday_date(
    now: datetime,
    weekday: int,
):
    """
    找「下一個 calendar week」中的 weekday。

    一週從 Sunday 開始。

    例如：
    下週日 → next Sunday
    下週一 → next Sunday + 1
    下週二 → next Sunday + 2
    """

    this_sunday = _get_this_sunday(
        now
    )

    next_sunday = (
        this_sunday
        + timedelta(days=7)
    )

    # Python weekday:
    # Monday=0 ... Sunday=6
    #
    # 轉成 Sunday based offset：
    #
    # Sunday -> 0
    # Monday -> 1
    # Tuesday -> 2
    # ...
    sunday_based_offset = (
        weekday + 1
    ) % 7

    return (
        next_sunday
        + timedelta(
            days=sunday_based_offset
        )
    )
