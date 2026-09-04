# wiki-quiz 진행 상황

> 이 문서는 "우리가 해야 할 것 / 이때까지 한 것 / 남은 것"을 계속 갱신하며 추적하는
> 살아있는 문서다. `/process` 명령으로 자동 갱신된다(`.claude/commands/process.md` 참고).
> 세부 근거가 필요하면 `REVIEW_2026-08-22.md`(종합 점검 보고서), `tests/e2e_go_live_checklist.md`
> (실연동 전 체크리스트), `SECURITY_AND_COST_AUDIT.md`(보안·비용 전수조사, gitignore됨,
> 로컬 전용)를 참고.

마지막 갱신: 2026-09-05 · 커밋 `5e34a4f` 기준

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

## 지금 당장 결정/실행 필요 (사람 판단 대기 중) ⚠️

- **[진짜 100% 보장을 위한 Outline 권한 제한 — 아직 미실행]** 코드는 `OUTLINE_DOCUMENT_ID`가
  `mOuXpLufUA`가 아니면 즉시 실패하도록 고정했지만(`config.py`), 이건 "우리 코드가 실수로
  다른 문서를 안 읽는다"만 보장한다. `OUTLINE_API_KEY`가 유출되어 코드를 거치지 않고 Outline
  API에 직접 호출되면, 그 키의 소유 계정이 원래 읽을 수 있는 문서는 다 읽힌다. **진짜 크리덴셜
  레벨 100% 보장**을 원하면 Outline 쪽에서:
  1. 이 문서가 속한 컬렉션을 "제한됨(restricted)"으로 설정
  2. 전용 계정을 만들고 `documents.add_user`로 이 문서에만 권한 부여
  3. 그 계정으로 `OUTLINE_API_KEY` 재발급
  아직 실행 안 됨 — Outline 관리자 화면 캡처 주면 단계별로 안내 가능.

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

**GitHub 설정(코드 밖, Secrets/Variables) 진행 상황:**
- ✅ `OUTLINE_API_URL` (Variable), `OUTLINE_API_KEY` / `OUTLINE_DOCUMENT_ID` / `GEMINI_API_KEY` (Secrets) 등록 확인됨
- ✅ `DELIVERY_MODE=discord` 사용하기로 결정
- ⏳ `DISCORD_WEBHOOK_URL` (Secret), `DELIVERY_MODE` (Variable) — 등록 방법 안내는 완료, 실제 등록 여부 미확인

---

## 남은 것 (TODO)

### 사람이 결정/실행해야 하는 것
- [ ] Gemini 무료 티어 데이터 정책 최종 확정 (위 "지금 당장 결정 필요" 참고)
- [ ] GitHub Secrets에 `DISCORD_WEBHOOK_URL` 등록
- [ ] GitHub Variables에 `DELIVERY_MODE=discord` 등록
- [ ] 등록 후 Actions에서 수동 실행(`Run workflow`)해서 Discord로 실제 퀴즈 도착하는지 확인 — **아직 전체 파이프라인이 끝까지 성공한 로그를 확인한 적 없음** (Outline 수집 단계는 성공 확인됨, Gemini 생성 이후 단계는 미확인)
- [ ] `tests/e2e_smoke_test.py`를 실제 `.env` 채워서 본인 터미널에서 실행 (Outline/Gemini 키 유효성 확인)
- [x] `OUTLINE_DOCUMENT_ID` 값이 정확히 의도한 문서(`mOuXpLufUA`)인지 — 코드가 이 값이
  아니면 즉시 실패하도록 고정해서, 잘못된 값이 등록돼 있다면 실행 시 바로 드러남

### 코드 개선 검토 항목 (`REVIEW_2026-08-22.md` 3번 항목 근거)
- [ ] [높음] `quiz_generator.py::_generate_with_gemini` — Gemini가 안전 필터 등으로 응답을 차단하면 `IndexError`/`TypeError`로 죽음. 명확한 예외 처리 필요
- [ ] [중간] `delivery/*.py` 5개 모듈에 429/일시적 오류 재시도 로직 없음 (Outline 크롤링 단계만 있음)
- [ ] [중간] 워크플로 실패 시 알림 스텝 없음 (`if: failure()`로 Slack/Discord 알림 추가 검토)
- [ ] [중간] `quiz_generator.py`/`main.py`/`config.py`에 대한 단위 테스트 없음 (현재 21개 테스트는 이 세 파일을 커버 안 함)
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
