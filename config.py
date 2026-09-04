"""환경변수 로드 및 파이프라인 전역 설정."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# 보안 고정값 (2026-09-05 사용자 확정): 이 위키에는 이 문서 하나만 퀴즈 소스로 써도
# 되고, 그 외 문서에는 민감 정보가 있어 절대 노출되면 안 된다. OUTLINE_DOCUMENT_ID가
# 이 값과 다르면(오타, 설정 실수, 다른 컬렉션으로 확장 등) 파이프라인을 아예 실행하지
# 않고 즉시 실패시킨다 — "설정 실수로 범위가 넓어지는 것"을 코드 레벨에서 막는 최후
# 방어선. 단, 이건 우리 코드가 실수로 다른 문서를 읽지 않게 막을 뿐, OUTLINE_API_KEY가
# 유출되어 이 코드를 거치지 않고 Outline API에 직접 호출되는 경우까지는 막지 못한다
# (그 경우를 막으려면 Outline 쪽에서 이 키의 소유 계정 자체가 다른 문서를 읽을 권한이
# 없도록 컬렉션을 restricted로 설정 + documents.add_user로 이 문서에만 권한을 부여해야
# 한다 — README/process.md 참고). 대상 문서를 의도적으로 바꾸려면 이 값도 함께 바꿀 것.
_ALLOWED_OUTLINE_DOCUMENT_ID = "mOuXpLufUA"


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

    delivery_mode: str  # "outline" | "slack" | "discord" | "google_chat" | "email" | "cli"

    # delivery별 부가 설정 (선택)
    outline_quiz_log_collection_id: str | None
    slack_webhook_url: str | None
    discord_webhook_url: str | None
    google_chat_webhook_url: str | None
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
    # 보안 고정값 검증: 위 _ALLOWED_OUTLINE_DOCUMENT_ID 주석 참고. 다른 문서/컬렉션으로
    # 범위가 넓어지는 설정 실수를 조용히 넘어가지 않고 여기서 바로 막는다.
    if document_id and document_id != _ALLOWED_OUTLINE_DOCUMENT_ID:
        raise ValueError(
            f"OUTLINE_DOCUMENT_ID({document_id!r})가 허용된 문서({_ALLOWED_OUTLINE_DOCUMENT_ID!r})와 "
            "다릅니다. 다른 위키 문서에는 민감 정보가 있어 의도적으로 이 문서만 허용하도록 "
            "고정해뒀습니다. 대상 문서를 실제로 바꾸려면 config.py의 "
            "_ALLOWED_OUTLINE_DOCUMENT_ID도 함께 수정해야 합니다."
        )
    if root_collection_id:
        raise ValueError(
            "OUTLINE_ROOT_COLLECTION_ID는 이 저장소에서 의도적으로 비활성화되어 있습니다 "
            "(컬렉션 전체 순회는 민감 문서 노출 위험이 있어 금지). OUTLINE_DOCUMENT_ID만 사용하세요."
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
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
        google_chat_webhook_url=os.environ.get("GOOGLE_CHAT_WEBHOOK_URL"),
        smtp_host=os.environ.get("SMTP_HOST"),
        smtp_port=int(os.environ["SMTP_PORT"]) if os.environ.get("SMTP_PORT") else None,
        smtp_user=os.environ.get("SMTP_USER"),
        smtp_app_password=os.environ.get("SMTP_APP_PASSWORD"),
        email_to=os.environ.get("EMAIL_TO"),
    )
