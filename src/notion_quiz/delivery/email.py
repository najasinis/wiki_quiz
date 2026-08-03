"""5-B. 이메일 발송 — 푸시처럼 습관화되나 SMTP + App Password 설정이 한 단계 더 필요."""

import smtplib
from email.message import EmailMessage

from notion_quiz.quiz_generator import QuizQuestion


def deliver(questions: list[QuizQuestion], config) -> None:
    """
    SUDO:
      body = format_as_plain_text(questions)
      msg = EmailMessage(); msg["Subject"] = "오늘의 위키 퀴즈"
      msg["From"] = config.smtp_user; msg["To"] = config.email_to
      msg.set_content(body)
      with smtplib.SMTP(config.smtp_host, config.smtp_port) as s:
          s.starttls()
          s.login(config.smtp_user, config.smtp_app_password)
          s.send_message(msg)
    """
    raise NotImplementedError
