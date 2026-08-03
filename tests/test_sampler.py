"""sampler.py 단위 테스트 스켈레톤."""

from notion_quiz.sampler import TextChunk, sample_chunks


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
