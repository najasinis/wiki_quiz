"""quiz_generator.py 단위 테스트 — LLM 호출은 전부 가짜로 치환, 실제 네트워크 호출 없음."""

from types import SimpleNamespace

import pytest

from wiki_quiz.quiz_generator import QuizQuestion, _build_context, _raise_if_gemini_blocked, generate_quiz
from wiki_quiz.sampler import TextChunk


def _sample_chunks():
    return [TextChunk(source="doc1", text="파이썬은 동적 타입 언어다.")]


def _sample_question_dict(n=1):
    return {
        "question": f"질문{n}",
        "choices": ["A", "B", "C", "D"],
        "answer_index": 0,
        "explanation": "해설",
        "source": "doc1",
    }


# ── 공통 로직 ────────────────────────────────────────────────────────

def test_build_context_joins_chunks_with_source_prefix():
    chunks = [TextChunk(source="doc1", text="가"), TextChunk(source="doc2", text="나")]
    assert _build_context(chunks) == "[doc1] 가\n\n[doc2] 나"


def test_generate_quiz_returns_empty_list_without_calling_provider_when_no_chunks():
    # provider가 실존하지 않는 값인데도 에러 없이 빈 리스트를 반환해야 한다 — 빈 조각일 때
    # provider 쪽 코드를 아예 타지 않고 조기 반환한다는 뜻.
    result = generate_quiz([], question_count=3, model="x", api_key="x", provider="no-such-provider")
    assert result == []


def test_generate_quiz_rejects_unknown_provider():
    with pytest.raises(ValueError, match="지원하지 않는 QUIZ_PROVIDER"):
        generate_quiz(_sample_chunks(), 1, "model", "key", provider="unknown")


# ── Claude ───────────────────────────────────────────────────────────

def test_generate_quiz_with_claude_happy_path(monkeypatch):
    tool_use_block = SimpleNamespace(
        type="tool_use",
        name="submit_quiz",
        input={"questions": [_sample_question_dict(1), _sample_question_dict(2)]},
    )
    fake_response = SimpleNamespace(content=[tool_use_block])

    class FakeMessages:
        def create(self, **kwargs):
            return fake_response

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeAnthropic)

    questions = generate_quiz(_sample_chunks(), question_count=1, model="claude-x", api_key="k", provider="claude")

    # question_count=1이므로 2개 중 1개로 잘려야 한다.
    assert len(questions) == 1
    assert isinstance(questions[0], QuizQuestion)
    assert questions[0].question == "질문1"


def test_generate_quiz_with_claude_raises_when_no_tool_use_block(monkeypatch):
    fake_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="답할 수 없습니다")])

    class FakeMessages:
        def create(self, **kwargs):
            return fake_response

    class FakeAnthropic:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeAnthropic)

    with pytest.raises(RuntimeError, match="tool_use"):
        generate_quiz(_sample_chunks(), 1, "claude-x", "k", provider="claude")


# ── Gemini ───────────────────────────────────────────────────────────

def _fake_gemini_response(questions_payload, finish_reason="STOP"):
    function_call = SimpleNamespace(name="submit_quiz", args={"questions": questions_payload})
    part = SimpleNamespace(function_call=function_call)
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=[part]),
        finish_reason=SimpleNamespace(name=finish_reason),
    )
    return SimpleNamespace(candidates=[candidate], prompt_feedback=None)


def test_generate_quiz_with_gemini_happy_path(monkeypatch):
    fake_response = _fake_gemini_response([_sample_question_dict(1)])

    class FakeModels:
        def generate_content(self, **kwargs):
            return fake_response

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)

    questions = generate_quiz(_sample_chunks(), 1, "gemini-x", "k", provider="gemini")

    assert len(questions) == 1
    assert questions[0].question == "질문1"


def test_generate_quiz_with_gemini_raises_when_no_function_call(monkeypatch):
    part = SimpleNamespace(function_call=None)
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]), finish_reason=SimpleNamespace(name="STOP"))
    fake_response = SimpleNamespace(candidates=[candidate], prompt_feedback=None)

    class FakeModels:
        def generate_content(self, **kwargs):
            return fake_response

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)

    with pytest.raises(RuntimeError, match="function_call"):
        generate_quiz(_sample_chunks(), 1, "gemini-x", "k", provider="gemini")


# ── Gemini 안전 필터 차단 (REVIEW_2026-08-22.md 3번 항목 회귀 테스트) ──────
#
# 안전 필터에 걸리면 candidates가 비거나 content.parts가 없을 수 있는데, 그대로 두면
# IndexError/TypeError로 죽어서 원인을 알기 어려웠다. _raise_if_gemini_blocked가
# 그 경우들을 먼저 사람이 읽을 수 있는 RuntimeError로 바꿔 던지는지 확인한다.

def test_raise_if_gemini_blocked_passes_normal_response():
    response = _fake_gemini_response([_sample_question_dict(1)])
    _raise_if_gemini_blocked(response)  # 예외 없이 통과해야 함


def test_raise_if_gemini_blocked_when_prompt_itself_blocked():
    response = SimpleNamespace(candidates=[], prompt_feedback=SimpleNamespace(block_reason="SAFETY"))
    with pytest.raises(RuntimeError, match="프롬프트 자체를 차단"):
        _raise_if_gemini_blocked(response)


def test_raise_if_gemini_blocked_when_no_candidates():
    response = SimpleNamespace(candidates=[], prompt_feedback=None)
    with pytest.raises(RuntimeError, match="후보 응답을 하나도 반환하지 않았습니다"):
        _raise_if_gemini_blocked(response)


def test_raise_if_gemini_blocked_when_finish_reason_is_safety():
    candidate = SimpleNamespace(content=None, finish_reason=SimpleNamespace(name="SAFETY"))
    response = SimpleNamespace(candidates=[candidate], prompt_feedback=None)
    with pytest.raises(RuntimeError, match="정상 종료되지 않았습니다"):
        _raise_if_gemini_blocked(response)


def test_raise_if_gemini_blocked_when_content_parts_empty():
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[]), finish_reason=SimpleNamespace(name="STOP"))
    response = SimpleNamespace(candidates=[candidate], prompt_feedback=None)
    with pytest.raises(RuntimeError, match="content.parts가 없습니다"):
        _raise_if_gemini_blocked(response)
