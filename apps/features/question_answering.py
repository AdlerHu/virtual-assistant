from apps.services.ai_agent import client, Models
from apps.services.ai_agent import generate, Models


def question_answering(question: str) -> str:

    prompt = f"""
請直接回答使用者的問題。

問題：
{question}
"""

    response = generate(
        model=Models.QUESTION_ANSWERING,
        contents=prompt,
    )

    return response.text