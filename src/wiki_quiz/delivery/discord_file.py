"""
5-D'. Discord 발송 (파일 첨부) — 개념 설명 + 퀴즈를 HTML 또는 Markdown 파일로 만들어
webhook에 첨부한다. 형식은 DISCORD_FILE_FORMAT(html|md, 기본 html).

Discord 모바일은 HTML 미리보기를 지원하지 않으므로, 다운로드해서 브라우저로 열어야 한다.
바로 읽기 편한 쪽을 원하면 md를 쓴다(Discord가 텍스트 미리보기를 보여줌).
"""

import json
from datetime import date

import httpx

from wiki_quiz.delivery.report import render_html, render_markdown
from wiki_quiz.quiz_generator import QuizQuestion
from wiki_quiz.retry import post_with_retry


def deliver(questions: list[QuizQuestion], config) -> None:
    if not questions:
        return
    if not config.discord_webhook_url:
        raise ValueError("DELIVERY_MODE=discord_file 이지만 DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")

    today = date.today()
    fmt = config.discord_file_format
    if fmt == "html":
        body, mime = render_html(questions, today), "text/html"
    elif fmt == "md":
        body, mime = render_markdown(questions, today), "text/markdown"
    else:
        raise ValueError(f"DISCORD_FILE_FORMAT은 html 또는 md여야 합니다 (현재: {fmt!r}).")

    payload = {"content": "**오늘의 위키 퀴즈** :bulb:", "allowed_mentions": {"parse": []}}
    with httpx.Client(timeout=30.0) as client:
        post_with_retry(
            client,
            config.discord_webhook_url,
            data={"payload_json": json.dumps(payload)},
            files={"files[0]": (f"wiki-quiz-{today.isoformat()}.{fmt}", body.encode("utf-8"), mime)},
        )
