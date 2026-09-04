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
