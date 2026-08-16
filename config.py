"""환경변수 로드 및 파이프라인 전역 설정."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    outline_api_url: str
    outline_api_key: str
    # 둘 중 하나는 반드시 있어야 한다: root_collection_id면 컬렉션 전체를,
    # document_id면 그 문서(+하위 트리)만 순회한다. document_id가 우선한다.
    outline_root_collection_id: str | None
    outline_document_id: str | None

    quiz_provider: str  # "gemini" | "claude"
    anthropic_api_key: str | None  # QUIZ_PROVIDER=claude 일 때만 필요
    gemini_api_key: str | None     # QUIZ_PROVIDER=gemini 일 때만 필요
    quiz_model: str

    sample_chunk_count: int
    question_count: int

    delivery_mode: str  # "outline" | "slack" | "email" | "cli"

    # delivery별 부가 설정 (선택)
    outline_quiz_log_collection_id: str | None
    slack_webhook_url: str | None
    smtp_host: str | None
    smtp_port: int | None
    smtp_user: str | None
    smtp_app_password: str | None
    email_to: str | None


def load_config() -> Config:
    # SUDO: 필수 값 누락 시 명시적으로 에러 던지기 (조용히 None으로 두지 않기)
    root_collection_id = os.environ.get("OUTLINE_ROOT_COLLECTION_ID")
    document_id = os.environ.get("OUTLINE_DOCUMENT_ID")
    if not root_collection_id and not document_id:
        raise KeyError(
            "OUTLINE_ROOT_COLLECTION_ID 또는 OUTLINE_DOCUMENT_ID 중 하나는 반드시 설정해야 합니다."
        )

    # `or "gemini"`: GitHub Actions에서 vars.QUIZ_PROVIDER 미설정 시 빈 문자열이 주입되는데,
    # os.environ.get(key, default)는 키가 존재하면(빈 값이어도) default를 적용하지 않으므로
    # 명시적으로 빈 문자열도 걸러낸다.
    quiz_provider = os.environ.get("QUIZ_PROVIDER") or "gemini"
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if quiz_provider == "claude" and not anthropic_api_key:
        raise KeyError("QUIZ_PROVIDER=claude 인데 ANTHROPIC_API_KEY가 설정되지 않았습니다.")
    if quiz_provider == "gemini" and not gemini_api_key:
        raise KeyError("QUIZ_PROVIDER=gemini 인데 GEMINI_API_KEY가 설정되지 않았습니다.")

    return Config(
        outline_api_url=os.environ["OUTLINE_API_URL"],
        outline_api_key=os.environ["OUTLINE_API_KEY"],
        outline_root_collection_id=root_collection_id,
        outline_document_id=document_id,
        quiz_provider=quiz_provider,
        anthropic_api_key=anthropic_api_key,
        gemini_api_key=gemini_api_key,
        quiz_model=os.environ.get("QUIZ_MODEL") or (
            "gemini-3.5-flash-lite" if quiz_provider == "gemini" else "claude-haiku-4-5"
        ),
        sample_chunk_count=int(os.environ.get("SAMPLE_CHUNK_COUNT", "15")),
        question_count=int(os.environ.get("QUESTION_COUNT", "3")),
        # QUIZ_PROVIDER와 같은 이유로 `or` 사용 — vars.DELIVERY_MODE 미설정 시 빈 문자열이
        # 주입되면 os.environ.get(key, default)는 기본값을 적용하지 않는다.
        delivery_mode=os.environ.get("DELIVERY_MODE") or "cli",
        outline_quiz_log_collection_id=os.environ.get("OUTLINE_QUIZ_LOG_COLLECTION_ID"),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        smtp_host=os.environ.get("SMTP_HOST"),
        smtp_port=int(os.environ["SMTP_PORT"]) if os.environ.get("SMTP_PORT") else None,
        smtp_user=os.environ.get("SMTP_USER"),
        smtp_app_password=os.environ.get("SMTP_APP_PASSWORD"),
        email_to=os.environ.get("EMAIL_TO"),
    )
