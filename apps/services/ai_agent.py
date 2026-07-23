# apps/services/ai_agent.py

import os

from google import genai
from google.genai import types


PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "global")


_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=types.HttpOptions(api_version="v1"),
)


class Models:
    INTENT_ROUTER = "gemini-2.5-flash"
    QUESTION_ANSWERING = "gemini-2.5-flash"
    REMINDER_PARSER = "gemini-2.5-flash"
    TRANSLATION = "gemini-2.5-flash"
    ENGLISH_PRACTICE = "gemini-2.5-flash"


def generate(
    *,
    model: str,
    contents,
    config=None,
):
    return _client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )