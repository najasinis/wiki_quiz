# wiki-quiz 진행 상황

> 이 문서는 "우리가 해야 할 것 / 이때까지 한 것 / 남은 것"을 계속 갱신하며 추적하는
> 살아있는 문서다. `/process` 명령으로 자동 갱신된다(`.claude/commands/process.md` 참고).
> 세부 근거가 필요하면 `REVIEW_2026-08-22.md`(종합 점검 보고서), `tests/e2e_go_live_checklist.md`
> (실연동 전 체크리스트), `SECURITY_AND_COST_AUDIT.md`(보안·비용 전수조사, gitignore됨,
> 로컬 전용)를 참고.

마지막 갱신: 2026-09-30 · 커밋 `8916068` 기준

---

## 프로젝트가 뭔지 (한 줄)

Outline 위키 문서를 매일 순회해서 무작위로 뽑은 내용으로 Claude/Gemini에게 4지선다
퀴즈 3문제를 만들게 하고, Slack/Discord/Google Chat/이메일/Outline 문서 중 하나로
전달하는 GitHub Actions 기반 무서버 배치 파이프라인. DB 없음, 상태 저장 없음, 매일
처음부터 다시 실행.

---

## 결정된 것 (2026-09-05)

- **Gemini 무료 티어 계속 사용 확정.** 다만 위키 안에 이 파이프라인이 다뤄도 되는 문서는
  `mOuXpLufUA`(https://wiki.class.day/doc/...-mOuXpLufUA) **단 하나뿐이고, 그 외 문서에는
  민감 정보가 있어 절대 노출되면 안 된다**는 전제 하의 결정. → 아래 "문서 접근 범위 제한"으로
  코드 레벨 방어 추가.

## 지금 해야 할 순서 (사람 실행 — A→B→C 순서대로, D는 여유 될 때) ⚠️

배포 검증(A~C)과 Outline 권한 잠그기(D)를 하나의 순서로 정리한 것. A→B→C를 먼저
끝내서 "파이프라인이 실제로 도는가"부터 확인하고, D는 급하지 않으니 그다음에.

### A. 로컬에서 전체 파이프라인 검증
- [x] A-1-a. `.env` 파일 생성 + 비밀값 아닌 항목 채우기(`OUTLINE_DOCUMENT_ID=mOuXpLufUA`,
  `DELIVERY_MODE=discord`)는 AI가 완료(2026-09-30) — 이 값들은 이미 대화에 공개된 값이라
  AI가 직접 채울 수 있었음
- [ ] **A-1-b. 실제 비밀값 채우기 (사람만 가능)**: `OUTLINE_API_KEY`, `GEMINI_API_KEY`,
  `DISCORD_WEBHOOK_URL` — AI는 이 값들을 받은 적이 없어 채울 수 없음. `.env` 파일을
  열어서 이 3개만 채우면 됨(다른 항목은 이미 채워져 있음)
- [x] A-2. `pip install -r requirements.txt` — AI가 완료(2026-09-30), 8개 패키지 정상 설치 확인
- [x] A-3-예비검증. AI가 플레이스홀더 키로 먼저 실행해봄 — 0단계(Python 버전)/1단계
  (config 로드, 문서 ID 보안 고정 포함) 정상 통과, 2단계(Outline 인증)에서 가짜 키로
  인한 401까지 깔끔하게 도달 확인(2026-09-30). **이 과정에서 `.env.example` 버그를
  발견해 수정함**(커밋 `8916068` — 인라인 주석이 값으로 잘못 파싱되던 문제)
- [ ] **A-3. 진짜 실행 (사람만 가능)**: A-1-b 채운 뒤 `python3 tests/e2e_smoke_test.py`
  재실행 — 0~7단계 전부 `[OK]`인지 확인 (`[FAIL]` 뜨면 그 메시지 그대로 공유)
- [ ] A-4. 통과하면 `python3 tests/e2e_smoke_test.py --send`로 Discord에 실제 1회 전송,
      채널에서 도착 확인

### B. GitHub Secrets/Variables 등록 확인
- [x] B-1. `DISCORD_WEBHOOK_URL` Secret 등록 완료(2026-09-30, 스크린샷 확인)
- [x] B-2. `DELIVERY_MODE=discord` Variable 등록 완료(2026-09-30, 스크린샷 확인)

### C. GitHub Actions 실전 확인
- [x] C-1. Actions 탭 → Daily Wiki Quiz → **Run workflow** 수동 실행 완료(2026-09-30)
- [x] C-2. 워크플로 성공 (사용자 확인)
- [x] C-3. Discord `#일반` 채널에 "wiki_quiz" 앱 명의로 "오늘의 위키 퀴즈" 메시지 3문제
      도착 확인(스크린샷, 2026-09-30 01:54 KST) — 위키 실제 내용(Claude Code/OpenClaw,
      브라우저 저장소, 실시간 통신 방식) 기반 문제로 확인됨

**🎉 파이프라인 첫 완전 성공 기록: 2026-09-30.** Outline 문서 수집 → Gemini 퀴즈 생성
→ Discord 전달까지 전 구간이 실제 자격증명으로 처음 끝까지 성공. 단, 이 실행은
수동(`Run workflow`)이었고 cron(매일 KST 09:00) 자동 실행 성공은 아직 별도 확인 필요.

**⚠️ 확인 필요**: 캡처에서 정답이 스포일러(클릭 전 가림) 없이 바로 평문으로 보임 —
discord.py의 `||정답: ...||` 스포일러 태그가 의도대로 렌더링되는지 검증 필요
(사용자가 이미 클릭해서 열어본 상태였을 가능성도 있어 원인 미확정, 확인 중).

### D. Outline 권한 진짜 100% 잠그기 (급하지 않음, 여유될 때)
코드(`config.py`의 `_ALLOWED_OUTLINE_DOCUMENT_ID`)는 "우리 코드가 실수로 다른 문서를
안 읽는다"만 보장한다. `OUTLINE_API_KEY`가 유출돼 코드를 거치지 않고 Outline API에
직접 호출되면, 그 키의 소유 계정이 원래 읽을 수 있는 문서는 다 읽힌다. 크리덴셜
레벨 100% 보장을 원하면 Outline 쪽(전부 Outline 웹사이트에서):
- [ ] D-1. `mOuXpLufUA` 문서가 속한 컬렉션 확인
- [ ] D-2. 그 컬렉션을 "제한됨(restricted)"으로 설정 (팀 전체가 아니라 지정된 사람/계정만)
- [ ] D-3. 전용 계정 준비 (새 계정 만들거나, 다른 민감 컬렉션 권한 없는 기존 계정 사용)
- [ ] D-4. 그 문서 하나에만 D-3 계정에게 읽기 권한 부여 (문서의 공유/접근 관리 메뉴)
- [ ] D-5. D-3 계정으로 로그인해 새 API 키 발급 (범위: `documents.list documents.info`)
- [ ] D-6. GitHub Secrets → `OUTLINE_API_KEY` 값을 D-5에서 발급한 키로 교체 (Update)
      — **새 Secret을 만드는 게 아니라 기존 `OUTLINE_API_KEY` 값 자체를 덮어쓰는 것**
- [ ] D-7. 위 A-3(e2e 스모크 테스트) 다시 돌려서 여전히 정상 동작하는지 확인

Outline 관리자 화면이 어떻게 생겼는지 몰라서, D 시작할 때 화면 캡처 주면서 같이
단계별로 진행하는 게 정확함.

---

## 완료된 것 (타임라인)

| 날짜 | 커밋 | 내용 |
|---|---|---|
| 2026-08-04 | `aa2adbf` | notion-quiz 파이프라인 스켈레톤 초기 커밋 |
| 2026-08-15 | `727b94d` | 대상 위키가 Notion이 아니라 **Outline**임을 실제 HTML 확인 후 전제 전환, 스켈레톤 → 실제 구현 완성 |
| 2026-08-16 | `d3f2f44` | `OUTLINE_DOCUMENT_ID`로 컬렉션 전체 대신 단일 문서(+하위 트리)만 순회하는 기능 추가 |
| 2026-08-16 | `e404e5f` | README에 데이터 흐름 + GitHub Secrets 안전성 ASCII 다이어그램 추가 |
| 2026-08-16 | `3bba644` | `collect_document_tree`가 URL slug 대신 실제 UUID로 하위 문서 조회하도록 수정 (400 에러 해결) |
| 2026-08-16 | `edbad82` | 퀴즈 생성 LLM을 **Gemini(무료 티어)** 로 전환, Claude는 유료 대안으로 유지 (`QUIZ_PROVIDER`) |
| 2026-08-16 | `e745b8e` | `QUIZ_PROVIDER`/`DELIVERY_MODE`가 빈 문자열일 때 기본값 폴백 안 되던 버그 수정 |
| 2026-08-17 | `001bfa2` | 단종된 `gemini-2.0-flash` → `gemini-3.5-flash-lite`로 기본 모델 교체 (404 해결) |
| 2026-08-17 | `7957a20` | **Discord, Google Chat** 전달 방식 추가 (Discord는 스포일러 태그, Google Chat은 threadKey로 정답 처리) |
| 2026-08-21 | `86952ae` | `config.py` 주석에 discord/google_chat 값 누락된 것 수정 |
| 2026-08-22 | `a19289e` | `SECURITY_AND_COST_AUDIT.md`를 gitignore에 추가 (내부 전용 유지) |
| 2026-08-23 | `4125412` | 종합 점검 보고서(`REVIEW_2026-08-22.md`) + e2e 체크리스트/스모크 테스트 추가 (다른 세션에서 진행, Gemini 무료 티어 데이터 정책 이슈 최초 발견) |
| 2026-09-05 | `5e34a4f` | `process.md` 신설, `/process` 명령어 추가. Gemini 무료 티어 유지 확정 + `OUTLINE_DOCUMENT_ID`를 `mOuXpLufUA` 하나로 코드 레벨 고정(다른 값이면 즉시 실패), `OUTLINE_ROOT_COLLECTION_ID` 경로 완전 비활성화. `tests/test_config.py` 4건 추가 |
| 2026-09-19 | `fd4cb62` | E2E 스모크 테스트를 현재 구성(Gemini/Discord/단일문서)에 맞게 전면 재작성 — auth-ping 수준에서 실제 크롤링·퀴즈 생성까지 구동하는 버전으로 |
| 2026-09-25 | `5ad4ad8` | 병렬 세션에서 갈라진 e2e 스크립트 두 벌을 `e2e_smoke_test.py` 하나로 병합, 체크리스트 문서의 스크립트 본문 복사를 파일 링크로 교체(문서 드리프트 재발 방지) |
| 2026-09-25 | `2ba4e02` | `quiz_generator.py` Gemini 안전 필터 차단 시 `IndexError` 대신 명확한 `RuntimeError`로 처리, `test_quiz_generator.py` 신설 |
| 2026-09-25 | `efe5521` | `wiki_quiz/retry.py` 신설 — delivery 5개 모듈(outline_document/slack/discord/google_chat/email)에 429/일시 오류 재시도 로직 추가, `outline_client.py`의 기존 재시도 로직도 여기로 통합 |
| 2026-09-25 | `6ec688e` | `daily_quiz.yml`에 파이프라인 실패 시 Discord 알림 스텝(`if: failure()`) 추가 |
| 2026-09-25 | `b9433e2` | `test_main.py` 신설(오케스트레이션 배선 검증), `test_config.py` 확장(provider/delivery_mode 기본값). pytest 21개 → 56개 |
| 2026-09-25 | `4551cbe` | 배포 검증(A~C)과 Outline 권한 잠그기(D)를 process.md "지금 해야 할 순서" 섹션 하나로 통합 |
| 2026-09-30 | `8916068` | **버그 수정**: `.env.example`의 `KEY=   # 설명` 형태 줄에서 인라인 주석이 python-dotenv에 값으로 잘못 파싱되던 문제 발견·수정(`OUTLINE_ROOT_COLLECTION_ID`/`OUTLINE_DOCUMENT_ID`/`QUIZ_MODEL` 해당). `cp .env.example .env` 직후 바로 쓰면 `OUTLINE_ROOT_COLLECTION_ID`가 비의도적으로 채워져 즉시 에러 나던 것 — `tests/e2e_smoke_test.py`를 실제로 로컬에서 돌려보다가 발견함. 수정 후 0~1단계(Python 버전, config 로드)는 정상 통과, 2단계(Outline 인증)에서 플레이스홀더 키로 인한 401까지 깔끔하게 도달 확인 |

**GitHub 설정(코드 밖, Secrets/Variables) 진행 상황:**
- ✅ `OUTLINE_API_URL` (Variable), `OUTLINE_API_KEY` / `OUTLINE_DOCUMENT_ID` / `GEMINI_API_KEY` (Secrets) 등록 확인됨
- ✅ `DELIVERY_MODE=discord` 사용하기로 결정
- ⏳ `DISCORD_WEBHOOK_URL` (Secret), `DELIVERY_MODE` (Variable) — 등록 방법 안내는 완료, 실제 등록 여부 미확인

---

## 남은 것 (TODO)

### 사람이 결정/실행해야 하는 것
- [ ] **배포 검증 + Outline 권한 잠그기 A~D 순서 전체** → 위 "지금 해야 할 순서" 섹션 참고
  (예전엔 이 항목이 여기 개별 체크박스로 흩어져 있었는데, 2026-09-25에 A/B/C/D 순서
  하나로 합쳤다 — 중복 방지를 위해 여기서는 저 섹션을 가리키기만 함)
- [x] `OUTLINE_DOCUMENT_ID` 값이 정확히 의도한 문서(`mOuXpLufUA`)인지 — 코드가 이 값이
  아니면 즉시 실패하도록 고정해서, 잘못된 값이 등록돼 있다면 실행 시 바로 드러남

### 코드 개선 검토 항목 (`REVIEW_2026-08-22.md` 3번 항목 근거)
- [x] [높음] `quiz_generator.py::_generate_with_gemini` — Gemini가 안전 필터 등으로 응답을 차단하면 `IndexError`/`TypeError`로 죽던 문제. `_raise_if_gemini_blocked`를 추가해 `prompt_feedback.block_reason`/빈 `candidates`/`finish_reason != STOP`/빈 `content.parts`를 먼저 사람이 읽을 수 있는 `RuntimeError`로 바꿔 던지도록 수정 (2026-09-25)
- [x] [중간] `delivery/*.py` 5개 모듈에 429/일시적 오류 재시도 로직 없음 — `wiki_quiz/retry.py`에 공통 정책(`post_with_retry`/`smtp_retry`) 신설, outline_client.py의 기존 429 로직도 여기로 통합. outline_document/slack/discord/google_chat은 POST 한 번 단위로, email은 SMTP 연결 단위로 재시도 (요청 하나 단위로만 감싸서 한쪽 메시지가 재시도되는 동안 이미 성공한 다른 메시지가 중복 전송되지 않게 함) (2026-09-25)
- [x] [중간] 워크플로 실패 시 알림 스텝 없음 — `daily_quiz.yml`에 `if: failure()` 스텝 추가, `DISCORD_WEBHOOK_URL`이 있으면 실패 시에만 Discord로 알림 (2026-09-25)
- [x] [중간] `quiz_generator.py`/`main.py`/`config.py`에 대한 단위 테스트 없음 — `test_quiz_generator.py`(LLM 응답 모킹 + 안전필터 차단 회귀 테스트), `test_main.py`(오케스트레이션 배선 검증), `test_config.py` 확장(provider/delivery_mode 기본값·검증) 추가. `test_retry.py`도 신설. 21개 → 56개 (2026-09-25)
- [ ] [낮음] `requirements.txt`의 `anthropic`/`google-genai` 버전 상한 없음 (breaking release 시 크론이 조용히 깨질 위험)
- [ ] [낮음] `SAMPLE_CHUNK_COUNT`/`QUESTION_COUNT`에 값 검증(0 이하 방지) 없음
- [ ] [낮음] `requirements.txt`의 죽은 `slack_sdk` 주석 정리

### 문서 정리
- [ ] `tests/e2e_go_live_checklist.md`를 지금 구성(Gemini 기본값·Discord 포함)에 맞게 갱신할지 검토
- [ ] `OUTLINE_ROOT_COLLECTION_ID` 관련 문구가 README에 남아있는데 실제로는 `OUTLINE_DOCUMENT_ID`만 사용 중 — 실사용 기준으로 단순화할지 검토

---

## 참고 문서
- [README.md](README.md) — 아키텍처·파이프라인·설정값 전체 설명
- [REVIEW_2026-08-22.md](REVIEW_2026-08-22.md) — 종합 점검 보고서(비용/보안/코드 버그)
- [tests/e2e_go_live_checklist.md](tests/e2e_go_live_checklist.md) — 실연동 전 체크리스트
- `SECURITY_AND_COST_AUDIT.md` — 보안·비용 전수조사 (gitignore됨, 로컬에만 존재)
