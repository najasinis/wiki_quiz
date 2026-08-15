# wiki-quiz

개발 위키(https://wiki.class.day/doc/42-NgGIyvI63i 등, **Outline** 기반) 전체를 순회해
텍스트·PDF·Word·Markdown 첨부파일까지 포함한 콘텐츠에서 매일 랜덤 3문제 퀴즈를
Claude API로 자동 생성하는 배치 파이프라인.

> ⚠️ 이전 설계 메모에는 대상 위키를 Notion으로 잘못 가정하고 있었음. `wiki.class.day` 페이지의
> HTML 소스(`<title>Outline</title>`, "A modern team knowledge base..." 문구, `/static/assets/...`
> 자산 경로)를 직접 확인한 결과 **Outline**(오픈소스 팀 위키/지식베이스, https://www.getoutline.com )으로
> 확인되어 Notion API 기준 설계를 전부 Outline API 기준으로 재작성함.

## 현재 상태: 스켈레톤 → 구현 완료 (실제 위키 연동 전 최종 확인 필요)

이전 설계 메모 단계의 `NotImplementedError` 스켈레톤을 모두 실제 코드로 채웠고, 로컬에서
Outline API·Claude API를 모킹한 end-to-end 드라이런과 `pytest` 전체 스위트(13개)로 검증했다.
다만 실제 `wiki.class.day` 인스턴스에 대한 연동은 아직 한 번도 실행해보지 않았으므로, 아래
"실제 연동 전 확인 필요" 항목은 여전히 남아 있다 — 이 부분은 실제 API 키/권한을 가진 사람이
검증해야 하며, 이 저장소 작업만으로는 확인할 수 없었다.

## 파이프라인

1. **위키 순회 수집** — `outline_client.py`: Outline API는 RPC 스타일 POST 엔드포인트를 사용.
   컬렉션의 루트부터 `documents.list`(자식 문서 목록, offset/limit 페이지네이션) →
   `documents.info`(본문 조회)를 재귀 호출해 문서 트리 전체를 순회. 인증은
   `Authorization: Bearer <API Key>` 헤더 방식(Settings → API Keys에서 발급).
   429 응답에서만 지수 백오프로 재시도하도록 구현(비일시적 오류인 401/403 등은 즉시 실패).
2. **첨부파일 다운로드·파싱** — `attachment_parser.py`: 문서 본문(Markdown)에서
   `[..](url)`/`![..](url)` 패턴으로 첨부 링크를 추출하고, 확장자(pdf/docx/doc/md/markdown)로
   필터링한 뒤 pdfplumber/python-docx로 텍스트 추출. 다운로드 시 Outline API 키를
   `Authorization: Bearer` 헤더로 함께 실어 보내도록 구현(아래 "확인 필요" 참고).
3. **랜덤 샘플링** — `sampler.py`: 문서/첨부 텍스트를 문단 단위로 모아 최대 500자
   청크로 쪼갠 뒤(`build_chunks`), 그중 무작위 표본을 추출(`sample_chunks`)해 토큰 비용 억제.
4. **퀴즈 생성** — `quiz_generator.py`: Claude API (Haiku 4.5 기본, 필요 시 Sonnet 5)를
   `tool_choice`로 구조화 출력을 강제해 4지선다 3문제를 JSON으로 생성(자유 텍스트 파싱보다
   견고함).
5. **결과 전달** — `delivery/`: Outline 문서 생성(`documents.create`) / Slack / 이메일 / CLI
   중 `DELIVERY_MODE`로 선택. 필수 설정이 비어 있으면 각 모듈이 바로 `ValueError`를 던진다.
6. **매일 자동 실행** — `.github/workflows/daily_quiz.yml` (GitHub Actions cron, UTC).

## 폴더 구조

```
wiki-quiz/
├── README.md
├── requirements.txt
├── .env.example
├── conftest.py                      # pytest가 src/를 import 경로에 잡도록 하는 설정 (아래 "고친 버그" 참고)
├── config.py                        # 환경변수·설정 로드
├── src/wiki_quiz/
│   ├── __init__.py
│   ├── outline_client.py            # 1. 위키 순회 수집
│   ├── attachment_parser.py         # 2. 첨부파일 파싱
│   ├── sampler.py                   # 3. 랜덤 샘플링
│   ├── quiz_generator.py            # 4. Claude API 퀴즈 생성
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── outline_document.py      # 5-A. Outline 문서 생성
│   │   ├── slack.py                 # 5-B. Slack 발송
│   │   ├── email.py                 # 5-B. 이메일 발송
│   │   └── cli.py                   # 5-C. CLI 출력
│   └── main.py                      # 전체 오케스트레이션 entrypoint
├── .github/workflows/daily_quiz.yml # 6. 매일 자동 실행
├── scripts/run_local.sh             # 로컬 테스트용 실행 스크립트
└── tests/
    ├── fixtures/                    # sample.pdf / sample.docx (attachment_parser 테스트용)
    ├── test_sampler.py
    ├── test_attachment_parser.py
    └── test_outline_client.py
```

## 설정

`.env.example`을 `.env`로 복사 후 값 채우기:

- `OUTLINE_API_URL` — 인스턴스 API 베이스 URL (예: `https://wiki.class.day/api`)
- `OUTLINE_API_KEY` — Outline API 키 (Settings → API Keys에서 발급, 대상 위키 접근 권한 필요)
- `OUTLINE_ROOT_COLLECTION_ID` — 순회를 시작할 루트 컬렉션 ID
- `ANTHROPIC_API_KEY` — Claude API 키
- `QUIZ_MODEL` — 기본 `claude-haiku-4-5`, 필요 시 `claude-sonnet-5`로 전환
- `DELIVERY_MODE` — `outline` / `slack` / `email` / `cli`
- (전달 방식별 추가 값: `SLACK_WEBHOOK_URL`, `SMTP_*` 등)

## 로컬 실행

**요구 사항: Python >= 3.10** (코드 전체에서 `X | None` 문법(PEP 604) 사용 — macOS
기본 `python3`가 3.9 이하인 경우가 있어 그대로 실행하면 `TypeError`로 즉시 실패한다.
`python3 --version`으로 먼저 확인하고, 낮으면 pyenv 등으로 3.10+ 설치 후 그 인터프리터로
venv를 만들 것. 레포 루트의 `.python-version`(3.12)이 pyenv 사용 시 자동으로 잡힌다.)

```bash
python3 --version   # 3.10 미만이면 아래 pip install 전에 3.10+ 인터프리터로 교체
pip install -r requirements.txt
cp .env.example .env   # 값 채우기
python -m src.wiki_quiz.main
```

또는 `scripts/run_local.sh`를 실행하면 venv 생성부터 실행까지 한 번에 처리된다(단, 이 경우도
`python3` 자체가 3.10+ 여야 한다 — 스크립트는 시스템 `python3`로 venv를 만든다).

## 자동 실행 (GitHub Actions)

`.github/workflows/daily_quiz.yml`이 매일 정해진 UTC 시각에 `python -m src.wiki_quiz.main`을
실행. 레포 Settings → Secrets에 `.env`와 동일한 키들을 등록해야 함.

## 테스트

```bash
pip install -r requirements.txt
pytest
```

13개 테스트 모두 통과(네트워크 호출 없이 동작 — Outline/Claude API 호출은 각각
monkeypatch/respx 스타일로 목킹해서 검증했다). `tests/fixtures/sample.pdf`,
`sample.docx`는 attachment_parser 파싱 테스트용으로 새로 추가한 최소 픽스처 파일이다.

## 이번에 고친 버그: import 경로 문제

이전 스켈레톤 상태에서 README 안내대로 `python -m src.wiki_quiz.main`이나 `pytest`를
그대로 실행하면 `ModuleNotFoundError: No module named 'wiki_quiz'`가 발생했다(실제
재현·확인함). `src/wiki_quiz/*.py` 내부 모듈들이 서로를 `from wiki_quiz.xxx import ...`
(앞에 `src.` 없는 절대 임포트)로 참조하는데, `-m` 실행 시 저장소 루트만 `sys.path`에
올라가고 `src/`는 올라가지 않기 때문. 다음 세 곳에 `PYTHONPATH=src` 관련 설정을
추가해 해결했다.

- `conftest.py` (신규) — pytest 실행 시 자동으로 `src/`를 import 경로에 추가
- `scripts/run_local.sh` — `python -m src.wiki_quiz.main` 실행 전 `PYTHONPATH` 설정
- `.github/workflows/daily_quiz.yml` — 파이프라인 실행 스텝에 `PYTHONPATH: ${{ github.workspace }}/src` 추가

## 실제 연동 전 확인 필요 (이 세션에서 확인 불가능한 항목)

아래 항목들은 `wiki.class.day` 인스턴스에 실제 API 키로 접근해봐야 확정할 수 있는
사실이라, 이번 작업에서는 코드가 두 경우 모두 합리적으로 대응하도록 구현해뒀을 뿐
실측 검증은 하지 못했다. 실제 연동 시 반드시 확인 필요:

- **첨부파일 URL 인증 방식** — 서명된 만료 URL(S3 presigned 등)인지, API 키 인증이
  필요한 프록시 URL인지 미확인. 두 경우 모두 대응 가능하도록 다운로드 시
  `Authorization: Bearer <OUTLINE_API_KEY>` 헤더를 함께 보내되, **다운로드 대상 host가
  `OUTLINE_API_URL`의 host와 일치할 때만** 헤더를 붙이도록 제한했다(보안 수정 — 위키
  본문에 제3자 도메인 링크가 있어도 API 키가 그쪽으로 유출되지 않도록). 실제 Outline
  인스턴스 응답으로 인증 방식 자체는 아직 검증되지 않았다.
- **Outline 레이트리밋 실측치** — 공식 문서의 "IP당 분당 1000 req" 예시는 설치별로
  조정 가능한 기본값일 뿐, `wiki.class.day` 인스턴스의 실제 설정값과 429 발생 지점은
  다를 수 있다. 429 백오프 로직 자체는 구현·테스트했지만 실제 임계치는 미검증.
- **API 키 발급 권한** — `wiki.class.day`에 대한 Outline 관리자 권한 또는 API 키 발급
  권한 보유 여부. 이건 계정/조직 권한 문제라 코드로 해결할 수 없다.
- **한국어 PDF 텍스트 깨짐 여부** — pdfplumber 추출 결과가 실제 한국어 위키 첨부파일에서
  깨지는지는 실제 파일로만 확인 가능. 현재는 별도 인코딩 보정 로직 없이 원본 추출 결과를
  그대로 사용한다.

## 설계상 결정한 사항 (기존 "미결정 사항" 중 이번에 해소한 것)

- **전달 방식(outline/slack/email/cli)** — 넷 다 구현 완료, `DELIVERY_MODE`로 전환.
  자동 실행(GitHub Actions) 목적이라면 CLI는 사람이 보지 못하므로 Slack 또는 Email 중
  하나를 기본으로 쓰는 걸 권장.
- **Slack 정답 스포일러 처리** — Incoming Webhook은 스레드 답글 API를 제공하지 않아
  완벽한 스포일러 처리는 불가능. 대신 문제 메시지와 정답/해설 메시지를 두 번의 별도
  웹훅 호출로 나눠 보내는 절충안으로 구현. 진짜 스레드 답글이 필요하면 Bot 토큰 기반
  `chat.postMessage`로 교체 필요.
- **레이트리밋 재시도 범위** — "모든 Exception 재시도"에서 "429 응답에만 재시도"로
  좁힘. 인증 오류 등 비일시적 오류를 최대 6회 재시도하며 시간을 낭비하지 않도록 함.
- **launchd 병행 여부** — 필요성 자체는 GitHub Actions 운영 후 지연 문제가 실제로
  발생하는지 봐야 판단 가능하므로, 여전히 보류 상태로 남겨둠 (`scripts/run_local.sh`는
  이미 launchd에서 바로 호출 가능한 형태로 준비되어 있음).
