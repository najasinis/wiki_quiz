"""5-A. Outline 문서 생성 — 위키와 같은 공간에 기록이 쌓임. 알림은 없음."""

from datetime import date

import httpx

from wiki_quiz.quiz_generator import QuizQuestion
from wiki_quiz.retry import post_with_retry


def deliver(questions: list[QuizQuestion], config) -> None:
    if not questions:
        return
    if not config.outline_quiz_log_collection_id:
        raise ValueError(
            "DELIVERY_MODE=outline 이지만 OUTLINE_QUIZ_LOG_COLLECTION_ID가 설정되지 않았습니다."
        )

    today = date.today().isoformat()
    title = f"오늘의 퀴즈 - {today}"
    body_md = f"# {title}\n\n{_questions_to_markdown(questions)}"

    with httpx.Client(timeout=30.0) as client:
        # Outline API 자체가 429를 낼 수 있어(outline_client.py와 동일한 인스턴스),
        # 429일 때만 지수 백오프로 재시도한다.
        post_with_retry(
            client,
            f"{config.outline_api_url}/documents.create",
            headers={
                "Authorization": f"Bearer {config.outline_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "text": body_md,
                "collectionId": config.outline_quiz_log_collection_id,
                "publish": True,
            },
        )


def _questions_to_markdown(questions: list[QuizQuestion]) -> str:
    lines = []
    for i, q in enumerate(questions, start=1):
        lines.append(f"## Q{i}. {q.question}\n")
        for j, choice in enumerate(q.choices):
            letter = chr(ord("A") + j)
            if j == q.answer_index:
                lines.append(f"- **{letter}. {choice}** ✅")
            else:
                lines.append(f"- {letter}. {choice}")
        lines.append(f"\n> 해설: {q.explanation}")
        lines.append(f"> 출처: {q.source}\n")
    return "\n".join(lines)
