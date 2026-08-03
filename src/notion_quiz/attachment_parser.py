"""
2단계: 첨부파일 다운로드·파싱

Notion API는 PDF/Word/Markdown 블록에 대해 텍스트가 아니라
만료되는 다운로드 URL만 준다. 여기서 파일을 받아
포맷별 라이브러리로 텍스트를 추출한다. Notion API가 대신 해주지 않는 구간.
"""

from dataclasses import dataclass

import httpx


@dataclass
class ParsedAttachment:
    name: str
    text: str


def parse_attachment(url: str, name: str) -> ParsedAttachment | None:
    """
    SUDO:
      ext = infer_extension(name, url)
      raw_bytes = download(url)   # 만료 전에 즉시 다운로드
      if ext == "pdf":      text = parse_pdf(raw_bytes)
      elif ext == "docx":   text = parse_docx(raw_bytes)
      elif ext == "md":     text = parse_markdown(raw_bytes)
      else:                 return None  # 지원 안 하는 포맷은 스킵 (로그만 남김)
      return ParsedAttachment(name, text)
    """
    ext = _infer_extension(name, url)
    raw_bytes = _download(url)

    if ext == "pdf":
        text = _parse_pdf(raw_bytes)
    elif ext == "docx":
        text = _parse_docx(raw_bytes)
    elif ext == "md":
        text = _parse_markdown(raw_bytes)
    else:
        return None

    return ParsedAttachment(name=name, text=text)


def _infer_extension(name: str, url: str) -> str:
    # SUDO: name.split(".")[-1].lower(), url 쿼리스트링 제거 후 fallback
    raise NotImplementedError


def _download(url: str) -> bytes:
    # SUDO: httpx.get(url).content  (Notion 파일 URL은 인증 불필요, S3 presigned)
    raise NotImplementedError


def _parse_pdf(raw_bytes: bytes) -> str:
    """
    SUDO (pdfplumber 사용):
      with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
          return "\n".join(page.extract_text() or "" for page in pdf.pages)

    NOTE: 한국어 PDF의 경우 폰트 임베딩에 따라 텍스트 깨짐 가능 —
          추출 결과에 깨진 문자 비율 체크 로직 추가 검토 필요 (README "미결정 사항" 참고).
    """
    raise NotImplementedError


def _parse_docx(raw_bytes: bytes) -> str:
    """
    SUDO (python-docx 사용):
      doc = docx.Document(io.BytesIO(raw_bytes))
      return "\n".join(p.text for p in doc.paragraphs)
    """
    raise NotImplementedError


def _parse_markdown(raw_bytes: bytes) -> str:
    """
    SUDO:
      text = raw_bytes.decode("utf-8")
      return strip_markdown_syntax(text)  # 필요 시 원본 그대로 둬도 무방 (LLM이 md 이해 가능)
    """
    raise NotImplementedError
