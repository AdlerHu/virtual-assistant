from apps.services.schedule_parser import parse_schedule_range
from apps.services.time_service import (
    get_user_timezone,
    format_local,
)


def check_schedule(
    order: str,
    chat_id: int,
    db,
) -> str:
    """
    查詢指定日期範圍內的行程。

    例如：
    - 我今天有什麼行程？
    - 我明天有什麼行程？
    - 我後天有什麼安排？
    """

    timezone_name = get_user_timezone(
        db=db,
        chat_id=chat_id,
    )

    start_at, end_at, label = parse_schedule_range(
        order=order,
        timezone_name=timezone_name,
    )

    docs = (
        db.collection("reminders")
        .where("chat_id", "==", chat_id)
        .where("event_at", ">=", start_at)
        .where("event_at", "<", end_at)
        .stream()
    )

    schedules = []

    for doc in docs:
        data = doc.to_dict()

        if data.get("status") == "cancelled":
            continue

        event_at = data.get("event_at")
        event_text = data.get("event_text")

        if event_at is None or not event_text:
            continue

        schedules.append({
            "event_at": event_at,
            "event_text": event_text,
            "status": data.get(
                "status",
                "scheduled",
            ),
        })

    schedules.sort(
        key=lambda item: item["event_at"]
    )

    if not schedules:
        return f"{label}目前沒有安排任何行程。"

    lines = [
        f"{label}共有 {len(schedules)} 個行程："
    ]

    for index, item in enumerate(
        schedules,
        start=1,
    ):
        event_time = format_local(
            item["event_at"],
            timezone_name=timezone_name,
            fmt="%H:%M",
        )

        lines.append(
            f"{index}. {event_time}｜"
            f"{item['event_text']}"
        )

    return "\n".join(lines)