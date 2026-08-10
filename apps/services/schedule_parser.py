from datetime import datetime, time, timedelta
import re

from apps.services.time_service import (
    get_timezone,
    now_local,
)


def parse_schedule_range(
    order: str,
    timezone_name: str,
) -> tuple[datetime, datetime, str]:

    timezone = get_timezone(timezone_name)
    now = now_local(timezone_name)

    date_match = re.search(
        r"(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        order,
    )

    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))

        target_date = now.date().replace(
            month=month,
            day=day,
        )

        label = f"{month} 月 {day} 日"

    elif "後天" in order:
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
        tzinfo=timezone,
    )

    end_at = start_at + timedelta(days=1)

    return start_at, end_at, label