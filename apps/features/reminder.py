from apps.services.reminder_parser import parse_reminder
from apps.services.task_queue import create_reminder_task


def reminder(order: str, chat_id: int):
    reminder_data = parse_reminder(order)

    create_reminder_task(
        chat_id=chat_id,
        reminder_text=reminder_data["reminder_text"],
        scheduled_at=reminder_data["scheduled_at"],
    )

    return (
        f"已設定提醒：\n"
        f"{reminder_data['scheduled_at'].strftime('%Y-%m-%d %H:%M')}\n"
        f"{reminder_data['reminder_text']}"
    )