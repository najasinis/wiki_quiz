# 실제 위키 연동 전 E2E 체크리스트 (Go-Live 전 최종 확인)

> 대상: `wiki-quiz`가 실제 `wiki.class.day` Outline 인스턴스에 처음 연동되기 전 마지막 검증 단계.
> README의 "실제 연동 전 확인 필요" 항목을 실행 가능한 체크리스트 + 스모크 테스트 스크립트로 정리한 것.

## 0. 왜 이 체크리스트가 필요한가

로컬 검증(모킹된 Outline/Claude API + pytest 13~14개)은 **로직이 스펙대로 동작하는지**만
확인했을 뿐, 아래 네 가지는 실제 `wiki.class.day` 응답을 봐야만 확정할 수 있는 사실이라
여전히 미검증 상태다.

1. 첨부파일 URL이 서명된 만료 URL인지, API 키 인증이 필요한 프록시 URL인지
2. Outline 레이트리밋(429) 실제 임계치
3. `wiki.class.day`에 대한 API 키 발급 권한 보유 여부
4. 한국어 PDF 텍스트 추출 시 깨짐 여부

이 문서는 이 항목들을 포함해 실 연동 전 확인해야 할 것들을, **AI/스크립트에 맡겨도 되는 것**과
**사람이 직접 판단·실행해야 하는 것**으로 나눠 정리한다.

## 세션에서 재검증한 사실 (참고)

이번 점검 세션에서 리포지토리 코드를 받아 직접 `pytest`를 재실행했다. README는 "13개 테스트
모두 통과"라고 적혀 있으나, 실제로는 **14개 테스트가 수집되어 14개 모두 통과**했다
(`test_attachment_parser.py`에 6개, `test_outline_client.py`에 2개, `test_sampler.py`에
6개 — 합 14개). 개수 표기가 사소하게 어긋나 있을 뿐 실패는 없었다. README의 "13개"는
업데이트가 필요해 보인다(사소한 문서 오기이며, 이 자체가 연동을 막는 문제는 아니다).

---

## 1. 구분 기준

| 구분 | 기준 |
|---|---|
| **자동화 가능 (AI/CI에 위임)** | 실제 자격증명 없이도 검증 가능하거나, 결과가 명확한 참/거짓으로 판정되거나, 되돌리기 쉬운 읽기 전용 호출 |
| **사람이 직접 확인 필요** | (a) 계정/조직 권한 문제라 AI가 대신할 수 없음, (b) 실제 자격증명을 AI 세션에 노출하면 안 됨(보안), (c) 육안 품질 판단이 필요함, (d) 실제 수신자에게 메시지가 발송되는 등 되돌리기 어려움, (e) 프로덕션 트래픽(레이트리밋)에 영향을 줄 수 있음 |

---

## 2. 사람이 먼저 준비해야 하는 것 (스크립트 실행 전 전제조건)

- [ ] `wiki.class.day`에 대한 Outline 관리자 권한 또는 API 키 발급 권한 확인 — **계정 문제라 AI가 대신할 수 없음**
- [ ] Settings → API Keys에서 API 키 발급, `.env`에 직접 입력 (`OUTLINE_API_URL`, `OUTLINE_API_KEY`) — **AI 세션에 실제 키 값을 붙여넣지 말 것**
- [ ] `ANTHROPIC_API_KEY` 발급 및 `.env`에 입력
- [ ] **테스트용으로 격리된 소규모 컬렉션 ID**를 `OUTLINE_ROOT_COLLECTION_ID`에 지정 — 처음부터 회사 전체 위키(인사/급여 등 민감 문서 포함 가능)를 대상으로 돌리지 말 것. 사람이 "이 컬렉션은 퀴즈 소스로 써도 괜찮다"고 판단한 범위만 지정
- [ ] `python3 --version` ≥ 3.10 확인 (낮으면 pyenv 등으로 교체)

이 단계는 전부 "AI가 봐서는 안 되는 값을 다루거나(API 키), 사람만 판단 가능한 범위 결정(어떤
문서를 퀴즈 소스로 쓸지)"이라 자동화 대상에서 제외한다.

---

## 3. 자동화 스모크 테스트 (AI가 작성 — 실행은 실제 키를 가진 사람이)

아래 스크립트는 **전체 크롤링/전체 퀴즈 생성/실제 발송을 하지 않는다.** 읽기 전용 최소 호출로
"연동이 되는가/안 되는가"만 빠르게 확인하는 용도다. `.env`를 채운 뒤 저장소 루트에서 실행:

```bash
python3 tests/e2e_smoke_test.py
```

스크립트 본문 (`tests/e2e_smoke_test.py`로 저장):

```python
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
```

이 스크립트가 확인하지 않는 것(의도적으로 제외 — 아래 4번, 5번에서 사람이 직접 확인):
전체 문서 트리 순회, 첨부파일 다운로드, 퀴즈 3문제 실제 생성, Slack/Email 실제 발송.
이 부분들은 되돌리기 어렵거나(실발송), 프로덕션 레이트리밋에 영향을 주거나(전체 크롤링),
육안 판단이 필요해서(품질) 스모크 테스트 범위에서 뺐다.

---

## 4. 실제 첫 실행 절차 (사람이 통제된 순서로 직접 실행)

1. **`DELIVERY_MODE=cli`로 먼저 실행** (터미널 출력만, 외부 발송 없음):
   ```bash
   export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
   python -m src.wiki_quiz.main
   ```
2. 실행 시간과 로그를 보고 문서 개수 대비 소요 시간을 확인 — 429가 발생하면 백오프 로그가
   찍히는지, 최종적으로 성공하는지 관찰.
3. 터미널에 출력된 퀴즈 3문제를 **육안으로 검수**: 질문/보기/정답/해설이 실제 위키 내용과
   부합하는지, 이상하게 지어낸 내용(hallucination)이 없는지 확인.
4. 문제없으면 `DELIVERY_MODE=slack` 또는 `email`로 전환하되, **실제 운영 채널/주소가 아닌
   테스트용 채널/본인 이메일로 먼저 1회** 보내서 포맷을 확인한 뒤에만 운영 채널로 전환.
5. 위 1~4가 모두 통과한 뒤에만 `.github/workflows/daily_quiz.yml`의 GitHub Secrets/Variables를
   등록하고 스케줄을 활성화 (cron은 최초 등록 순간부터 매일 자동 실행되므로, 이 시점 이전에
   반드시 수동 실행 검증을 마칠 것).

---

## 5. 체크리스트 표 (항목별 자동화 여부 / 담당 / 확인 방법)

| # | 항목 | 자동화 가능? | 담당 | 확인 방법 / 이유 |
|---|---|---|---|---|
| 1 | pytest 스위트 통과 | ✅ AI/CI | AI | 이번 세션에서 재실행, 14/14 통과 확인 완료 |
| 2 | Python 버전 ≥ 3.10 | ✅ AI/CI | AI 또는 사람 | 스모크 테스트 스크립트에 포함 |
| 3 | 필수 환경변수 존재 여부(값 노출 없이) | ✅ AI/CI | AI 또는 사람 | 스모크 테스트 스크립트에 포함 |
| 4 | Outline API 키 유효성 | ✅ 스크립트, 실행은 사람 | 사람 (키 보유자) | `auth.info` 호출 — AI 세션은 실제 키 없음 |
| 5 | 루트 컬렉션 접근 가능 여부 | ✅ 스크립트, 실행은 사람 | 사람 | `documents.list(limit=1)` — 전체 크롤링 없이 확인 |
| 6 | Anthropic API 키 유효성 | ✅ 스크립트, 실행은 사람 | 사람 | 최소 호출(`max_tokens=10`) |
| 7 | Outline API 키 발급 권한 자체 보유 여부 | ❌ 사람 전용 | 사람 | 계정/조직 권한 문제, 코드로 해결 불가 |
| 8 | 첨부파일 URL 인증 방식(presigned vs 프록시) | ❌ 사람 전용 | 사람 | 실제 첨부파일 1건을 다운로드해보고 `trusted_host` 매칭 시 200/403 여부 직접 확인 |
| 9 | 실제 레이트리밋(429) 임계치 | ❌ 사람 전용 | 사람 | 실제 첫 실행 시 로그로 관찰. AI가 반복 실행하며 임계치를 "찾아보는" 것은 프로덕션에 부담을 줄 수 있어 금지 |
| 10 | 한국어 PDF 텍스트 깨짐 여부 | ❌ 사람 전용 | 사람 | 실제 첫 실행 출력에서 육안 확인 |
| 11 | 생성된 퀴즈 내용의 사실 부합 여부(hallucination 체크) | ❌ 사람 전용 | 사람 | 품질 판단은 자동화 불가, 최소 1회분 육안 검수 |
| 12 | 크롤링 범위(`OUTLINE_ROOT_COLLECTION_ID`)에 민감 문서 포함 여부 | ❌ 사람 전용 | 사람 | 퀴즈로 전체 팀에 노출돼도 괜찮은 컬렉션인지 판단 — 정보보호 문제 |
| 13 | Slack/Email 첫 실 발송 확인 | ❌ 사람 전용 | 사람 | 되돌릴 수 없는 외부 발송이므로 테스트 채널로 먼저 확인 |
| 14 | GitHub Secrets/Variables 등록 | ❌ 사람 전용 | 사람 | 자격증명이므로 AI에게 값 노출 금지 |
| 15 | GitHub Actions cron 최종 활성화 | ❌ 사람 전용 | 사람 | 1~14 모두 통과 확인 후 최종 승인 |

---

## 6. 실패 시 대응 메모

- `auth.info` 401/403 → API 키 자체가 잘못됐거나 권한 부족 (7번 항목부터 재확인)
- `documents.list` 403 → 키는 유효하나 해당 컬렉션에 접근 권한 없음 → 컬렉션 ID 또는 팀 권한 확인
- 첨부파일 다운로드 401 (trusted_host 일치했는데도) → presigned URL 방식일 가능성, `_download`의
  인증 로직 재검토 필요 (README "확인 필요" 참고)
- 429 반복 발생 → `sample_chunk_count`를 낮추기보다, 크롤링 자체가 문서 트리 크기에 비례하므로
  루트 컬렉션 범위를 좁히는 것을 우선 검토

---

## 7. 이번 세션 재검증 결과 (2026-08-22)

체크리스트 3번의 자동화 가능 항목(1~3번 표 기준)까지 이 세션에서 재실행했다. `.env`가
저장소에 없어 실제 API 키가 필요한 항목(4번 이후)은 이 세션에서 확인 불가 — 의도된 경계선이다.

- **pytest 전체 스위트**: **21/21 통과**. 6번 항목 "세션에서 재검증한 사실"에는 14개로
  기록돼 있으나, 그 사이 `test_discord.py`, `test_google_chat.py`가 추가되어 현재는 21개.
  README/문서의 테스트 개수 표기 갱신 필요.
- **Python 버전**: `.venv` 기준 3.12.12로 3.10+ 요건 통과.
- **`tests/e2e_smoke_test.py`**: 저장소에 없어 3번 섹션 본문 그대로 파일 생성.
  실행 결과:
  ```
  [FAIL] 환경변수 존재 확인: 누락된 환경변수: ['OUTLINE_API_URL', 'OUTLINE_API_KEY', 'OUTLINE_ROOT_COLLECTION_ID', 'ANTHROPIC_API_KEY']
  [OK]   Python 버전 확인
  [FAIL] Outline API 키 유효성 (auth.info): 'OUTLINE_API_URL'
  [FAIL] 루트 컬렉션 접근 가능 여부: 'OUTLINE_API_URL'
  [FAIL] Anthropic API 키 유효성 (ping): 'ANTHROPIC_API_KEY'
  ```
  `.env`가 없어 4개 항목 모두 실패 — 실제 키가 이 세션에 없으므로 정상적으로 막힌 것.
  체크리스트가 명시한 "AI 세션에 실제 키 값을 노출하지 말 것" 원칙대로 동작한 결과.

**남은 절차**: 사람이 `.env`에 실제 키를 채운 뒤 본인 터미널에서
`python3 tests/e2e_smoke_test.py`를 실행해 4~6번 항목(Outline 인증, 컬렉션 접근,
Anthropic 인증)을 확인하고, 통과하면 4장 "실제 첫 실행 절차"로 진행한다.
