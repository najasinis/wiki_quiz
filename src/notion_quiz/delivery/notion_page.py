"""5-A. Notion 페이지 생성 — 위키와 같은 공간에 기록이 쌓임. 알림은 없음."""

from notion_client import Client

from notion_quiz.quiz_generator import QuizQuestion


def deliver(questions: list[QuizQuestion], config) -> None:
    """
    SUDO:
      client = Client(auth=config.notion_api_key)
      today = date.today().isoformat()
      children_blocks = [heading("오늘의 퀴즈 - " + today)]
      for i, q in enumerate(questions):
          children_blocks += question_to_blocks(q, i)
      client.pages.create(
          parent={"page_id": config.notion_quiz_log_parent_page_id},
          properties={"title": [...]},
          children=children_blocks,
      )
    """
    raise NotImplementedError
