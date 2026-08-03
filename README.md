# notion-quiz

Notion 개발 위키(https://wiki.class.day/doc/42-NgGIyvI63i 등) 전체를 순회해
텍스트·PDF·Word·Markdown 첨부파일까지 포함한 콘텐츠에서 매일 랜덤 3문제 퀴즈를
Claude API로 자동 생성하는 배치 파이프라인.

## 파이프라인 (설계 메모 기준)

1. **위키 순회 수집** — `notion_client.py`: `Get Block Children`을 재귀 호출해 페이지 트리 전체 순회. 초당 ~3req 레이트리밋 → 429 백오프.
2. **첨부파일 다운로드·파싱** — `attachment_parser.py`: 만료 URL로 파일 받아 PDF/Word/Markdown 텍스트 추출.
3. **랜덤 샘플링** — `sampler.py`: 블록/문단/첨부 청크 중 무작위 표본 추출 (토큰 비용 억제).
4. **퀴즈 생성** — `quiz_generator.py`: Claude API (Haiku 4.5 기본, 필요 시 Sonnet 5)로 3문제 생성.
5. **결과 전달** — `delivery/`: Notion 페이지 / Slack / 이메일 / CLI 중 선택.
6. **매일 자동 실행** — `.github/workflows/daily_quiz.yml` (GitHub Actions cron, UTC).

## 폴더 구조

```
notion-quiz/
├── README.md
├── requirements.txt
├── .env.example
├── config.py                        # 환경변수·설정 로드
├── src/notion_quiz/
│   ├── __init__.py
│   ├── notion_client.py             # 1. 위키 순회 수집
│   ├── attachment_parser.py         # 2. 첨부파일 파싱
│   ├── sampler.py                   # 3. 랜덤 샘플링
│   ├── quiz_generator.py            # 4. Claude API 퀴즈 생성
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── notion_page.py           # 5-A. Notion 페이지 생성
│   │   ├── slack.py                 # 5-B. Slack 발송
│   │   ├── email.py                 # 5-B. 이메일 발송
│   │   └── cli.py                   # 5-C. CLI 출력
│   └── main.py                      # 전체 오케스트레이션 entrypoint
├── .github/workflows/daily_quiz.yml # 6. 매일 자동 실행
├── scripts/run_local.sh             # 로컬 테스트용 실행 스크립트
└── tests/
    ├── test_sampler.py
    └── test_attachment_parser.py
```

## 설정

`.env.example`을 `.env`로 복사 후 값 채우기:

- `NOTION_API_KEY` — Notion Integration 토큰 (대상 위키에 연결 필요)
- `NOTION_ROOT_PAGE_ID` — 순회를 시작할 루트 페이지 ID
- `ANTHROPIC_API_KEY` — Claude API 키
- `QUIZ_MODEL` — 기본 `claude-haiku-4-5`, 필요 시 `claude-sonnet-5`로 전환
- `DELIVERY_MODE` — `notion` / `slack` / `email` / `cli`
- (전달 방식별 추가 값: `SLACK_WEBHOOK_URL`, `SMTP_*` 등)

## 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env   # 값 채우기
python -m src.notion_quiz.main
```

## 자동 실행 (GitHub Actions)

`.github/workflows/daily_quiz.yml`이 매일 정해진 UTC 시각에 `python -m src.notion_quiz.main`을
실행. 레포 Settings → Secrets에 `.env`와 동일한 키들을 등록해야 함.

## 미결정 사항 (추가 조사 필요했던 항목)

- 전달 방식(A/B/C) 최종 선택 — 현재 스켈레톤은 `DELIVERY_MODE`로 스위칭 가능하게 설계
- 한국어 PDF/Word 텍스트 깨짐 여부 — `attachment_parser.py`에 인코딩 처리 지점 표시해둠
- launchd 병행 여부 — GitHub Actions cron 지연이 문제되면 `scripts/run_local.sh` + launchd plist 추가 고려
