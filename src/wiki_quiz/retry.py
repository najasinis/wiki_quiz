"""
delivery 모듈들이 공통으로 쓰는 재시도 정책.

원래 outline_client.py에만 429(Too Many Requests) 지수 백오프 재시도가 있었고,
delivery/outline_document.py·slack.py·discord.py·google_chat.py는 httpx 호출이
한 번 실패하면 바로 예외를 던지고 끝났다(REVIEW_2026-08-22.md 3번 항목). 그 정책을
여기로 뽑아내 delivery 모듈들도 재사용한다.

인증 오류(401/403) 같은 비일시적 오류까지 최대 6회(최대 약 63초) 재시도하며 시간을
낭비하지 않도록, 429 응답에 대해서만 재시도한다 — outline_client.py의 기존 판단
기준을 그대로 따름.

주의: 재시도는 반드시 "요청 하나" 단위로 걸어야 한다. slack.py/google_chat.py처럼
한 번의 deliver() 호출 안에서 메시지를 두 번(문제/정답) 나눠 보내는 경우, deliver()
전체를 재시도하면 첫 메시지가 이미 성공했는데 두 번째 메시지의 429 때문에 첫
메시지가 채널에 중복으로 다시 올라갈 수 있다. 그래서 `post_with_retry`는 POST
호출 하나만 감싸도록 만들었다.
"""

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


http_retry = retry(
    retry=retry_if_exception(is_rate_limited),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)


@http_retry
def post_with_retry(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    """429일 때만 지수 백오프로 재시도하는 POST 한 번. 다른 4xx/5xx는 즉시 실패."""
    resp = client.post(url, **kwargs)
    resp.raise_for_status()
    return resp


def is_transient_smtp_error(exc: BaseException) -> bool:
    """SMTP 쪽 429에 해당하는 개념이 없어, 일시적 연결 오류로 판단되는 예외만 재시도한다.

    인증 실패(SMTPAuthenticationError)나 수신자 거부(SMTPRecipientsRefused) 같은
    비일시적 오류까지 재시도하면 시간만 버리므로 제외한다.
    """
    import smtplib

    return isinstance(
        exc,
        (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, ConnectionError),
    )


smtp_retry = retry(
    retry=retry_if_exception(is_transient_smtp_error),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)
