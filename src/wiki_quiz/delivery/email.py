"""5-B. 이메일 발송 — 푸시처럼 습관화되나 SMTP + App Password 설정이 한 단계 더 필요."""

import smtplib
from datetime import date
from email.message import EmailMessage

from wiki_quiz.quiz_generator import QuizQuestion


def deliver(questions: list[QuizQuestion], config) -> None:
    if not questions:
        return

    missing = [
        name
        for name, value in (
            ("SMTP_HOST", config.smtp_host),
            ("SMTP_PORT", config.smtp_port),
            ("SMTP_USER", config.smtp_user),
            ("SMTP_APP_PASSWORD", config.smtp_app_password),
            ("EMAIL_TO", config.email_to),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"DELIVERY_MODE=email 이지만 다음 설정이 없습니다: {', '.join(missing)}")

    today = date.today().isoformat()
    msg = EmailMessage()
    msg["Subject"] = f"오늘의 위키 퀴즈 - {today}"
    msg["From"] = config.smtp_user
    msg["To"] = config.email_to
    msg.set_content(_format_plain_text(questions, today))

    with smtplib.SMTP(config.smtp_host, config.smtp_port) as s:
        s.starttls()
        s.login(config.smtp_user, config.smtp_app_password)
        s.send_message(msg)


def _format_plain_text(questions: list[QuizQuestion], today: str) -> str:
    lines = [f"오늘의 위키 퀴즈 - {today}", ""]
    for i, q in enumerate(questions, start=1):
        lines.append(f"Q{i}. {q.question}")
        for j, choice in enumerate(q.choices):
            marker = " (정답)" if j == q.answer_index else ""
            lines.append(f"  {chr(ord('A') + j)}. {choice}{marker}")
        lines.append(f"  해설: {q.explanation}")
        lines.append(f"  출처: {q.source}")
        lines.append("")
    return "\n".join(lines)
