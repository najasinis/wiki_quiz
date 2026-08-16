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

## 이 서비스는 어떻게 운영되나 (쉽게 설명)

**[wiki-quiz 동작 원리 — DB도, 서버도, 화면도 없는 이유]** 👍

결론부터 말하면 이 서비스에는 **DB(데이터베이스)도 없고, 항상 켜져 있는 백엔드 서버도 없고,
우리가 흔히 아는 프론트엔드 화면(웹사이트)도 없습니다.** "매일 딱 한 번, 정해진 시간에
스스로 일어나서 할 일을 하고 다시 잠드는 로봇 우체부" 같은 구조예요.

**하루 동안 실제로 일어나는 일 (순서대로)**

1. **알람이 울린다** — GitHub Actions라는 곳에 "매일 UTC 0시(한국시간 오전 9시)에 이 로봇을
   깨워줘"라고 예약(cron)을 걸어둠. 평소엔 이 로봇, 아예 존재하지 않는 것과 같음(서버 요금도
   안 나감). 정해진 시간에만 잠깐 컴퓨터 한 대가 켜졌다가 일 끝나면 바로 꺼짐.
2. **도서관에 간다** — 로봇이 Outline 위키(우리 회사 도서관)에 들어가서, 책장(컬렉션)부터
   시작해 모든 책(문서)을 하나하나 펼쳐본다. 재귀 호출이라는 방식으로 "이 책 밑에 또 다른
   책이 있으면 그것도 펼쳐본다"를 문서 트리 끝까지 반복.
3. **첨부파일도 챙긴다** — 책 속에 PDF나 워드파일 링크가 있으면 그것도 다운로드해서
   내용을 텍스트로 뽑아낸다.
4. **아무거나 몇 장 뽑는다** — 도서관 전체 내용을 다 기억하면 너무 비싸고 느리니까,
   그중에서 무작위로 몇 조각(청크)만 뽑는다. 제비뽑기와 같음.
5. **똑똑한 친구에게 물어본다** — 뽑은 조각들을 Claude(AI)에게 보여주고 "이 내용으로
   4지선다 퀴즈 3개만 만들어줘"라고 부탁. Claude가 문제·보기·정답·해설을 만들어서 돌려줌.
6. **우편함에 넣는다** — 완성된 퀴즈를 미리 정해둔 곳(Outline 문서/Slack/이메일/터미널
   화면 중 하나)에 배달하고, 로봇은 다시 잠든다.
7. **내일 또 반복** — 어제 무슨 문제를 냈는지는 **전혀 기억하지 않음.** 매일 처음부터
   새로 도서관을 통째로 다시 훑고, 새로 무작위로 뽑음.

**왜 DB가 없어도 되나, 왜 서버가 항상 켜져 있지 않아도 되나**

| 보통의 서비스라면 | wiki-quiz는 |
|---|---|
| DB에 "어제 낸 문제, 사용자 정답 기록" 저장 | 아무것도 저장 안 함 — 매번 새로 뽑고 끝나면 잊어버림 |
| 항상 켜진 서버가 요청을 기다림 (24시간 대기) | 하루 한 번, 딱 실행되는 순간에만 컴퓨터가 켜짐(GitHub Actions) |
| 웹사이트(프론트엔드)에서 사용자가 클릭·조회 | 화면이 따로 없고, 결과를 Outline 문서/Slack/이메일 중 하나로 "떠먹여줌" |
| 회원가입·로그인 같은 사용자 관리 | 없음 — 보는 사람은 그냥 Slack 채널이나 이메일함을 보면 됨 |

이렇게 "저장하지 않고 매번 새로 만들어서 던져주고 끝"이라는 구조라서, 관리할 서버도
DB도 필요 없이 GitHub Actions라는 무료(또는 저렴한) 자동 실행 서비스 하나로 전체가
굴러갑니다. `DELIVERY_MODE` 설정값 하나로 "오늘은 어느 우편함에 넣을지"만 고르면 됨.

예) 매일 아침 신문 배달부가 그날그날 신문사에서 신문을 받아 그대로 우편함에 넣고
    가는 것과 같음 — 배달부는 어제 배달한 신문을 창고에 쌓아두지 않고, 자기 집(서버)도
    없이 매일 아침 잠깐 나타났다가 사라짐.

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
- `OUTLINE_ROOT_COLLECTION_ID` — 순회를 시작할 루트 컬렉션 ID (컬렉션 전체를 순회)
- `OUTLINE_DOCUMENT_ID` — 설정하면 컬렉션 전체 대신 이 문서(+하위 트리)만 순회.
  둘 중 하나는 필수이며, 둘 다 설정 시 `OUTLINE_DOCUMENT_ID`가 우선한다.
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

## 데이터 흐름 (코드 기준, 어느 파일이 무엇을 하는지)

이 서비스에는 DB가 없다. 매일 실행마다 아래 파이프라인을 처음부터 끝까지 통째로
돌리고, 끝나면 메모리에 있던 모든 데이터(문서 본문, 청크, 생성한 퀴즈)는 그대로
날아간다. `main.py`가 이 전체를 순서대로 호출하는 오케스트레이터다.

```
GitHub Actions (cron, 매일 UTC 0시)
  │  daily_quiz.yml 이 아래 env를 주입하고
  │  `python -m src.wiki_quiz.main` 실행
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ main.py : run()                                                  │
└─────────────────────────────────────────────────────────────────┘
  │
  │ ① cfg = load_config()               [config.py]
  │    환경변수 OUTLINE_API_URL / OUTLINE_API_KEY /
  │    OUTLINE_DOCUMENT_ID(또는 OUTLINE_ROOT_COLLECTION_ID) /
  │    ANTHROPIC_API_KEY 등을 읽어 Config 객체로 모음
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ ② OutlineWikiCrawler                  [outline_client.py]        │
│                                                                    │
│   OUTLINE_DOCUMENT_ID 있음?                                       │
│     예 → collect_document_tree(document_id)                      │
│           documents.info(문서 하나 조회)                          │
│              └→ documents.list(그 문서의 자식들, 재귀)            │
│     아니오 → collect_all_documents(root_collection_id)           │
│           documents.list(컬렉션 최상위) → 재귀로 트리 전체 순회   │
│                                                                    │
│   요청마다 헤더: Authorization: Bearer {OUTLINE_API_KEY}          │
│   응답: WikiDocument(문서 id, 제목, 본문 markdown, 첨부 링크 목록)│
└─────────────────────────────────────────────────────────────────┘
  │  docs: list[WikiDocument]  (메모리에만 존재, 저장 안 함)
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ ③ attachment_parser.py                                           │
│   문서 본문 안 [텍스트](url) / ![이미지](url) 링크 중             │
│   pdf/docx/doc/md 확장자만 골라 다운로드 → 텍스트 추출            │
│   (다운로드 URL host가 Outline 인스턴스와 같을 때만 API 키를      │
│    Authorization 헤더에 실어 보냄 — 다른 사이트로 키 유출 방지)   │
└─────────────────────────────────────────────────────────────────┘
  │  attachments: list[ParsedAttachment]
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ ④ sampler.py                                                     │
│   build_chunks()  : 문서 본문 + 첨부 텍스트를 문단 단위로 모아   │
│                      최대 500자짜리 조각(TextChunk)들로 분해      │
│   sample_chunks() : 그중 무작위로 SAMPLE_CHUNK_COUNT개만 추출     │
│                      (Claude에게 위키 전체를 보내면 비용·시간 폭증)│
└─────────────────────────────────────────────────────────────────┘
  │  sampled: list[TextChunk]  (매번 새로 무작위 추출, 기록 안 남음)
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ ⑤ quiz_generator.py                                              │
│   Claude API(Anthropic) 호출, tool_choice로 구조화 출력 강제      │
│   system prompt: "주어진 조각만 근거로, 지어내지 마라"            │
│   요청 헤더: x-api-key: {ANTHROPIC_API_KEY} (SDK가 자동 처리)     │
│   응답: 4지선다 문제 QUESTION_COUNT개(JSON) → QuizQuestion 리스트 │
└─────────────────────────────────────────────────────────────────┘
  │  questions: list[QuizQuestion]
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ ⑥ delivery/ (DELIVERY_MODE로 분기)                                │
│   outline → documents.create 로 Outline에 새 문서로 올림          │
│   slack   → SLACK_WEBHOOK_URL 로 메시지 전송                      │
│   email   → SMTP_* 설정으로 발송                                  │
│   cli     → 터미널에 그대로 출력                                  │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
프로세스 종료 → GitHub Actions 러너(컴퓨터)도 함께 종료
   (다음 실행까지 이 파이프라인은 어디에도 존재하지 않는다)
```

핵심은 ②에서 "컬렉션 전체를 훑을지, 문서 하나(+하위 트리)만 훑을지"가
`OUTLINE_DOCUMENT_ID` 유무로 갈린다는 점이다. 이후 ③~⑥ 단계는 입력 문서 개수가
1개든 100개든 완전히 동일한 코드 경로를 탄다.

## GitHub Secrets는 실제로 어떻게, 어디까지 안전한가

"Secret에 등록해두면 어떻게 코드가 그걸 안전하게 읽어오나?"에 대한 설명이다.
핵심 원칙 하나만 기억하면 된다 — **Secret 값은 절대 저장소(코드)에 존재하지
않고, 딱 실행되는 그 순간에만 잠깐 컴퓨터의 "환경변수"로 주입됐다가 실행이
끝나면 사라진다.**

```
┌──────────────────────┐
│ GitHub 저장소 Settings │   여기 적힌 값은 암호화되어 저장.
│  → Secrets and         │   생성한 사람 본인도 다시 값을 볼 수 없음
│    variables → Actions │   (이름만 보이고, 값은 "Update"로 덮어쓰기만 가능)
│                        │
│  OUTLINE_API_KEY       │
│  OUTLINE_DOCUMENT_ID   │
│  ANTHROPIC_API_KEY ... │
└──────────┬─────────────┘
           │ (2) cron 시각이 되면 GitHub이
           │     임시 가상머신 한 대를 새로 띄우고
           │     이 저장소 코드를 그 안에 체크아웃
           ▼
┌────────────────────────────────────────────┐
│ daily_quiz.yml 의 env: 블록                  │
│                                              │
│   OUTLINE_API_KEY: ${{ secrets.OUTLINE_API_KEY }} │
│                                              │
│  ${{ secrets.XXX }} 는 "그 값을 코드에 적어라"가 │
│  아니라 "실행 직전에 그 값을 그 자리에 채워 넣어라"│
│  라는 뜻. 이 yml 파일 자체에는 실제 키 값이       │
│  단 한 글자도 적혀 있지 않다.                    │
└──────────────────┬───────────────────────────┘
                   │ (3) 채워진 값이 그 임시 가상머신의
                   │     "환경변수"로만 설정됨
                   ▼
┌────────────────────────────────────────────┐
│ python -m src.wiki_quiz.main 실행 중         │
│                                              │
│   config.py: os.environ["OUTLINE_API_KEY"]  │
│   → 이 시점에 딱 한 번, 메모리 위에서만 읽힘   │
│   → 파일로 저장하지 않고, 코드 어디에도        │
│     print/log로 남기지 않음                   │
└──────────────────┬───────────────────────────┘
                   │ (4) 실행 끝
                   ▼
     가상머신 자체가 통째로 폐기됨
     (환경변수도, 코드도, 그 실행 흔적도 전부 함께 사라짐)
```

**이 구조가 안전한 이유:**

- **코드에는 값이 없다** — `daily_quiz.yml`을 아무리 열어봐도 `${{ secrets.OUTLINE_API_KEY }}`
  라는 "이름표"만 있지 실제 키 값은 없다. 저장소가 공개(public)여도 키가 새어나가지 않음.
- **로그에서 자동으로 가려짐** — 만약 실수로 코드가 그 값을 `print`해버려도, GitHub
  Actions가 Secret으로 등록된 값과 일치하는 문자열을 로그에서 자동으로 `***`로
  마스킹한다.
- **fork된 PR에는 전달 안 됨** — 이 저장소를 다른 사람이 fork해서 PR을 보내도,
  그 PR을 실행하는 워크플로에는 Secrets가 전달되지 않는다(악의적인 PR이 몰래
  키를 빼가는 걸 막는 GitHub의 기본 정책).
- **범위(scope)로 이중 방어** — `OUTLINE_API_KEY` 발급 시 `documents.list
  documents.info`로 범위를 좁혀뒀기 때문에, 설령 이 키가 어딘가로 샌다 해도
  문서 읽기만 가능하고 삭제·멤버 관리 같은 위험한 동작은 애초에 이 키로는 불가능.

정리하면: Secrets 탭은 "코드가 실행되는 딱 그 순간에만 잠깐 빌려주는 열쇠 보관함"이고,
`config.py`의 `os.environ[...]`은 그 순간에만 열쇠를 손에 쥐었다가 실행이 끝나면
자동으로 손을 놓는 구조다. DB가 없는 것과 같은 이유로, 이 열쇠 역시 어디에도
영구히 저장되지 않는다.

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
