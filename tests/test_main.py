"""main.py 단위 테스트 — 오케스트레이션 배선(어떤 함수를 어떤 인자로 부르는지)만 검증.

실제 Outline/LLM 네트워크 호출은 전부 가짜로 치환한다. 개별 모듈의 로직 자체는
각자의 테스트 파일(test_config.py, test_quiz_generator.py 등)에서 이미 검증하므로,
여기서는 main.run()이 그 조각들을 올바른 순서·인자로 연결하는지만 확인한다.
"""

import config as config_module
from wiki_quiz import main
from wiki_quiz.attachment_parser import ParsedAttachment
from wiki_quiz.outline_client import WikiDocument
from wiki_quiz.quiz_generator import QuizQuestion


def _make_config(**overrides) -> config_module.Config:
    base = dict(
        outline_api_url="https://wiki.class.day/api",
        outline_api_key="outline-key",
        outline_root_collection_id=None,
        outline_document_id="mOuXpLufUA",
        quiz_provider="gemini",
        anthropic_api_key=None,
        gemini_api_key="gemini-key",
        quiz_model="gemini-3.5-flash-lite",
        sample_chunk_count=15,
        question_count=3,
        delivery_mode="cli",
        outline_quiz_log_collection_id=None,
        slack_webhook_url=None,
        discord_webhook_url=None,
        google_chat_webhook_url=None,
        smtp_host=None,
        smtp_port=None,
        smtp_user=None,
        smtp_app_password=None,
        email_to=None,
    )
    base.update(overrides)
    return config_module.Config(**base)


def _fake_doc(attachment_urls=None) -> WikiDocument:
    return WikiDocument(
        document_id="d1",
        title="문서1",
        text="본문 내용입니다.",
        parent_document_id=None,
        collection_id="c1",
        attachment_urls=attachment_urls or [],
    )


def _fake_questions() -> list[QuizQuestion]:
    return [QuizQuestion(question="Q", choices=["A", "B", "C", "D"], answer_index=0,
                          explanation="해설", source="d1")]


class _FakeCrawler:
    """OutlineWikiCrawler 대신 쓰는 가짜 — 어떤 메서드가 어떤 인자로 불렸는지만 기록한다."""

    last_call: tuple[str, str] | None = None
    docs: list[WikiDocument] = []

    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass

    def collect_document_tree(self, root_document_id):
        _FakeCrawler.last_call = ("collect_document_tree", root_document_id)
        return _FakeCrawler.docs

    def collect_all_documents(self, root_collection_id):
        _FakeCrawler.last_call = ("collect_all_documents", root_collection_id)
        return _FakeCrawler.docs


def _patch_common(monkeypatch, cfg, docs=None, generate_quiz=None, deliver=None, parse_attachment=None):
    """네 개 의존성(load_config/크롤러/generate_quiz/deliver)을 한 번에 갈아끼운다."""
    _FakeCrawler.last_call = None
    _FakeCrawler.docs = docs if docs is not None else [_fake_doc()]
    monkeypatch.setattr(main, "load_config", lambda: cfg)
    monkeypatch.setattr(main, "OutlineWikiCrawler", _FakeCrawler)
    monkeypatch.setattr(main, "parse_attachment", parse_attachment or (lambda *a, **k: None))
    monkeypatch.setattr(main, "generate_quiz", generate_quiz or (lambda *a, **k: _fake_questions()))
    monkeypatch.setattr(main, "deliver", deliver or (lambda *a, **k: None))


def test_run_uses_collect_document_tree_when_document_id_set(monkeypatch):
    cfg = _make_config(outline_document_id="mOuXpLufUA")
    _patch_common(monkeypatch, cfg)

    main.run()

    assert _FakeCrawler.last_call == ("collect_document_tree", "mOuXpLufUA")


def test_run_uses_collect_all_documents_when_no_document_id(monkeypatch):
    cfg = _make_config(outline_document_id=None, outline_root_collection_id="col-1")
    _patch_common(monkeypatch, cfg)

    main.run()

    assert _FakeCrawler.last_call == ("collect_all_documents", "col-1")


def test_run_selects_gemini_api_key_for_gemini_provider(monkeypatch):
    cfg = _make_config(quiz_provider="gemini", gemini_api_key="g-key", anthropic_api_key=None)
    captured = {}

    def fake_generate_quiz(chunks, count, model, api_key, provider):
        captured["api_key"] = api_key
        captured["provider"] = provider
        return _fake_questions()

    _patch_common(monkeypatch, cfg, generate_quiz=fake_generate_quiz)

    main.run()

    assert captured == {"api_key": "g-key", "provider": "gemini"}


def test_run_selects_anthropic_api_key_for_claude_provider(monkeypatch):
    cfg = _make_config(quiz_provider="claude", gemini_api_key=None, anthropic_api_key="a-key",
                        quiz_model="claude-haiku-4-5")
    captured = {}

    def fake_generate_quiz(chunks, count, model, api_key, provider):
        captured["api_key"] = api_key
        captured["provider"] = provider
        return _fake_questions()

    _patch_common(monkeypatch, cfg, generate_quiz=fake_generate_quiz)

    main.run()

    assert captured == {"api_key": "a-key", "provider": "claude"}


def test_run_forwards_delivery_mode_and_questions_and_config_to_deliver(monkeypatch):
    cfg = _make_config(delivery_mode="discord")
    questions = _fake_questions()
    captured = {}

    def fake_deliver(mode, qs, config):
        captured["mode"] = mode
        captured["questions"] = qs
        captured["config"] = config

    _patch_common(monkeypatch, cfg, generate_quiz=lambda *a, **k: questions, deliver=fake_deliver)

    main.run()

    assert captured["mode"] == "discord"
    assert captured["questions"] == questions
    assert captured["config"] is cfg


def test_run_only_sends_auth_token_to_trusted_outline_host(monkeypatch):
    """attachment_urls가 있으면 parse_attachment가 outline_host를 trusted_host로 받는지
    확인 — API 키가 다른 host로 새어나가지 않게 하는 배선 검증 (main.py NOTE 참고).
    """
    cfg = _make_config(outline_api_url="https://wiki.class.day/api", outline_api_key="outline-key")
    captured = {}

    def fake_parse_attachment(url, name, auth_token, trusted_host):
        captured["url"] = url
        captured["auth_token"] = auth_token
        captured["trusted_host"] = trusted_host
        return ParsedAttachment(name=name, text="첨부 내용")

    docs = [_fake_doc(attachment_urls=["https://wiki.class.day/files/a.pdf"])]
    _patch_common(monkeypatch, cfg, docs=docs, parse_attachment=fake_parse_attachment)

    main.run()

    assert captured["trusted_host"] == "wiki.class.day"
    assert captured["auth_token"] == "outline-key"
    assert captured["url"] == "https://wiki.class.day/files/a.pdf"
