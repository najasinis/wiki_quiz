"""5-B. Slack 발송 — 푸시 알림처럼 와서 습관화하기 쉬움. Webhook 토큰 관리 필요."""

import httpx

from notion_quiz.quiz_generator import QuizQuestion


def deliver(questions: list[QuizQuestion], config) -> None:
    """
    SUDO:
      text = format_as_slack_markdown(questions)  # 정답은 스포일러 처리(스레드 답글 등) 고려
      httpx.post(config.slack_webhook_url, json={"text": text})
    """
    raise NotImplementedError
