"""환경변수 로드 및 파이프라인 전역 설정."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    notion_api_key: str
    notion_root_page_id: str

    anthropic_api_key: str
    quiz_model: str

    sample_chunk_count: int
    question_count: int

    delivery_mode: str  # "notion" | "slack" | "email" | "cli"

    # delivery별 부가 설정 (선택)
    notion_quiz_log_parent_page_id: str | None
    slack_webhook_url: str | None
    smtp_host: str | None
    smtp_port: int | None
    smtp_user: str | None
    smtp_app_password: str | None
    email_to: str | None


def load_config() -> Config:
    # SUDO: 필수 값 누락 시 명시적으로 에러 던지기 (조용히 None으로 두지 않기)
    return Config(
        notion_api_key=os.environ["NOTION_API_KEY"],
        notion_root_page_id=os.environ["NOTION_ROOT_PAGE_ID"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        quiz_model=os.environ.get("QUIZ_MODEL", "claude-haiku-4-5"),
        sample_chunk_count=int(os.environ.get("SAMPLE_CHUNK_COUNT", "15")),
        question_count=int(os.environ.get("QUESTION_COUNT", "3")),
        delivery_mode=os.environ.get("DELIVERY_MODE", "cli"),
        notion_quiz_log_parent_page_id=os.environ.get("NOTION_QUIZ_LOG_PARENT_PAGE_ID"),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        smtp_host=os.environ.get("SMTP_HOST"),
        smtp_port=int(os.environ["SMTP_PORT"]) if os.environ.get("SMTP_PORT") else None,
        smtp_user=os.environ.get("SMTP_USER"),
        smtp_app_password=os.environ.get("SMTP_APP_PASSWORD"),
        email_to=os.environ.get("EMAIL_TO"),
    )
