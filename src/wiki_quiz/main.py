"""
전체 파이프라인 오케스트레이션 entrypoint.

실행: python -m src.wiki_quiz.main
매일 GitHub Actions cron이 이 모듈을 그대로 호출한다.
"""

from urllib.parse import urlparse

from config import load_config
from wiki_quiz.attachment_parser import parse_attachment
from wiki_quiz.delivery import deliver
from wiki_quiz.outline_client import OutlineWikiCrawler
from wiki_quiz.quiz_generator import generate_quiz
from wiki_quiz.sampler import build_chunks, sample_chunks


def run() -> None:
    """1~5단계를 순서대로 실행하는 오케스트레이션."""
    cfg = load_config()

    with OutlineWikiCrawler(cfg.outline_api_url, cfg.outline_api_key) as crawler:
        # OUTLINE_DOCUMENT_ID가 설정되어 있으면 그 문서(+하위 트리)만, 아니면 컬렉션 전체를 순회한다.
        if cfg.outline_document_id:
            docs = crawler.collect_document_tree(cfg.outline_document_id)
        else:
            docs = crawler.collect_all_documents(cfg.outline_root_collection_id)

    # NOTE: 첨부 URL이 인증 필요 프록시 URL인지 아직 미확인이라(README 참고),
    # Outline API 키를 Authorization 헤더로 함께 실어 보낸다 — 단, 보안상 다운로드
    # 대상 host가 우리 Outline 인스턴스(outline_host)와 일치할 때만. 위키 본문 링크는
    # 제3자 도메인일 수 있어서, 무조건 붙이면 그쪽으로 API 키가 유출될 수 있다.
    outline_host = urlparse(cfg.outline_api_url).netloc
    attachments = [
        parsed
        for d in docs
        for url in d.attachment_urls
        for parsed in [
            parse_attachment(
                url,
                name=url.rsplit("/", 1)[-1],
                auth_token=cfg.outline_api_key,
                trusted_host=outline_host,
            )
        ]
        if parsed is not None
    ]

    all_chunks = build_chunks(docs, attachments)
    sampled = sample_chunks(all_chunks, cfg.sample_chunk_count)

    questions = generate_quiz(sampled, cfg.question_count, cfg.quiz_model, cfg.anthropic_api_key)

    deliver(cfg.delivery_mode, questions, cfg)


if __name__ == "__main__":
    run()
