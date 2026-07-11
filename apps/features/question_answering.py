from google import genai
from google.genai import types
import os

PROJECT_ID = os.environ["PROJECT_ID"]

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global",
    http_options=types.HttpOptions(api_version="v1"),
)


def question_answering(question: str) -> str:

    prompt = f"""
請直接回答使用者的問題。

問題：
{question}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text