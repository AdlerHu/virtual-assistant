from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Taipei")


def parse_schedule_range(order: str) -> tuple[datetime, datetime, str]:
    now = datetime.now(TIMEZONE)

    if "後天" in order:
        target_date = now.date() + timedelta(days=2)
        label = "後天"

    elif "明天" in order:
        target_date = now.date() + timedelta(days=1)
        label = "明天"

    else:
        target_date = now.date()
        label = "今天"

    start_at = datetime.combine(
        target_date,
        time.min,
        tzinfo=TIMEZONE,
    )

    end_at = start_at + timedelta(days=1)

    return start_at, end_at, label