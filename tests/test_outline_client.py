"""outline_client.py 단위 테스트 (네트워크 호출 없이 순수 로직만 검증)."""

from wiki_quiz.outline_client import OutlineWikiCrawler


def test_extract_attachment_urls_filters_by_extension():
    text = (
        "본문입니다.\n\n"
        "![스크린샷](https://wiki.class.day/api/attachments/1/screenshot.png)\n\n"
        "참고자료: [스펙 문서](https://wiki.class.day/api/attachments/2/spec.pdf)\n\n"
        "관련 링크: [공식 문서](https://example.com/docs)\n\n"
        "[회의록](https://wiki.class.day/api/attachments/3/notes.docx?token=abc)"
    )

    urls = OutlineWikiCrawler._extract_attachment_urls(text)

    assert "https://wiki.class.day/api/attachments/2/spec.pdf" in urls
    assert "https://wiki.class.day/api/attachments/3/notes.docx?token=abc" in urls
    assert not any(u.endswith(".png") for u in urls)
    assert not any("example.com/docs" in u for u in urls)


def test_extract_attachment_urls_returns_empty_for_no_text():
    assert OutlineWikiCrawler._extract_attachment_urls("") == []
    assert OutlineWikiCrawler._extract_attachment_urls(None) == []
