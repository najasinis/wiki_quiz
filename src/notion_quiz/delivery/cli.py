"""5-C. CLI 출력 — 가장 빠른 전달 방식, 전달 계층 없이 터미널에 바로 출력."""

from notion_quiz.quiz_generator import QuizQuestion


def deliver(questions: list[QuizQuestion]) -> None:
    for i, q in enumerate(questions, start=1):
        print(f"\nQ{i}. {q.question}")
        for j, choice in enumerate(q.choices):
            marker = "*" if j == q.answer_index else " "
            print(f"  [{marker}] {choice}")
        print(f"  해설: {q.explanation}")
        print(f"  출처: {q.source}")
