from __future__ import annotations

from rapidfuzz import fuzz


FUZZY_MIN_SCORE = 70.0


def align_span(haystack: str, needle: str) -> tuple[int | None, int | None]:
    """Return (start, end) char offsets of `needle` inside `haystack`.

    Exact substring match first. If not found, falls back to
    rapidfuzz.partial_ratio_alignment to recover from minor drift
    (whitespace, CJK normalization, small paraphrase). Returns
    (None, None) when neither approach produces a confident match.
    """
    if not needle:
        return (None, None)

    idx = haystack.find(needle)
    if idx >= 0:
        return (idx, idx + len(needle))

    align = fuzz.partial_ratio_alignment(needle, haystack)
    if align is None or align.score < FUZZY_MIN_SCORE:
        return (None, None)
    return (align.dest_start, align.dest_end)
