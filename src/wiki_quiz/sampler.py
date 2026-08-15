"""
3단계: 랜덤 샘플링

수집된 전체 텍스트 조각(블록·문단·첨부 청크) 중 무작위 표본을 뽑아
퀴즈 생성용 컨텍스트로 구성한다. 위키가 커질수록 청크 단위 샘플링이
토큰 비용을 억제하는 핵심 장치.
"""

import random
from dataclasses import dataclass

from wiki_quiz.attachment_parser import ParsedAttachment
from wiki_quiz.outline_client import WikiDocument


@dataclass
class TextChunk:
    source: str   # 문서 id 또는 첨부파일명 — 출처 추적용
    text: str


_DEFAULT_MAX_LEN = 500


def build_chunks(
    docs: list[WikiDocument],
    attachments: list[ParsedAttachment],
    max_len: int = _DEFAULT_MAX_LEN,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for d in docs:
        if d.text:
            chunks.extend(_split_into_chunks(d.text, max_len, source=d.document_id))
    for a in attachments:
        chunks.extend(_split_into_chunks(a.text, max_len, source=a.name))
    return chunks


def _split_into_chunks(text: str, max_len: int, source: str) -> list[TextChunk]:
    """텍스트를 문단(빈 줄) 단위로 모아 max_len에 가깝게 합치고, 조각을 만든다.

    문단 하나가 max_len보다 길면 강제로 잘라서라도 max_len을 넘지 않게 한다
    (첨부파일 안에 아주 긴 코드블록 등이 통째로 한 문단으로 들어오는 경우 대비).
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    merged: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}" if buf else para
        if buf and len(candidate) > max_len:
            merged.append(buf)
            buf = para
        else:
            buf = candidate
    if buf:
        merged.append(buf)

    chunks: list[TextChunk] = []
    for piece in merged:
        if len(piece) <= max_len:
            chunks.append(TextChunk(source=source, text=piece))
        else:
            for i in range(0, len(piece), max_len):
                chunks.append(TextChunk(source=source, text=piece[i : i + max_len]))
    return chunks


def sample_chunks(chunks: list[TextChunk], count: int, seed: int | None = None) -> list[TextChunk]:
    """
    SUDO:
      if len(chunks) <= count: return chunks
      rng = random.Random(seed)   # 매일 실행 시 seed=None (진짜 무작위)
      return rng.sample(chunks, count)
    """
    rng = random.Random(seed)
    if len(chunks) <= count:
        return chunks
    return rng.sample(chunks, count)
