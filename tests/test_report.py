"""delivery/report.py 렌더링 단위 테스트."""

from datetime import date

from wiki_quiz.delivery.report import render_html, render_markdown
from wiki_quiz.quiz_generator import Concept, QuizQuestion, QuizSet


def _set(text="질문") -> QuizSet:
    q = QuizQuestion(question=text, choices=["a", "b", "c", "d"], answer_index=1,
                     explanation="해설", source="doc1")
    return QuizSet([q, q], [Concept("개념", "설명입니다")])


def test_html_has_concepts_and_quiz():
    html = render_html(_set(), date(2026, 10, 5))
    assert "핵심 개념" in html and "설명입니다" in html
    assert html.count('<details class="quiz">') == 2
    assert "정답: B" in html


def test_html_escapes_llm_text():
    html = render_html(_set("<script>x</script>"), date(2026, 10, 5))
    assert "<script>x</script>" not in html


def test_markdown_has_concepts_and_answer():
    md = render_markdown(_set(), date(2026, 10, 5))
    assert "## 핵심 개념" in md and "정답: B" in md


def test_plain_list_without_concepts_still_renders():
    q = _set()[0]
    assert "핵심 개념" not in render_html([q], date(2026, 10, 5))
