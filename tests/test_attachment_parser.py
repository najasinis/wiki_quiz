"""attachment_parser.py 단위 테스트 스켈레톤 — 구현 후 fixture 파일 추가해서 채우기."""

import pytest

from notion_quiz.attachment_parser import parse_attachment


@pytest.mark.skip(reason="구현 전 스켈레톤 — _download/_parse_* 구현 후 활성화")
def test_parse_pdf_extracts_text():
    ...


@pytest.mark.skip(reason="구현 전 스켈레톤")
def test_parse_docx_extracts_text():
    ...


@pytest.mark.skip(reason="구현 전 스켈레톤")
def test_unsupported_extension_returns_none():
    ...
