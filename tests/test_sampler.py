"""sampler.py 단위 테스트."""

from wiki_quiz.attachment_parser import ParsedAttachment
from wiki_quiz.outline_client import WikiDocument
from wiki_quiz.sampler import TextChunk, build_chunks, sample_chunks


def test_sample_chunks_returns_requested_count():
    chunks = [TextChunk(source=f"b{i}", text=f"text {i}") for i in range(50)]
    sampled = sample_chunks(chunks, count=15, seed=42)
    assert len(sampled) == 15


def test_sample_chunks_returns_all_when_fewer_than_count():
    chunks = [TextChunk(source="b0", text="only one")]
    sampled = sample_chunks(chunks, count=15, seed=42)
    assert sampled == chunks


def test_sample_chunks_is_deterministic_with_seed():
    chunks = [TextChunk(source=f"b{i}", text=f"text {i}") for i in range(50)]
    a = sample_chunks(chunks, count=10, seed=1)
    b = sample_chunks(chunks, count=10, seed=1)
    assert a == b


def _make_doc(document_id: str, text: str | None) -> WikiDocument:
    return WikiDocument(
        document_id=document_id,
        title=document_id,
        text=text,
        parent_document_id=None,
        collection_id="col1",
        attachment_urls=[],
    )


def test_build_chunks_splits_long_document_text():
    long_text = "\n\n".join(f"문단 {i} " + ("가" * 100) for i in range(10))
    docs = [_make_doc("doc1", long_text)]

    chunks = build_chunks(docs, attachments=[], max_len=200)

    assert len(chunks) > 1
    assert all(len(c.text) <= 200 for c in chunks)
    assert all(c.source == "doc1" for c in chunks)


def test_build_chunks_skips_documents_without_text():
    docs = [_make_doc("doc1", None), _make_doc("doc2", "짧은 본문")]

    chunks = build_chunks(docs, attachments=[])

    assert len(chunks) == 1
    assert chunks[0].source == "doc2"


def test_build_chunks_includes_attachment_text():
    docs = [_make_doc("doc1", "본문")]
    attachments = [ParsedAttachment(name="spec.pdf", text="첨부파일 내용")]

    chunks = build_chunks(docs, attachments)

    sources = {c.source for c in chunks}
    assert "doc1" in sources
    assert "spec.pdf" in sources
