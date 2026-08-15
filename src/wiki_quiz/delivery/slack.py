"""5-B. Slack 발송 — 푸시 알림처럼 와서 습관화하기 쉬움. Webhook 토큰 관리 필요.

구현 메모: Slack Incoming Webhook은 "스레드 답글"을 만드는 API를 제공하지 않는다
(스레드 답글은 chat.postMessage + thread_ts 조합이 필요하고, 이건 Bot 토큰이 있는
정식 Slack App이어야 한다). 그래서 이 스켈레톤이 요구한 "정답 스포일러 처리"는
완벽한 스레드 답글 대신, 문제 메시지와 정답/해설 메시지를 두 번의 별도 웹훅 호출로
나눠 보내는 절충안으로 구현했다. 진짜 스레드 답글이 필요하면 DELIVERY_MODE=slack을
Bot 토큰 기반 구현으로 교체해야 한다 (README "미결정 사항"에 기록).
"""

import httpx

from wiki_quiz.quiz_generator import QuizQuestion


def deliver(questions: list[QuizQuestion], config) -> None:
    if not questions:
        return
    if not config.slack_webhook_url:
        raise ValueError("DELIVERY_MODE=slack 이지만 SLACK_WEBHOOK_URL이 설정되지 않았습니다.")

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(config.slack_webhook_url, json={"text": _format_questions(questions)})
        resp.raise_for_status()

        # 정답 스포일러 방지를 위해 별도 메시지로 분리 발송 (진짜 스레드 답글 아님, 위 NOTE 참고)
        resp2 = client.post(config.slack_webhook_url, json={"text": _format_answers(questions)})
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
