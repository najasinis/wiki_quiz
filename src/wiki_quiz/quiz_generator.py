"""
4단계: Claude API로 퀴즈 3문제 생성

기본 모델은 Haiku 4.5 (입력 $1 / 출력 $5 / MTok). 품질 이슈 발생 시
Sonnet 5 (입력 $3 / 출력 $15)로 config.QUIZ_MODEL만 바꿔 전환.
하루 3문제 워크로드는 어느 모델이든 월 비용이 사실상 무시할 수준.

구현 메모: 스켈레톤 NOTE에서 권장한 대로 `tool_choice`로 구조화 출력을 강제한다.
자유 텍스트 응답을 `json.loads`로 파싱하던 이전 방식은 모델이 JSON 앞뒤로 설명을
덧붙이면 파싱이 깨지기 쉬워서, tool_use 블록에서 바로 구조화된 값을 받는 방식으로
바꿨다.
"""

from dataclasses import dataclass

from anthropic import Anthropic

from wiki_quiz.sampler import TextChunk

QUIZ_SYSTEM_PROMPT = """\
너는 개발 위키 내용을 바탕으로 퀴즈를 출제하는 어시스턴트다.
주어진 텍스트 조각들만 근거로 사용하고, 조각에 없는 내용은 지어내지 마라.
"""

_SUBMIT_QUIZ_TOOL_NAME = "submit_quiz"

_SUBMIT_QUIZ_TOOL = {
    "name": _SUBMIT_QUIZ_TOOL_NAME,
    "description": "생성한 퀴즈 문제 목록을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "문제 지문"},
                        "choices": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 4,
                            "maxItems": 4,
                            "description": "4지선다 보기",
                        },
                        "answer_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3,
                            "description": "정답 보기의 0-based 인덱스",
                        },
                        "explanation": {"type": "string", "description": "정답 해설"},
                        "source": {"type": "string", "description": "근거로 쓰인 조각의 source 값"},
                    },
                    "required": ["question", "choices", "answer_index", "explanation", "source"],
                },
            }
        },
        "required": ["questions"],
    },
}


@dataclass
class QuizQuestion:
    question: str
    choices: list[str]     # 4지선다
    answer_index: int      # 0-based
    explanation: str
    source: str             # 근거가 된 chunk.source


def generate_quiz(
    chunks: list[TextChunk],
    question_count: int,
    model: str,
    api_key: str,
) -> list[QuizQuestion]:
    if not chunks:
        # 위키에서 아무 텍스트도 수집되지 않은 경우 (빈 위키, 전부 파싱 실패 등)
        return []

    client = Anthropic(api_key=api_key)
    context = _build_context(chunks)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=QUIZ_SYSTEM_PROMPT,
        tools=[_SUBMIT_QUIZ_TOOL],
        tool_choice={"type": "tool", "name": _SUBMIT_QUIZ_TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": (
                    f"{context}\n\n위 조각들에서만 근거를 사용해 {question_count}문제를 "
                    f"4지선다로 출제해줘. 반드시 {_SUBMIT_QUIZ_TOOL_NAME} 도구를 호출해서 제출해."
                ),
            }
        ],
    )

    return _parse_questions(response, question_count)


def _build_context(chunks: list[TextChunk]) -> str:
    return "\n\n".join(f"[{c.source}] {c.text}" for c in chunks)


def _parse_questions(response, question_count: int) -> list[QuizQuestion]:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _SUBMIT_QUIZ_TOOL_NAME:
            data = block.input.get("questions", [])
            return [QuizQuestion(**item) for item in data[:question_count]]
    raise RuntimeError(
        f"Claude 응답에서 '{_SUBMIT_QUIZ_TOOL_NAME}' tool_use 블록을 찾지 못했습니다: {response.content!r}"
    )
