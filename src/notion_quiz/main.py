"""
전체 파이프라인 오케스트레이션 entrypoint.

실행: python -m src.notion_quiz.main
매일 GitHub Actions cron이 이 모듈을 그대로 호출한다.
"""

from config import load_config
from notion_quiz.attachment_parser import parse_attachment
from notion_quiz.delivery import deliver
from notion_quiz.notion_client import NotionWikiCrawler
from notion_quiz.quiz_generator import generate_quiz
from notion_quiz.sampler import build_chunks, sample_chunks


def run() -> None:
    """
    SUDO:
      cfg = load_config()

      # 1. 위키 순회 수집
      crawler = NotionWikiCrawler(cfg.notion_api_key)
      blocks = crawler.collect_all_blocks(cfg.notion_root_page_id)

      # 2. 첨부파일 다운로드·파싱
      attachments = []
      for b in blocks where b.attachment_url:
          parsed = parse_attachment(b.attachment_url, b.attachment_name)
          if parsed: attachments.append(parsed)

      # 3. 랜덤 샘플링
      all_chunks = build_chunks(blocks, attachments)
      sampled = sample_chunks(all_chunks, cfg.sample_chunk_count)

      # 4. Claude API로 퀴즈 생성
      questions = generate_quiz(sampled, cfg.question_count, cfg.quiz_model, cfg.anthropic_api_key)

      # 5. 결과 전달
      deliver(cfg.delivery_mode, questions, cfg)
    """
    cfg = load_config()

    crawler = NotionWikiCrawler(cfg.notion_api_key)
    blocks = crawler.collect_all_blocks(cfg.notion_root_page_id)

    attachments = [
        parsed
        for b in blocks
        if b.attachment_url
        for parsed in [parse_attachment(b.attachment_url, b.attachment_name)]
        if parsed is not None
    ]

    all_chunks = build_chunks(blocks, attachments)
    sampled = sample_chunks(all_chunks, cfg.sample_chunk_count)

    questions = generate_quiz(sampled, cfg.question_count, cfg.quiz_model, cfg.anthropic_api_key)

    deliver(cfg.delivery_mode, questions, cfg)


if __name__ == "__main__":
    run()
