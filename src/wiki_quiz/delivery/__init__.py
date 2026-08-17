"""
5단계: 결과 전달

DELIVERY_MODE 설정값에 따라 outline / slack / discord / google_chat / email / cli
중 하나로 라우팅.
"""

from wiki_quiz.quiz_generator import QuizQuestion


def deliver(mode: str, questions: list[QuizQuestion], config) -> None:
    """
    SUDO:
      match mode:
        case "outline":     outline_document.deliver(questions, config)
        case "slack":       slack.deliver(questions, config)
        case "discord":     discord.deliver(questions, config)
        case "google_chat": google_chat.deliver(questions, config)
        case "email":       email.deliver(questions, config)
        case "cli":         cli.deliver(questions)
        case _: raise ValueError(f"unknown DELIVERY_MODE: {mode}")
    """
    if mode == "outline":
        from wiki_quiz.delivery import outline_document
        outline_document.deliver(questions, config)
    elif mode == "slack":
        from wiki_quiz.delivery import slack
        slack.deliver(questions, config)
    elif mode == "discord":
        from wiki_quiz.delivery import discord
        discord.deliver(questions, config)
    elif mode == "google_chat":
        from wiki_quiz.delivery import google_chat
        google_chat.deliver(questions, config)
    elif mode == "email":
        from wiki_quiz.delivery import email
        email.deliver(questions, config)
    elif mode == "cli":
        from wiki_quiz.delivery import cli
        cli.deliver(questions)
    else:
        raise ValueError(f"unknown DELIVERY_MODE: {mode}")
