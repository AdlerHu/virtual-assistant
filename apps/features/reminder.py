from google.cloud import firestore

from apps.services.reminder_parser import (
    ParsedReminder,
    ReminderParseError,
    parse_reminders,
)
from apps.services.task_queue import create_reminder_task
from apps.services.time_service import (
    get_user_timezone,
    now_local,
    format_local,
)


MAX_REMINDERS_PER_REQUEST = 20


def reminder(order: str, chat_id: int, db) -> str:
    """
    建立一筆或多筆提醒。

    Args:
        order:
            Telegram 使用者的原始訊息。

        chat_id:
            Telegram chat ID。

        db:
            Firestore client。

    Returns:
        建立結果的 Telegram 回覆文字。
    """

    timezone_name = get_user_timezone(
        db=db,
        chat_id=chat_id,
    )

    try:
        parsed_reminders = parse_reminders(
            order=order,
            timezone_name=timezone_name,
        )

    except ReminderParseError as exc:
        print(f"Reminder parse error: {exc}")

        return (
            "我無法辨識提醒的時間或內容。\n"
            "請提供明確的日期、時間和事項。"
        )

    if len(parsed_reminders) > MAX_REMINDERS_PER_REQUEST:
        return (
            f"一次最多只能建立 "
            f"{MAX_REMINDERS_PER_REQUEST} 筆提醒。"
        )

    now = now_local(timezone_name)

    valid_reminders: list[ParsedReminder] = []
    expired_reminders: list[ParsedReminder] = []

    for item in parsed_reminders:
        if item.notify_at <= now:
            expired_reminders.append(item)
        else:
            valid_reminders.append(item)

    if not valid_reminders:
        return (
            "沒有建立提醒。\n"
            "辨識到的提醒時間都已經過去。"
        )

    created_reminders: list[ParsedReminder] = []
    failed_reminders: list[ParsedReminder] = []

    for item in valid_reminders:
        try:
            task_name = create_reminder_task(
                chat_id=chat_id,
                reminder_text=item.event_text,
                event_at=item.event_at,
                notify_at=item.notify_at,
            )

            db.collection("reminders").add({
                "chat_id": chat_id,
                "event_text": item.event_text,
                "event_at": item.event_at,
                "notify_at": item.notify_at,
                "timezone": timezone_name,
                "status": "scheduled",
                "task_name": task_name,
                "created_at": firestore.SERVER_TIMESTAMP,
            })

            created_reminders.append(item)

        except Exception as exc:
            print(
                "Failed to create reminder: "
                f"event_text={item.event_text!r}, "
                f"error={exc}"
            )

            failed_reminders.append(item)

    return _format_confirmation(
        created=created_reminders,
        expired=expired_reminders,
        failed=failed_reminders,
        timezone_name=timezone_name,
    )


def _format_confirmation(
    created: list[ParsedReminder],
    expired: list[ParsedReminder],
    failed: list[ParsedReminder],
    timezone_name: str,
) -> str:
    lines: list[str] = []

    if created:
        lines.append(f"已建立 {len(created)} 筆提醒：")

        for index, item in enumerate(created, start=1):
            event_at = format_local(
                item.event_at,
                timezone_name=timezone_name,
                fmt="%Y/%m/%d %H:%M",
            )

            notify_at = format_local(
                item.notify_at,
                timezone_name=timezone_name,
                fmt="%Y/%m/%d %H:%M",
            )

            if item.event_at == item.notify_at:
                lines.append(
                    f"{index}. {event_at}｜{item.event_text}"
                )
            else:
                lines.append(
                    f"{index}. {event_at}｜{item.event_text}\n"
                    f"   提醒時間：{notify_at}"
                )

    if expired:
        if lines:
            lines.append("")

        lines.append(
            f"略過 {len(expired)} 筆已經過期的提醒。"
        )

    if failed:
        if lines:
            lines.append("")

        lines.append(
            f"有 {len(failed)} 筆提醒建立失敗，"
            "請稍後重新設定。"
        )

    if not lines:
        return "沒有建立任何提醒。"

    return "\n".join(lines)