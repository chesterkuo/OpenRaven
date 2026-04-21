from openraven.extraction.alignment import align_span


def test_exact_match_returns_native_offsets():
    text = "Kafka is a distributed event streaming platform."
    start, end = align_span(text, "distributed event streaming")
    assert (start, end) == (11, 38)
    assert text[start:end] == "distributed event streaming"


def test_no_match_returns_none():
    start, end = align_span("some text", "completely unrelated string that is long enough to fail")
    assert (start, end) == (None, None)


def test_fuzzy_match_recovers_near_miss():
    # Simulate a tokenizer echoing a normalized form; the haystack has the raw original.
    # 'distributed log' is not a literal substring but partial_ratio finds the closest slice.
    text = "Kafka is a distributed event streaming platform for log pipelines."
    start, end = align_span(text, "distributed log")
    assert start is not None and end is not None
    assert 0 <= start < end <= len(text)


def test_cjk_exact_match():
    text = "BOXVERSE Intelligence Platform V3.3 — 產品功能總覽"
    start, end = align_span(text, "產品功能總覽")
    assert text[start:end] == "產品功能總覽"


def test_empty_needle_returns_none():
    start, end = align_span("anything", "")
    assert (start, end) == (None, None)
