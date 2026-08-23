"""
읽기 전용 스모크 테스트: 전체 크롤링/퀴즈 생성/실제 발송 없이
"연동 자체가 되는가"만 빠르게 확인한다. 실제 API 키가 담긴 .env가 필요하므로
AI 세션이 아니라 키를 보유한 사람이 직접 실행해야 한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

import httpx


def check(name, fn):
    try:
        fn()
        print(f"[OK]   {name}")
        return True
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False


def check_env_vars():
    required = ["OUTLINE_API_URL", "OUTLINE_API_KEY", "OUTLINE_ROOT_COLLECTION_ID", "ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"누락된 환경변수: {missing}")


def check_python_version():
    if sys.version_info < (3, 10):
        raise RuntimeError(f"Python 3.10+ 필요, 현재 {sys.version}")


def check_outline_auth():
    """Outline auth.info — 데이터를 건드리지 않고 API 키 유효성만 확인."""
    url = os.environ["OUTLINE_API_URL"].rstrip("/")
    key = os.environ["OUTLINE_API_KEY"]
    resp = httpx.post(
        f"{url}/auth.info",
        headers={"Authorization": f"Bearer {key}"},
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    print(f"       -> 인증된 사용자: {data.get('user', {}).get('name', '?')} / "
          f"팀: {data.get('team', {}).get('name', '?')}")


def check_root_collection_accessible():
    """documents.list를 딱 1페이지(limit=1)만 호출 — 전체 순회 없이 접근 가능 여부만 확인."""
    url = os.environ["OUTLINE_API_URL"].rstrip("/")
    key = os.environ["OUTLINE_API_KEY"]
    collection_id = os.environ["OUTLINE_ROOT_COLLECTION_ID"]
    resp = httpx.post(
        f"{url}/documents.list",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"collectionId": collection_id, "offset": 0, "limit": 1},
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    print(f"       -> 루트 컬렉션에서 문서 {len(data)}건 확인 (limit=1 샘플)")


def check_anthropic_auth():
    """max_tokens=10짜리 최소 호출로 키 유효성만 확인 (전체 퀴즈 생성 아님, 비용 무시 가능 수준)."""
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=os.environ.get("QUIZ_MODEL", "claude-haiku-4-5"),
        max_tokens=10,
        messages=[{"role": "user", "content": "ping"}],
    )
    print(f"       -> Claude 응답 수신 확인 (model={resp.model})")


if __name__ == "__main__":
    results = [
        check("환경변수 존재 확인", check_env_vars),
        check("Python 버전 확인", check_python_version),
        check("Outline API 키 유효성 (auth.info)", check_outline_auth),
        check("루트 컬렉션 접근 가능 여부 (documents.list, limit=1)", check_root_collection_accessible),
        check("Anthropic API 키 유효성 (ping)", check_anthropic_auth),
    ]
    print()
    if all(results):
        print("모든 스모크 테스트 통과. 아래 4단계(실제 첫 실행)로 진행 가능.")
        sys.exit(0)
    else:
        print("일부 항목 실패. 아래 5번 체크리스트 표에서 해당 실패 원인을 확인할 것.")
        sys.exit(1)
