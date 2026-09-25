"""config.py 단위 테스트 — 특히 허용된 문서 하나만 읽도록 고정한 보안 검증 로직.

배경: 이 위키에는 지정된 문서 하나(OUTLINE_DOCUMENT_ID="mOuXpLufUA") 외에 민감 정보가
있어, 그 외 문서/컬렉션 전체 순회는 코드 레벨에서 원천 차단하도록 고정했다
(2026-09-05 사용자 확정). 여기서 그 차단이 실제로 동작하는지 잠근다.
"""

import pytest

import config


def _set_required_env(monkeypatch, **overrides):
    """load_config()가 요구하는 최소 필수 환경변수를 세팅한다."""
    base = {
        "OUTLINE_API_URL": "https://wiki.class.day/api",
        "OUTLINE_API_KEY": "dummy-key",
        "GEMINI_API_KEY": "dummy-gemini-key",
    }
    base.update(overrides)
    for key, value in base.items():
        monkeypatch.setenv(key, value)


def test_allowed_document_id_passes(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA")

    cfg = config.load_config()

    assert cfg.outline_document_id == "mOuXpLufUA"


def test_wrong_document_id_is_rejected(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="some-other-doc-id")

    with pytest.raises(ValueError, match="허용된 문서"):
        config.load_config()


def test_root_collection_id_is_rejected_even_if_valid_looking(monkeypatch):
    """컬렉션 전체 순회는 민감 문서 노출 위험이 있어 완전히 금지되어 있어야 한다."""
    _set_required_env(monkeypatch, OUTLINE_ROOT_COLLECTION_ID="some-collection-id")
    monkeypatch.delenv("OUTLINE_DOCUMENT_ID", raising=False)

    with pytest.raises(ValueError, match="의도적으로 비활성화"):
        config.load_config()


def test_missing_both_document_and_collection_id_raises(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("OUTLINE_DOCUMENT_ID", raising=False)
    monkeypatch.delenv("OUTLINE_ROOT_COLLECTION_ID", raising=False)

    with pytest.raises(KeyError):
        config.load_config()


# ── quiz_provider / 기본값 (2026-09-05 Gemini 기본값 확정 이후 회귀 테스트) ──

def test_default_provider_is_gemini_when_unset(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA")
    monkeypatch.delenv("QUIZ_PROVIDER", raising=False)

    cfg = config.load_config()

    assert cfg.quiz_provider == "gemini"
    assert cfg.quiz_model == "gemini-3.5-flash-lite"


def test_empty_string_quiz_provider_falls_back_to_gemini(monkeypatch):
    """GitHub Actions는 vars.QUIZ_PROVIDER 미설정 시 빈 문자열을 주입한다 — os.environ.get의
    기본값은 키가 존재하면 안 먹으므로, 이 재현이 없으면 `or "gemini"` 폴백이 실은 빈
    문자열 앞에서 안 먹힌다는 걸 놓칠 수 있다."""
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA", QUIZ_PROVIDER="")

    cfg = config.load_config()

    assert cfg.quiz_provider == "gemini"


def test_gemini_provider_requires_gemini_key(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(KeyError):
        config.load_config()


def test_claude_provider_requires_anthropic_key(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA", QUIZ_PROVIDER="claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(KeyError):
        config.load_config()


def test_claude_provider_uses_claude_default_model(monkeypatch):
    _set_required_env(
        monkeypatch,
        OUTLINE_DOCUMENT_ID="mOuXpLufUA",
        QUIZ_PROVIDER="claude",
        ANTHROPIC_API_KEY="dummy-anthropic-key",
    )

    cfg = config.load_config()

    assert cfg.quiz_model == "claude-haiku-4-5"


# ── delivery_mode 기본값 ───────────────────────────────────────────────

def test_delivery_mode_defaults_to_cli(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA")
    monkeypatch.delenv("DELIVERY_MODE", raising=False)

    cfg = config.load_config()

    assert cfg.delivery_mode == "cli"


def test_empty_string_delivery_mode_falls_back_to_cli(monkeypatch):
    """QUIZ_PROVIDER와 같은 이유 — vars.DELIVERY_MODE 미설정 시 빈 문자열이 주입될 수 있다."""
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA", DELIVERY_MODE="")

    cfg = config.load_config()

    assert cfg.delivery_mode == "cli"


# ── 그 외 기본값/파싱 ────────────────────────────────────────────────────

def test_sample_chunk_count_and_question_count_have_defaults(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA")
    monkeypatch.delenv("SAMPLE_CHUNK_COUNT", raising=False)
    monkeypatch.delenv("QUESTION_COUNT", raising=False)

    cfg = config.load_config()

    assert cfg.sample_chunk_count == 15
    assert cfg.question_count == 3


def test_smtp_port_is_none_when_unset(monkeypatch):
    _set_required_env(monkeypatch, OUTLINE_DOCUMENT_ID="mOuXpLufUA")
    monkeypatch.delenv("SMTP_PORT", raising=False)

    cfg = config.load_config()

    assert cfg.smtp_port is None
