"""delivery/discord.py 순수 로직(메시지 조립·2,000자 분할) 단위 테스트."""

from wiki_quiz.delivery.discord import _DISCORD_CONTENT_LIMIT, _format_messages, _truncate
from wiki_quiz.quiz_generator import QuizQuestion


def _make_question(i: int, text_len: int = 20) -> QuizQuestion:
    return QuizQuestion(
        question=f"질문{i} " + ("가" * text_len),
        choices=["보기A", "보기B", "보기C", "보기D"],
        answer_index=0,
        explanation="해설 " + ("나" * text_len),
        source=f"doc{i}",
    )


def test_format_messages_fits_in_single_message_when_short():
    questions = [_make_question(i) for i in range(3)]

    messages = _format_messages(questions)

    assert len(messages) == 1
    assert all(len(m) <= _DISCORD_CONTENT_LIMIT for m in messages)


def test_format_messages_splits_when_exceeding_limit():
    # 문제 하나가 대략 (20*2 + 고정 텍스트)자 정도이므로, 충분히 많이 만들면
    # 2,000자 한도를 넘어 여러 메시지로 쪼개져야 한다.
    questions = [_make_question(i, text_len=200) for i in range(20)]

    messages = _format_messages(questions)

    assert len(messages) > 1
    assert all(len(m) <= _DISCORD_CONTENT_LIMIT for m in messages)


def test_format_messages_contains_spoiler_markers():
    questions = [_make_question(0)]

    messages = _format_messages(questions)

    assert "||" in messages[0]
    assert "정답" in messages[0]


def test_truncate_leaves_short_text_unchanged():
    assert _truncate("짧은 텍스트", limit=100) == "짧은 텍스트"


def test_truncate_cuts_long_text_to_limit():
    text = "가" * 50
    result = _truncate(text, limit=10)

    assert len(result) == 10
    assert result.endswith("…")
