"""
5-D. Discord 발송 — Discord 공식 스포일러 문법(||텍스트||)을 지원해서, Slack처럼
메시지를 문제/정답 두 개로 쪼갤 필요 없이 한 메시지 안에서 정답만 가릴 수 있다
(클릭해야 보이는 방식. https://support.discord.com/hc/en-us/articles/360022320632).

구현 메모:
- Discord webhook의 `content` 필드는 2,000자 제한이 있다(Slack Incoming Webhook의
  훨씬 넉넉한 한도와 다름). 위키 내용에 따라 문제 3개 분량이 이 한도를 넘을 수 있어,
  문제 단위 블록으로 나눠 2,000자 안에서 최대한 한 메시지에 묶고, 넘치면 다음
  메시지로 이어 보내는 방어 로직을 넣었다. 문제 하나만으로도 2,000자를 넘는
  극단적인 경우엔 그 블록만 잘라서(truncate) 보낸다 — 통째로 실패하는 것보다는
  일부 손실을 감수하는 쪽을 택함.
- 스포일러 태그는 webhook으로 보낸 메시지도 일반 채널 메시지와 동일한 렌더러를
  타므로 그대로 동작한다(별도 API 옵션이 필요 없음).
"""

import httpx

from wiki_quiz.quiz_generator import QuizQuestion

_DISCORD_CONTENT_LIMIT = 2000
_HEADER = "**오늘의 위키 퀴즈** :bulb:\n"


def deliver(questions: list[QuizQuestion], config) -> None:
    if not questions:
        return
    if not config.discord_webhook_url:
        raise ValueError("DELIVERY_MODE=discord 이지만 DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")

    with httpx.Client(timeout=15.0) as client:
        for msg in _format_messages(questions):
            resp = client.post(config.discord_webhook_url, json={"content": msg})
            resp.raise_for_status()


def _format_messages(questions: list[QuizQuestion]) -> list[str]:
    """문제마다 블록을 만들고, 2,000자 한도 안에서 최대한 한 메시지에 묶는다.

    넘치면 새 메시지로 넘어가고, 그 메시지에도 헤더를 다시 붙인다(여러 메시지로
    쪼개져도 각 메시지가 맥락 없이 툭 튀어나오지 않도록).
    """
    block_limit = _DISCORD_CONTENT_LIMIT - len(_HEADER)
    blocks = [_truncate(_format_one(i, q), block_limit) for i, q in enumerate(questions, start=1)]

    messages: list[str] = []
    current = _HEADER
    for block in blocks:
        candidate = current + block
        if len(candidate) > _DISCORD_CONTENT_LIMIT and current != _HEADER:
            messages.append(current)
            current = _HEADER + block
        else:
            current = candidate
    if current.strip():
        messages.append(current)
    return messages


def _format_one(i: int, q: QuizQuestion) -> str:
    lines = [f"\n**Q{i}. {q.question}**"]
    for j, choice in enumerate(q.choices):
        lines.append(f"{chr(ord('A') + j)}. {choice}")
    letter = chr(ord("A") + q.answer_index)
    lines.append(f"||정답: {letter}. {q.choices[q.answer_index]} — {q.explanation} (출처: {q.source})||")
    return "\n".join(lines) + "\n"


def _truncate(block: str, limit: int) -> str:
    if len(block) <= limit:
        return block
    return block[: limit - 1] + "…"
