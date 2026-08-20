import json
import os
from datetime import datetime

from google.api_core.exceptions import NotFound
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

# PROJECT_ID = os.environ["PROJECT_ID"]
PROJECT_ID = 'skills-building-413521'

TASKS_LOCATION = os.environ.get(
    "TASKS_LOCATION",
    "asia-east1",
)

TASKS_QUEUE = os.environ.get(
    "TASKS_QUEUE",
    "remind-queue",
)

CLOUD_RUN_URL = os.environ["CLOUD_RUN_URL"].rstrip("/")

tasks_client = tasks_v2.CloudTasksClient()


def delete_reminder_task(
    task_name: str,
) -> None:
    """
    刪除既有的 Cloud Task。

    如果 task 已經不存在，
    視為已經成功刪除。
    """

    if not task_name:
        return

    try:
        tasks_client.delete_task(
            name=task_name
        )

    except NotFound:
        # Task 可能已經執行完畢，
        # 或先前已被刪除。
        pass


def create_reminder_task(
    *,
    chat_id: int,
    reminder_text: str,
    event_at: datetime,
    notify_at: datetime,
) -> str:
    """
    建立一筆 Cloud Task。

    Cloud Tasks 會在 notify_at 呼叫：
    POST /tasks/send-reminder
    """

    if event_at.tzinfo is None:
        raise ValueError(
            "event_at 必須是包含時區的 datetime。"
        )

    if notify_at.tzinfo is None:
        raise ValueError(
            "notify_at 必須是包含時區的 datetime。"
        )

    parent = tasks_client.queue_path(
        PROJECT_ID,
        TASKS_LOCATION,
        TASKS_QUEUE,
    )

    payload = {
        "chat_id": chat_id,
        "reminder_text": reminder_text,
        "event_at": event_at.isoformat(),
    }

    schedule_time = timestamp_pb2.Timestamp()
    schedule_time.FromDatetime(notify_at)

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": (
                f"{CLOUD_RUN_URL}"
                "/tasks/send-reminder"
            ),
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8"),
        },
        "schedule_time": schedule_time,
    }

    response = tasks_client.create_task(
        request={
            "parent": parent,
            "task": task,
        }
    )

    return response.name
