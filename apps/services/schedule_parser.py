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
    # --------------------------------------------------

    raise ValueError(
    "我無法辨識你想查詢的日期。"
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