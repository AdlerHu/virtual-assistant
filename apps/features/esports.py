from apps.services.schedule_parser import (
    parse_schedule_range,
)
from apps.services.time_service import (
    get_user_timezone,
    format_local,
)


ESPORTS_TYPES = {
    "lck": "LCK",
    "worlds": "Worlds",
}


def check_esports(
    order: str,
    chat_id: int,
    db,
) -> str:
    """
    查詢指定日期或日期範圍內，
    已建立提醒的 LOL 賽事。
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

    docs = (
        db.collection("auto_reminders")
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

    matches = []

    for doc in docs:
        data = doc.to_dict()

        match_type = data.get("type")

        # auto_reminders 未來可能有其他類型，
        # esports 只處理 LOL 賽事。
        if match_type not in ESPORTS_TYPES:
            continue

        if (
            data.get("status")
            == "cancelled"
        ):
            continue

        event_at = data.get(
            "event_at"
        )

        team1 = data.get(
            "team1"
        )

        team2 = data.get(
            "team2"
        )

        if (
            event_at is None
            or not team1
            or not team2
        ):
            continue

        matches.append({
            "event_at": event_at,
            "league": ESPORTS_TYPES[
                match_type
            ],
            "team1": team1,
            "team2": team2,
        })

    matches.sort(
        key=lambda item:
            item["event_at"]
    )

    if not matches:
        return (
            f"{label}沒有你關注的 LOL 比賽。"
        )

    lines = [
        f"{label}共有 "
        f"{len(matches)} 場你關注的 LOL 比賽："
    ]

    # 與 check_schedule 使用相同顯示邏輯
    is_multi_day = (
        end_at.date()
        - start_at.date()
    ).days > 1

    for index, item in enumerate(
        matches,
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
            f"{item['league']}｜"
            f"{item['team1']} vs "
            f"{item['team2']}"
        )

    return "\n".join(lines)