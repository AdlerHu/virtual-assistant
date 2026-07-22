import json
import os

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2


PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = "asia-east1"
QUEUE = "reminder-queue"
CLOUD_RUN_URL = os.environ["CLOUD_RUN_URL"]


def create_reminder_task(
    chat_id: int,
    reminder_text: str,
    scheduled_at,
):
    client = tasks_v2.CloudTasksClient()

    parent = client.queue_path(
        PROJECT_ID,
        LOCATION,
        QUEUE,
    )

    payload = {
        "chat_id": chat_id,
        "reminder_text": reminder_text,
    }

    timestamp = timestamp_pb2.Timestamp()
    timestamp.FromDatetime(scheduled_at)

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{CLOUD_RUN_URL}/tasks/send-reminder",
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(payload).encode(),
        },
        "schedule_time": timestamp,
    }

    response = client.create_task(
        request={
            "parent": parent,
            "task": task,
        }
    )

    return response.name