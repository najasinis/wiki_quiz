"""
5단계: 결과 전달

DELIVERY_MODE 설정값에 따라 notion / slack / email / cli 중 하나로 라우팅.
"""

from notion_quiz.quiz_generator import QuizQuestion


def deliver(mode: str, questions: list[QuizQuestion], config) -> None:
    """
    SUDO:
      match mode:
        case "notion": notion_page.deliver(questions, config)
        case "slack":  slack.deliver(questions, config)
        case "email":  email.deliver(questions, config)
        case "cli":    cli.deliver(questions)
        case _: raise ValueError(f"unknown DELIVERY_MODE: {mode}")
    """
    if mode == "notion":
        from notion_quiz.delivery import notion_page
        notion_page.deliver(questions, config)
    elif mode == "slack":
        from notion_quiz.delivery import slack
        slack.deliver(questions, config)
    elif mode == "email":
        from notion_quiz.delivery import email
        email.deliver(questions, config)
    elif mode == "cli":
        from notion_quiz.delivery import cli
        cli.deliver(questions)
    else:
        raise ValueError(f"unknown DELIVERY_MODE: {mode}")
