"""
2단계: 첨부파일 다운로드·파싱

Outline 문서 본문(Markdown) 안에는 PDF/Word/Markdown 파일이 텍스트가 아니라
링크(이미지/파일 URL)로만 임베드되어 있다. 여기서 파일을 받아
포맷별 라이브러리로 텍스트를 추출한다. Outline API가 대신 해주지 않는 구간.

※ 그 URL이 서명된 만료 URL(S3 presigned 등)인지, API 키 인증이 필요한 프록시 URL인지는
아직 미확인 — 구현 시점에 실제 응답을 보고 `_download`의 인증 처리 여부를 확정해야 한다
(README "미결정 사항" 참고).

구현 메모:
- 위 미확인 사항에 대한 임시 대응으로 `parse_attachment`/`_download`에 선택적
  `auth_token` 파라미터를 추가했다. 인증이 필요한 프록시 URL이라면 이 헤더로 바로
  동작할 가능성이 있다 — 다만 실제 Outline 인스턴스 응답으로 검증된 것은 아니므로
  최초 연동 시 반드시 재확인 필요.
- **보안 수정**: 위키 본문에서 추출한 첨부파일 링크는 도메인이 임의(제3자 사이트일
  수도 있음)이므로, `auth_token`을 무조건 실어 보내면 위키 편집 권한자가 문서에 외부
  링크를 심는 것만으로 API 키가 그 외부 서버로 유출될 수 있다. 그래서 `trusted_host`
  파라미터를 추가해, 다운로드할 URL의 host가 `trusted_host`(= Outline 인스턴스
  host)와 **일치할 때만** Authorization 헤더를 붙이도록 제한했다. 일치하지 않으면
  인증 헤더 없이 받는다(그래도 실패하면 해당 첨부파일만 건너뛴다).
- 지원하지 않는 확장자는 다운로드를 시도하지 않고 바로 None을 반환하도록 순서를
  바꿨다(불필요한 네트워크 호출 방지, 유닛 테스트도 네트워크 없이 가능).
- 한국어 PDF 텍스트 깨짐 여부는 실제 파일로 확인 전까지 미해결 상태로 남겨둔다
  (README "미결정 사항" 참고).
"""

import io
from dataclasses import dataclass
from urllib.parse import urlparse

import docx
import httpx
import pdfplumber

_SUPPORTED_EXTENSIONS = {"pdf", "docx", "doc", "md", "markdown"}


@dataclass
class ParsedAttachment:
    name: str
    text: str


def parse_attachment(
    url: str,
    name: str,
    auth_token: str | None = None,
    trusted_host: str | None = None,
) -> ParsedAttachment | None:
    ext = _infer_extension(name, url)
    if ext not in _SUPPORTED_EXTENSIONS:
        return None

    raw_bytes = _download(url, auth_token=auth_token, trusted_host=trusted_host)

    if ext == "pdf":
        text = _parse_pdf(raw_bytes)
    elif ext in ("docx", "doc"):
        text = _parse_docx(raw_bytes)
    else:  # md / markdown
        text = _parse_markdown(raw_bytes)

    return ParsedAttachment(name=name, text=text)


def _infer_extension(name: str, url: str) -> str:
    for candidate in (name, urlparse(url).path):
        if not candidate:
            continue
        stripped = candidate.rsplit("?", 1)[0].rsplit("#", 1)[0]
        if "." in stripped:
            ext = stripped.rsplit(".", 1)[-1].lower()
            if ext:
                return ext
    return ""


def _download(url: str, auth_token: str | None = None, trusted_host: str | None = None) -> bytes:
    # 보안: 다운로드할 URL의 host가 trusted_host(Outline 인스턴스 host)와 일치할 때만
    # 인증 헤더를 붙인다. 위키 본문에서 추출한 링크는 제3자 도메인일 수 있으므로,
    # 무조건 붙이면 위키에 외부 링크 한 줄만 심어도 API 키가 그쪽으로 유출된다.
    url_host = urlparse(url).netloc
    send_auth = bool(auth_token and trusted_host and url_host == trusted_host)
    headers = {"Authorization": f"Bearer {auth_token}"} if send_auth else None

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.content


def _parse_pdf(raw_bytes: bytes) -> str:
    """
    NOTE: 한국어 PDF의 경우 폰트 임베딩에 따라 텍스트 깨짐 가능 —
          추출 결과에 깨진 문자 비율 체크 로직 추가 검토 필요 (README "미결정 사항" 참고).
    """
    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _parse_docx(raw_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in document.paragraphs)


def _parse_markdown(raw_bytes: bytes) -> str:
    # LLM이 Markdown 문법을 그대로 이해할 수 있으므로 원본을 그대로 둔다.
    return raw_bytes.decode("utf-8", errors="replace")
