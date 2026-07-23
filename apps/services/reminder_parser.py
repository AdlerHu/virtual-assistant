from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from google.genai import types

from apps.services.ai_agent import generate, Models


class ReminderData(BaseModel):
    reminder_text: str
    scheduled_at: str


def parse_reminder(order: str) -> dict:
    now = datetime.now(ZoneInfo("Asia/Taipei"))

    prompt = f"""
你是提醒事項解析器。

目前時間：
{now.isoformat()}

使用者時區：
Asia/Taipei

請解析以下使用者訊息：

{order}

你需要輸出：

1. reminder_text
   使用者到時間時應該被提醒做的事情。

2. scheduled_at
   ISO 8601 格式，必須包含 +08:00 時區。

例如：

輸入：
明天早上10點提醒我回信給 Agent

輸出概念：
reminder_text = 回信給 Agent
scheduled_at = 明天日期的 10:00:00+08:00
"""

    response = generate(
        model=Models.REMINDER_PARSER,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=ReminderData,
        ),
    )

    data = ReminderData.model_validate_json(response.order)

    scheduled_at = datetime.fromisoformat(
        data.scheduled_at
    )

    return {
        "reminder_text": data.reminder_text,
        "scheduled_at": scheduled_at,
    }