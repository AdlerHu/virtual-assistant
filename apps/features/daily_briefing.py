from apps.features.schedule import (
    get_today_schedule,
)
from apps.services.time_service import (
    get_user_timezone,
    now_local,
)


WEEKDAYS = [
    "星期一",
    "星期二",
    "星期三",
    "星期四",
    "星期五",
    "星期六",
    "星期日",
]


def daily_briefing(
    chat_id: int,
    db,
) -> str:
    timezone_name = get_user_timezone(
        db=db,
        chat_id=chat_id,
    )

    now = now_local(timezone_name)

    weekday = WEEKDAYS[
        now.weekday()
    ]

    date_text = (
        f"{now:%Y/%m/%d} "
        f"{weekday}"
    )

    schedule_text = get_today_schedule(
        chat_id=chat_id,
        db=db,
    )

    return (
        f"今天是 {date_text}\n\n"
        f"今天預定行程如下：\n"
        f"{schedule_text}"
    )
