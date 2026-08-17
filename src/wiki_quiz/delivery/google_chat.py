"""
5-E. Google Chat 발송 — Slack Incoming Webhook과 거의 동일한 JSON POST 방식이지만,
Google Chat 고유 기능인 `thread.threadKey`로 문제/정답 두 메시지를 같은 스레드로
묶어서 보낼 수 있다(Slack Incoming Webhook은 스레드 답글 자체가 불가능했던 것과
대비됨. README "설계상 결정한 사항" 참고).

구현 메모:
- Google Chat은 Discord의 스포일러(||텍스트||) 같은 "클릭해야 보이는 숨김 텍스트"
  문법을 지원하지 않는다(공식 서식 문서 확인 — 굵게/기울임/취소선/코드/목록/인용/
  링크/멘션은 지원하지만 스포일러는 없음). 그래서 Slack과 동일하게 문제 메시지와
  정답 메시지를 분리해서 보내되, threadKey로 같은 스레드에 묶어 최소한 대화가
  흩어지지 않게 했다.
- 웹훅 URL 자체에 `key`/`token` 인증 정보가 포함되는 구조라(Slack/Discord와 동일하게
  "URL 자체가 비밀"), 별도 Authorization 헤더가 필요 없다.
- 메시지 글자수 제한은 공식 문서에 명시되어 있지 않아(Discord의 2,000자처럼 확정된
  수치를 찾지 못함) Discord와 달리 별도 분할 로직은 넣지 않았다. 실제 사용 중
  오류(400 등)가 나면 이 부분을 재검토할 것.
"""

import httpx

from wiki_quiz.quiz_generator import QuizQuestion

# 문제/정답 메시지를 같은 스레드로 묶기 위한 고정 키. 매일 같은 값을 쓰면 어제
# 스레드에 계속 이어붙을 수 있어, 날짜를 섞어 하루 단위로 새 스레드를 만든다.
def _thread_key() -> str:
    from datetime import date

    return f"wiki-quiz-{date.today().isoformat()}"


def deliver(questions: list[QuizQuestion], config) -> None:
    if not questions:
        return
    if not config.google_chat_webhook_url:
        raise ValueError(
            "DELIVERY_MODE=google_chat 이지만 GOOGLE_CHAT_WEBHOOK_URL이 설정되지 않았습니다."
        )

    thread = {"threadKey": _thread_key()}
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            config.google_chat_webhook_url,
            json={"text": _format_questions(questions), "thread": thread},
        )
        resp.raise_for_status()

        resp2 = client.post(
            config.google_chat_webhook_url,
            json={"text": _format_answers(questions), "thread": thread},
        )
        resp2.raise_for_status()


def _format_questions(questions: list[QuizQuestion]) -> str:
    lines = ["*오늘의 위키 퀴즈* :bulb:"]
    for i, q in enumerate(questions, start=1):
        lines.append(f"\n*Q{i}. {q.question}*")
        for j, choice in enumerate(q.choices):
            letter = chr(ord("A") + j)
            lines.append(f"  {letter}. {choice}")
    lines.append("\n_정답과 해설은 바로 다음 메시지에서 확인하세요._")
    return "\n".join(lines)


def _format_answers(questions: list[QuizQuestion]) -> str:
    lines = ["*정답 및 해설*"]
    for i, q in enumerate(questions, start=1):
        letter = chr(ord("A") + q.answer_index)
        lines.append(f"\nQ{i} 정답: {letter}. {q.choices[q.answer_index]}")
        lines.append(f"해설: {q.explanation}")
        lines.append(f"출처: {q.source}")
    return "\n".join(lines)
