"""wiki_quiz.retry 단위 테스트 — 재시도 대상 판별 로직만 검증한다.

실제로 여러 번 재시도되는 동작까지 테스트하면 tenacity의 지수 백오프 대기 시간(최소
1초)이 계속 누적돼 유닛 테스트 스위트가 느려진다. "429/일시적 오류만 재시도 대상으로
판별하는가"와 "그 판별 결과대로 post_with_retry가 동작하는가"만 확인하고, 실제
재시도·대기 메커니즘 자체는 tenacity 라이브러리 영역이라 여기서 다시 검증하지 않는다.
"""

import smtplib
from unittest.mock import MagicMock

import httpx
import pytest

from wiki_quiz.retry import is_rate_limited, is_transient_smtp_error, post_with_retry


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://example.com/webhook")
    response = httpx.Response(status_code, request=request)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        response.raise_for_status()
    return exc_info.value


def test_is_rate_limited_true_only_for_429():
    assert is_rate_limited(_http_status_error(429)) is True
    assert is_rate_limited(_http_status_error(404)) is False
    assert is_rate_limited(_http_status_error(500)) is False
    assert is_rate_limited(RuntimeError("무관한 예외")) is False


def test_is_transient_smtp_error_only_for_connection_issues():
    assert is_transient_smtp_error(smtplib.SMTPConnectError(421, "연결 실패")) is True
    assert is_transient_smtp_error(smtplib.SMTPServerDisconnected()) is True
    assert is_transient_smtp_error(TimeoutError()) is True
    # 인증 실패는 재시도해도 다시 실패할 비일시적 오류라 대상에서 제외돼야 한다.
    assert is_transient_smtp_error(smtplib.SMTPAuthenticationError(535, "인증 실패")) is False


def test_post_with_retry_returns_response_on_success():
    client = MagicMock()
    client.post.return_value = httpx.Response(200, request=httpx.Request("POST", "https://x"))

    resp = post_with_retry(client, "https://x", json={"a": 1})

    assert resp.status_code == 200
    client.post.assert_called_once_with("https://x", json={"a": 1})


def test_post_with_retry_raises_immediately_on_non_429_error():
    client = MagicMock()
    client.post.return_value = httpx.Response(403, request=httpx.Request("POST", "https://x"))

    with pytest.raises(httpx.HTTPStatusError):
        post_with_retry(client, "https://x")

    # 403은 재시도 대상이 아니므로 딱 한 번만 호출돼야 한다(재시도로 시간 낭비 없음).
    assert client.post.call_count == 1
