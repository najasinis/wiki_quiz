"""
3단계: 랜덤 샘플링

수집된 전체 텍스트 조각(블록·문단·첨부 청크) 중 무작위 표본을 뽑아
퀴즈 생성용 컨텍스트로 구성한다. 위키가 커질수록 청크 단위 샘플링이
토큰 비용을 억제하는 핵심 장치.
"""

import random
from dataclasses import dataclass

from notion_quiz.attachment_parser import ParsedAttachment
from notion_quiz.notion_client import WikiBlock


@dataclass
class TextChunk:
    source: str   # 블록 id 또는 첨부파일명 — 출처 추적용
    text: str


def build_chunks(blocks: list[WikiBlock], attachments: list[ParsedAttachment]) -> list[TextChunk]:
    """
    SUDO:
      chunks = []
      for b in blocks where b.text:
          chunks.append(TextChunk(b.block_id, b.text))
      for a in attachments:
          chunks += split_into_chunks(a.text, max_len=500)  # 긴 첨부는 문단 단위로 쪼갬
      return chunks
    """
    raise NotImplementedError


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
