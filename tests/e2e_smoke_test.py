"""
E2E 파이프라인 검증 스크립트 — 핵심 기능 전체가 실제로 동작하는지 확인한다.

2026-09-05 이후 구성(OUTLINE_DOCUMENT_ID 단일 문서 고정 + Gemini 무료 티어 +
Discord 전달)에 맞춰 작성. 이전 버전(OUTLINE_ROOT_COLLECTION_ID/ANTHROPIC_API_KEY
기준 하드코딩)은 그 이후 설정과 어긋나 있었고, 그 뒤 한 번 더 auth-ping 수준
스크립트와 실제 파이프라인 호출 스크립트가 병렬 세션에서 각각 따로 만들어졌던 걸
이번에 하나로 합쳤다 — 앞으로 두 벌로 갈라지지 않도록 이 파일 하나만 유지한다.

실제 API 키가 담긴 .env가 필요하므로 AI 세션이 아니라 키를 보유한 사람이 직접
실행해야 한다.

단계 (전부 순서대로 실행, 앞 단계 실패하면 이후 단계는 건너뜀):
  0. Python 버전 확인 (>= 3.10)
  1. 환경변수 존재 + config.load_config() 통과 (문서 ID 보안 고정 검증 포함) —
     필수 환경변수 목록을 이 스크립트가 따로 하드코딩하지 않고 실제 config.py를
     그대로 재사용한다. config.py가 바뀌면 이 스크립트도 자동으로 같이 맞아떨어진다
     (하드코딩판이 설정 변경 후 어긋났던 문제의 재발 방지).
  2. Outline 인증 (auth.info) — 읽기 전용
  3. Outline 실제 크롤링 (collect_document_tree) — 지정된 문서(+하위) 전체를 실제로 수집
  4. 첨부파일 파싱 — 수집된 문서에 첨부 링크가 있으면 실제로 다운로드·파싱
  5. 샘플링 (build_chunks + sample_chunks) — 실제 수집 데이터로 청크 생성
  6. 퀴즈 생성 — 실제 LLM 호출로 4지선다 문제 생성 (quiz_provider 설정을 그대로 따름,
     기본값 Gemini 무료 티어라 비용 무시 가능 수준)
  7. 전달 미리보기 / 실제 전송
     - delivery_mode=discord일 때만 실제 Discord 메시지 포맷을 미리보기하고,
       --send 플래그 또는 E2E_ACTUALLY_SEND=1을 줘야만 실제로 전송한다
       (되돌릴 수 없는 외부 발송이라 기본은 항상 dry-run).
     - 그 외 delivery_mode는 --send를 줘도 항상 CLI 포맷으로만 미리보기하고
       실제 외부 발송은 하지 않는다 — Discord 외 채널은 이 스크립트가 검증한 적
       없는 코드 경로라 여기서까지 실전송 안전장치를 우회시키지 않기 위함.

사용법:
  python3 tests/e2e_smoke_test.py            # 7단계까지 전부, 전달은 미리보기만
  python3 tests/e2e_smoke_test.py --send      # delivery_mode=discord면 7단계에서 실제 전송까지
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dotenv import load_dotenv
load_dotenv()


def check(name, fn):
    """fn을 실행하고 성공/실패를 출력한다. 성공 시 (True, fn의 반환값), 실패 시 (False, None)."""
    try:
        result = fn()
        print(f"[OK]   {name}")
        return True, result
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        return False, None


# ── 0. Python 버전 ──────────────────────────────────────────────────

def check_python_version():
    if sys.version_info < (3, 10):
        raise RuntimeError(f"Python 3.10+ 필요, 현재 {sys.version}")


# ── 1. 환경변수 + config ────────────────────────────────────────────

def check_config_loads():
    import config as config_module
    cfg = config_module.load_config()
    assert cfg.outline_document_id, "outline_document_id가 비어있음"
    assert cfg.gemini_api_key or cfg.anthropic_api_key, "퀴즈 생성용 API 키가 없음"
    return cfg


# ── 2. Outline 인증 ─────────────────────────────────────────────────

def check_outline_auth(cfg):
    import httpx
    resp = httpx.post(
        f"{cfg.outline_api_url.rstrip('/')}/auth.info",
        headers={"Authorization": f"Bearer {cfg.outline_api_key}"},
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    print(f"       -> 인증된 사용자: {data.get('user', {}).get('name', '?')} / "
          f"팀: {data.get('team', {}).get('name', '?')}")


# ── 3. 실제 크롤링 ───────────────────────────────────────────────────

def check_real_crawl(cfg):
    from wiki_quiz.outline_client import OutlineWikiCrawler
    with OutlineWikiCrawler(cfg.outline_api_url, cfg.outline_api_key) as crawler:
        docs = crawler.collect_document_tree(cfg.outline_document_id)
    assert docs, "문서를 하나도 못 가져왔음 (빈 결과)"
    total_chars = sum(len(d.text or "") for d in docs)
    print(f"       -> 문서 {len(docs)}건 수집, 본문 총 {total_chars}자, "
          f"첨부 링크 {sum(len(d.attachment_urls) for d in docs)}개")
    return docs


# ── 4. 첨부파일 파싱 ─────────────────────────────────────────────────

def check_attachment_parsing(cfg, docs):
    from urllib.parse import urlparse
    from wiki_quiz.attachment_parser import parse_attachment

    outline_host = urlparse(cfg.outline_api_url).netloc
    attachments = []
    for d in docs:
        for url in d.attachment_urls:
            parsed = parse_attachment(
                url, name=url.rsplit("/", 1)[-1],
                auth_token=cfg.outline_api_key, trusted_host=outline_host,
            )
            if parsed is not None:
                attachments.append(parsed)
    print(f"       -> 첨부 링크 중 파싱 성공 {len(attachments)}건 "
          f"(첨부 링크 자체가 0개면 이 단계는 통과만 하고 실질적으로 검증할 게 없음)")
    return attachments


# ── 5. 샘플링 ────────────────────────────────────────────────────────

def check_sampling(cfg, docs, attachments):
    from wiki_quiz.sampler import build_chunks, sample_chunks
    all_chunks = build_chunks(docs, attachments)
    assert all_chunks, "청크가 하나도 안 만들어짐 (문서 본문이 비어있을 가능성)"
    sampled = sample_chunks(all_chunks, cfg.sample_chunk_count)
    print(f"       -> 전체 청크 {len(all_chunks)}개 중 {len(sampled)}개 샘플링")
    return sampled


# ── 6. 퀴즈 생성 ─────────────────────────────────────────────────────

def check_quiz_generation(cfg, sampled):
    from wiki_quiz.quiz_generator import generate_quiz
    quiz_api_key = cfg.gemini_api_key if cfg.quiz_provider == "gemini" else cfg.anthropic_api_key
    questions = generate_quiz(sampled, cfg.question_count, cfg.quiz_model, quiz_api_key, cfg.quiz_provider)
    assert questions, "퀴즈가 하나도 생성되지 않음"
    for q in questions:
        assert len(q.choices) == 4, f"보기가 4개가 아님: {q.choices}"
        assert 0 <= q.answer_index <= 3, f"answer_index 범위 밖: {q.answer_index}"
    print(f"       -> {cfg.quiz_provider}/{cfg.quiz_model}로 문제 {len(questions)}개 생성 확인")
    for i, q in enumerate(questions, 1):
        print(f"          Q{i}. {q.question[:60]}{'...' if len(q.question) > 60 else ''}")
    return questions


# ── 7. 전달 미리보기 / 실제 전송 ─────────────────────────────────────

def check_delivery_preview(cfg, questions, actually_send):
    if cfg.delivery_mode != "discord":
        # Discord 외 채널(slack/google_chat/email/outline)은 이 스크립트가 실전송 로직을
        # 검증한 적 없는 경로라, --send를 줘도 항상 CLI 포맷 미리보기로만 안전하게 처리한다.
        from wiki_quiz.delivery import cli
        cli.deliver(questions)
        print(f"       -> delivery_mode={cfg.delivery_mode!r} — 이 스크립트는 Discord 외에는 "
              f"항상 CLI 미리보기만 함 (실제 외부 발송 안전장치, --send 무시됨)")
        return

    from wiki_quiz.delivery import discord as discord_delivery
    messages = discord_delivery._format_messages(questions)
    print(f"       -> Discord 메시지 {len(messages)}개로 분할됨 (각 {[len(m) for m in messages]}자)")
    print("       --- 미리보기 (실제로는 전송되지 않음, 아래 첫 메시지만 일부 출력) ---")
    preview = messages[0][:300]
    for line in preview.splitlines():
        print(f"       | {line}")
    if len(messages[0]) > 300:
        print("       | ...(생략)...")

    if not actually_send:
        print("       -> --send 플래그가 없어 실제 전송은 건너뜀")
        return

    if not cfg.discord_webhook_url:
        raise RuntimeError("--send를 줬지만 DISCORD_WEBHOOK_URL이 설정되지 않음")
    discord_delivery.deliver(questions, cfg)
    print("       -> 실제로 Discord에 전송 완료 — 채널을 확인하세요")


def main():
    actually_send = "--send" in sys.argv or os.environ.get("E2E_ACTUALLY_SEND") == "1"
    if actually_send:
        print("⚠️  --send 모드: delivery_mode=discord면 마지막 단계에서 실제로 채널에 전송합니다.\n")

    ok, _ = check("0. Python 버전 확인 (>= 3.10)", check_python_version)
    if not ok:
        sys.exit(1)

    ok, cfg = check("1. 환경변수 + config 로드 (문서 ID 보안 고정 포함)", check_config_loads)
    if not ok:
        print("\n환경변수부터 잘못됐습니다. .env 확인 필요. 이후 단계는 건너뜁니다.")
        sys.exit(1)

    ok, _ = check("2. Outline 인증 (auth.info)", lambda: check_outline_auth(cfg))
    if not ok:
        sys.exit(1)

    ok, docs = check("3. Outline 실제 크롤링 (collect_document_tree)", lambda: check_real_crawl(cfg))
    if not ok:
        sys.exit(1)

    ok, attachments = check("4. 첨부파일 파싱", lambda: check_attachment_parsing(cfg, docs))
    if not ok:
        attachments = []  # 첨부파일 실패해도 나머지 단계는 계속 진행 가능

    ok, sampled = check("5. 샘플링 (build_chunks + sample_chunks)", lambda: check_sampling(cfg, docs, attachments))
    if not ok:
        sys.exit(1)

    ok, questions = check("6. 퀴즈 생성 (실제 LLM 호출)", lambda: check_quiz_generation(cfg, sampled))
    if not ok:
        sys.exit(1)

    label = "+ 실제 전송" if (actually_send and cfg.delivery_mode == "discord") else "미리보기"
    ok, _ = check(f"7. 전달 {label} (delivery_mode={cfg.delivery_mode})",
                  lambda: check_delivery_preview(cfg, questions, actually_send))

    print()
    if ok:
        print("모든 핵심 기능이 정상 동작합니다.")
        if cfg.delivery_mode == "discord" and not actually_send:
            print("실제 Discord 전송까지 확인하려면: python3 tests/e2e_smoke_test.py --send")
        sys.exit(0)
    else:
        print("일부 단계 실패. 위 [FAIL] 로그의 에러 메시지를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
