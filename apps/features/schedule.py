from apps.services.schedule_parser import parse_schedule_range


def check_schedule(
    order: str,
    chat_id: int,
    db,
) -> str:
    start_at, end_at, label = parse_schedule_range(order)

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
            "status": data.get("status", "scheduled"),
        })

    schedules.sort(
        key=lambda item: item["event_at"]
    )

    if not schedules:
        return f"{label}目前沒有安排任何行程。"

    lines = [f"{label}共有 {len(schedules)} 個行程："]

    for index, item in enumerate(schedules, start=1):
        event_time = item["event_at"].strftime("%H:%M")

        lines.append(
            f"{index}. {event_time}｜"
            f"{item['event_text']}"
        )

    return "\n".join(lines)