from pydantic import BaseModel, Field
from google.genai import types

from apps.services.ai_agent import (
    Models,
    generate,
)


class FollowedTeamCommand(BaseModel):
    team: str = Field(
        min_length=1,
    )


def parse_followed_team(
    order: str,
) -> str:
    prompt = f"""
從使用者輸入中找出 LOL 電競隊伍名稱。

只回傳隊伍名稱縮寫或常用英文代號。

例如：
- 把 KT 加進關注隊伍
  → KT

- 世界賽關注 G2
  → G2

- 不要再關注 HLE
  → HLE

- LCK 不看 DK 了
  → DK

使用者輸入：
{order}
"""

    response = generate(
        model=Models.INTENT_ROUTER,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type=(
                "application/json"
            ),
            response_schema=FollowedTeamCommand,
        ),
    )

    parsed = FollowedTeamCommand.model_validate_json(
        response.text
    )

    return parsed.team.strip().lower()