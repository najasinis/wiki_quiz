"""delivery/google_chat.py 순수 로직(메시지 포맷) 단위 테스트."""

from wiki_quiz.delivery.google_chat import _format_answers, _format_questions
from wiki_quiz.quiz_generator import QuizQuestion


def _make_question(i: int) -> QuizQuestion:
    return QuizQuestion(
        question=f"질문{i}",
        choices=["보기A", "보기B", "보기C", "보기D"],
        answer_index=1,
        explanation=f"해설{i}",
        source=f"doc{i}",
    )


def test_format_questions_excludes_answers():
    questions = [_make_question(0)]

    text = _format_questions(questions)

    assert "질문0" in text
    assert "보기B" in text
    assert "해설0" not in text  # 정답/해설은 다음 메시지에서만 노출


def test_format_answers_includes_answer_and_explanation():
    questions = [_make_question(0)]

    text = _format_answers(questions)

    assert "보기B" in text  # answer_index=1 → B
    assert "해설0" in text
    assert "doc0" in text
