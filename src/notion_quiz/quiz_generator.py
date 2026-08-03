"""
4단계: Claude API로 퀴즈 3문제 생성

기본 모델은 Haiku 4.5 (입력 $1 / 출력 $5 / MTok). 품질 이슈 발생 시
Sonnet 5 (입력 $3 / 출력 $15)로 config.QUIZ_MODEL만 바꿔 전환.
하루 3문제 워크로드는 어느 모델이든 월 비용이 사실상 무시할 수준.
"""

import json
from dataclasses import dataclass

from anthropic import Anthropic

from notion_quiz.sampler import TextChunk

QUIZ_SYSTEM_PROMPT = """\
너는 개발 위키 내용을 바탕으로 퀴즈를 출제하는 어시스턴트다.
주어진 텍스트 조각들만 근거로 사용하고, 조각에 없는 내용은 지어내지 마라.
"""


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
    """
    SUDO:
      context = join(chunks, with source labels)
      user_prompt = f"다음 {len(chunks)}개 조각에서 랜덤하게 {question_count}문제를 출제해줘. JSON으로만 응답."
      response = anthropic_client.messages.create(
          model=model,
          system=QUIZ_SYSTEM_PROMPT,
          messages=[{"role": "user", "content": context + user_prompt}],
          tools=[QUIZ_JSON_SCHEMA],   # 구조화 출력 강제 (tool_choice)
      )
      questions = parse_tool_call_result(response)
      assert len(questions) == question_count
      return questions
    """
    client = Anthropic(api_key=api_key)
    context = _build_context(chunks)

    # NOTE: 실제 구현 시 tool_choice로 구조화 JSON 강제 권장 (아래는 뼈대만)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=QUIZ_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{context}\n\n위 조각들에서만 근거를 사용해 {question_count}문제를 "
                    f"4지선다로 출제해줘. JSON 배열로만 응답."
                ),
            }
        ],
    )

    raw_text = response.content[0].text  # SUDO: 실제로는 tool_use 블록에서 파싱
    return _parse_questions(raw_text)


def _build_context(chunks: list[TextChunk]) -> str:
    # SUDO: "\n\n".join(f"[{c.source}] {c.text}" for c in chunks)
    raise NotImplementedError


def _parse_questions(raw_text: str) -> list[QuizQuestion]:
    """
    SUDO:
      data = json.loads(raw_text)
      return [QuizQuestion(**item) for item in data]
    """
    data = json.loads(raw_text)
    return [QuizQuestion(**item) for item in data]
