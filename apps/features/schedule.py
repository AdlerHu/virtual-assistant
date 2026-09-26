from datetime import datetime, timedelta

from apps.services.schedule_parser import (
    parse_schedule_range,
)
from apps.services.time_service import (
    format_local,
    get_user_timezone,
    now_local,
)


def check_schedule(
    order: str,
    chat_id: int,
    db,
) -> str:
    """
    根據自然語言查詢指定日期或日期範圍內的行程。
    """

    timezone_name = get_user_timezone(
        db=db,
        chat_id=chat_id,
    )

    try:
        start_at, end_at, label = (
            parse_schedule_range(
                order=order,
                timezone_name=timezone_name,
            )
        )

    except ValueError as exc:
        return str(exc)

    return get_schedules(
        start_at=start_at,
        end_at=end_at,
        label=label,
        chat_id=chat_id,
        db=db,
        timezone_name=timezone_name,
    )


def get_today_schedule(
    chat_id: int,
    db,
) -> str:
    """
    查詢使用者今天的行程。
    不經過自然語言 parser。
    """

    timezone_name = get_user_timezone(
        db=db,
        chat_id=chat_id,
    )

    now = now_local(timezone_name)

    start_at = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    end_at = start_at + timedelta(
        days=1,
    )

    return get_schedules(
        start_at=start_at,
        end_at=end_at,
        label="今天",
        chat_id=chat_id,
        db=db,
        timezone_name=timezone_name,
    )


def get_schedules(
    start_at: datetime,
    end_at: datetime,
    label: str,
    chat_id: int,
    db,
    timezone_name: str,
) -> str:
    """
    查詢指定時間範圍內的行程。
    """

    docs = (
        db.collection("reminders")
        .where(
            "chat_id",
            "==",
            chat_id,
        )
        .where(
            "event_at",
            ">=",
            start_at,
        )
        .where(
            "event_at",
            "<",
            end_at,
        )
        .stream()
    )

    schedules = []

    for doc in docs:
        data = doc.to_dict()

        if (
            data.get("status")
            == "cancelled"
        ):
            continue

        event_at = data.get(
            "event_at"
        )

        event_text = data.get(
            "event_text"
        )

        if (
            event_at is None
            or not event_text
        ):
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
        key=lambda item:
            item["event_at"]
    )

    if not schedules:
        return (
            f"{label}目前沒有安排任何行程。"
        )

    lines = [
        f"{label}共有 "
        f"{len(schedules)} 個行程："
    ]

    is_multi_day = (
        end_at.date()
        - start_at.date()
    ).days > 1

    for index, item in enumerate(
        schedules,
        start=1,
    ):
        if is_multi_day:
            event_time = format_local(
                item["event_at"],
                timezone_name=timezone_name,
                fmt="%m/%d %H:%M",
            )

        else:
            event_time = format_local(
                item["event_at"],
                timezone_name=timezone_name,
                fmt="%H:%M",
            )

        lines.append(
            f"{index}. "
            f"{event_time}｜"
            f"{item['event_text']}"
        )

    return "\n".join(lines)
