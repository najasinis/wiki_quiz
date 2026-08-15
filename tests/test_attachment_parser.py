"""attachment_parser.py 단위 테스트.

구현 후 fixture 파일(tests/fixtures/sample.pdf, sample.docx)을 추가해 실제
파싱 결과를 검증한다. 네트워크 호출은 monkeypatch로 `_download`를 대체해
로컬 fixture 바이트를 반환하도록 해서, 테스트가 실제 인터넷 접속 없이 돈다.
"""

from pathlib import Path

import wiki_quiz.attachment_parser as attachment_parser
from wiki_quiz.attachment_parser import parse_attachment

_FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_pdf_extracts_text(monkeypatch):
    raw = (_FIXTURES / "sample.pdf").read_bytes()
    monkeypatch.setattr(
        attachment_parser, "_download", lambda url, auth_token=None, trusted_host=None: raw
    )

    result = parse_attachment("https://example.com/files/sample.pdf", "sample.pdf")

    assert result is not None
    assert "Hello Outline Wiki Quiz PDF Fixture" in result.text


def test_parse_docx_extracts_text(monkeypatch):
    raw = (_FIXTURES / "sample.docx").read_bytes()
    monkeypatch.setattr(
        attachment_parser, "_download", lambda url, auth_token=None, trusted_host=None: raw
    )

    result = parse_attachment("https://example.com/files/sample.docx", "sample.docx")

    assert result is not None
    assert "Hello Outline Wiki Quiz DOCX Fixture" in result.text
    assert "두 번째 문단입니다." in result.text


def test_unsupported_extension_returns_none():
    # 지원하지 않는 확장자는 다운로드 자체를 시도하지 않고 바로 None을 반환해야 한다
    # (네트워크 호출 없이 이 테스트가 통과해야 정상).
    result = parse_attachment("https://example.com/files/archive.zip", "archive.zip")
    assert result is None


def test_infer_extension_from_name_with_query_string():
    ext = attachment_parser._infer_extension(
        "spec.pdf", "https://example.com/files/abc123?token=xyz"
    )
    assert ext == "pdf"


def test_infer_extension_falls_back_to_url_path():
    ext = attachment_parser._infer_extension("", "https://example.com/files/report.docx?x=1")
    assert ext == "docx"


def test_download_sends_auth_header_only_to_trusted_host(monkeypatch):
    """보안 회귀 테스트: trusted_host와 일치하는 도메인에만 Authorization 헤더를 보낸다.

    배경: 위키 본문에서 추출한 첨부파일 링크는 제3자 도메인일 수 있어서, 인증 토큰을
    무조건 실어 보내면 위키에 외부 링크 한 줄만 심어도 API 키가 유출될 수 있었다
    (실제로 발견되어 수정된 문제 — README/코드 주석 참고).
    """
    captured = {}

    class FakeResponse:
        content = b"fake-bytes"

        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(attachment_parser.httpx, "Client", FakeClient)

    # 신뢰 도메인과 일치 -> 인증 헤더 O
    attachment_parser._download(
        "https://wiki.class.day/api/attachments/1/spec.pdf",
        auth_token="secret-key",
        trusted_host="wiki.class.day",
    )
    assert captured["headers"] == {"Authorization": "Bearer secret-key"}

    # 신뢰 도메인과 불일치 -> 인증 헤더 X (키 유출 방지)
    attachment_parser._download(
        "https://attacker.example/x.pdf",
        auth_token="secret-key",
        trusted_host="wiki.class.day",
    )
    assert captured["headers"] is None
