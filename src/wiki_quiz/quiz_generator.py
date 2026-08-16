"""
4단계: LLM API로 퀴즈 3문제 생성

두 provider를 지원한다 (QUIZ_PROVIDER 환경변수로 선택, 기본 "gemini"):
- gemini: Google Gemini API. `gemini-3.5-flash-lite` 등 무료 티어(분당/일당 요청 수 제한은
  있지만 과금 없음)로 사용 가능해 기본값으로 삼았다. API 키는 https://aistudio.google.com
  에서 발급. Gemini는 모델 세대 교체·구버전 폐기가 잦으므로(예: gemini-2.0-flash는
  2026-06-01 서비스 종료), QUIZ_MODEL로 지정한 모델이 404를 내면 Google AI Studio의
  최신 모델 목록에서 후속 모델명으로 갱신할 것.
- claude: Anthropic Claude API. 유료 종량제(Claude.ai Max 구독과는 별개 결제).
  품질이 더 필요하면 QUIZ_PROVIDER=claude 로 전환.

하루 3문제 워크로드는 어느 provider·모델이든 비용/무료한도 모두 사실상 무시할 수준.

구현 메모: 두 provider 모두 자유 텍스트 응답을 `json.loads`로 파싱하는 대신, 모델이
지원하는 "도구 호출(tool/function calling)"로 구조화 출력을 강제한다. 모델이 JSON
앞뒤로 설명을 덧붙이면 파싱이 깨지기 쉬운 문제를 막기 위함.
"""

from dataclasses import dataclass

from wiki_quiz.sampler import TextChunk

QUIZ_SYSTEM_PROMPT = """\
너는 개발 위키 내용을 바탕으로 퀴즈를 출제하는 어시스턴트다.
주어진 텍스트 조각들만 근거로 사용하고, 조각에 없는 내용은 지어내지 마라.
"""

_SUBMIT_QUIZ_TOOL_NAME = "submit_quiz"

# 두 provider(Anthropic tool / Gemini function declaration) 모두 이 스키마를 그대로 쓴다.
# 두 SDK가 요구하는 JSON Schema 형태가 사실상 동일해서 provider별로 따로 정의할 필요가 없다.
_QUIZ_INPUT_SCHEMA = {
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
    provider: str = "gemini",
) -> list[QuizQuestion]:
    if not chunks:
        # 위키에서 아무 텍스트도 수집되지 않은 경우 (빈 위키, 전부 파싱 실패 등)
        return []

    context = _build_context(chunks)
    user_prompt = (
        f"{context}\n\n위 조각들에서만 근거를 사용해 {question_count}문제를 "
        f"4지선다로 출제해줘. 반드시 {_SUBMIT_QUIZ_TOOL_NAME} 도구를 호출해서 제출해."
    )

    if provider == "claude":
        data = _generate_with_claude(user_prompt, model, api_key)
    elif provider == "gemini":
        data = _generate_with_gemini(user_prompt, model, api_key)
    else:
        raise ValueError(f"지원하지 않는 QUIZ_PROVIDER: {provider!r} (claude 또는 gemini만 가능)")

    return [QuizQuestion(**item) for item in data[:question_count]]


def _build_context(chunks: list[TextChunk]) -> str:
    return "\n\n".join(f"[{c.source}] {c.text}" for c in chunks)


# ── Claude (Anthropic) ──────────────────────────────────────────────

def _generate_with_claude(user_prompt: str, model: str, api_key: str) -> list[dict]:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    tool = {
        "name": _SUBMIT_QUIZ_TOOL_NAME,
        "description": "생성한 퀴즈 문제 목록을 제출한다.",
        "input_schema": _QUIZ_INPUT_SCHEMA,
    }

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=QUIZ_SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": _SUBMIT_QUIZ_TOOL_NAME},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _SUBMIT_QUIZ_TOOL_NAME:
            return block.input.get("questions", [])
    raise RuntimeError(
        f"Claude 응답에서 '{_SUBMIT_QUIZ_TOOL_NAME}' tool_use 블록을 찾지 못했습니다: {response.content!r}"
    )


# ── Gemini (Google) ─────────────────────────────────────────────────

def _generate_with_gemini(user_prompt: str, model: str, api_key: str) -> list[dict]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    submit_quiz_fn = types.FunctionDeclaration(
        name=_SUBMIT_QUIZ_TOOL_NAME,
        description="생성한 퀴즈 문제 목록을 제출한다.",
        parameters=_QUIZ_INPUT_SCHEMA,
    )

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=QUIZ_SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[submit_quiz_fn])],
            # ANY: 반드시 지정한 함수 중 하나를 호출하도록 강제 (자유 텍스트 응답 방지)
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY", allowed_function_names=[_SUBMIT_QUIZ_TOOL_NAME]
                )
            ),
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.function_call and part.function_call.name == _SUBMIT_QUIZ_TOOL_NAME:
            return dict(part.function_call.args).get("questions", [])
    raise RuntimeError(
        f"Gemini 응답에서 '{_SUBMIT_QUIZ_TOOL_NAME}' function_call을 찾지 못했습니다: {response!r}"
    )
