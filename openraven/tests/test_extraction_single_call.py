import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openraven.extraction.extractor import Entity, ExtractionResult, extract_entities


SCHEMA = {
    "prompt_description": "Extract people, organizations, and concepts from the text.",
    "examples": [],
}


def _fake_gemini_response(entities: list[dict]) -> AsyncMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps({"entities": entities}, ensure_ascii=False)
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


@pytest.mark.asyncio
async def test_extract_entities_single_call_returns_entities_with_offsets():
    text = "Alice works at Acme Corp on the distributed log project."
    client = _fake_gemini_response([
        {"extraction_text": "Alice",     "extraction_class": "Person",       "attributes": {}},
        {"extraction_text": "Acme Corp", "extraction_class": "Organization", "attributes": {}},
    ])

    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(
            text=text, source_document="doc.md", schema=SCHEMA, model_id="gemini-2.5-flash",
        )

    assert isinstance(result, ExtractionResult)
    names = [e.name for e in result.entities]
    assert names == ["Alice", "Acme Corp"]
    alice = result.entities[0]
    assert alice.char_start == text.index("Alice")
    assert alice.char_end == alice.char_start + len("Alice")
    assert alice.entity_type == "Person"
    assert alice.source_document == "doc.md"
    # ONE call, not chunked
    assert client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_extract_entities_drops_hallucinated_spans():
    """LLM returns an entity whose text is not found in the source — it must be dropped."""
    text = "Alice works at Acme."
    client = _fake_gemini_response([
        {"extraction_text": "Alice",            "extraction_class": "Person", "attributes": {}},
        {"extraction_text": "Nonexistent Corp", "extraction_class": "Org",    "attributes": {}},
    ])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "doc.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["Alice"]


@pytest.mark.asyncio
async def test_extract_entities_cjk_text():
    text = "台積電股價今日上漲, 本益比為25倍"
    client = _fake_gemini_response([
        {"extraction_text": "台積電",  "extraction_class": "上市公司",       "attributes": {}},
        {"extraction_text": "本益比", "extraction_class": "financial_metric", "attributes": {"value": "25"}},
    ])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "zh.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["台積電", "本益比"]
    assert result.entities[0].attributes == {}
    assert result.entities[1].attributes == {"value": "25"}


def test_build_prompt_normalizes_langextract_example_dataclasses():
    """Real schemas use langextract.ExampleData; they must become structured JSON, not repr() strings."""
    from openraven.extraction.extractor import _build_prompt
    from langextract.core.data import ExampleData, Extraction

    schema = {
        "prompt_description": "extract",
        "examples": [
            ExampleData(
                text="Alice works at Acme.",
                extractions=[
                    Extraction(extraction_class="Person", extraction_text="Alice"),
                    Extraction(extraction_class="Organization", extraction_text="Acme"),
                ],
            ),
        ],
    }

    prompt = _build_prompt(schema, "some doc text")

    # Must NOT contain Python repr artifacts like 'ExampleData(', 'Extraction(', 'char_interval=None'
    assert "ExampleData(" not in prompt
    assert "Extraction(" not in prompt
    assert "char_interval" not in prompt
    # Must contain the structured JSON keys
    assert '"extraction_text": "Alice"' in prompt
    assert '"extraction_class": "Person"' in prompt
    assert '"entities":' in prompt
    # And the output-shape entities list (not a flat list of Extraction reprs)
    assert '"text": "Alice works at Acme."' in prompt


def test_build_prompt_handles_dict_examples():
    """Plain-dict examples (used in tests) must still work identically."""
    from openraven.extraction.extractor import _build_prompt

    schema = {
        "prompt_description": "extract",
        "examples": [
            {"text": "Bob drinks tea.", "extractions": [{"extraction_class": "Person", "extraction_text": "Bob"}]},
        ],
    }
    prompt = _build_prompt(schema, "doc")
    assert '"extraction_text": "Bob"' in prompt
    assert '"text": "Bob drinks tea."' in prompt


@pytest.mark.asyncio
async def test_extract_retries_on_json_decode_error():
    """First Gemini response is invalid JSON, second is valid → final result succeeds."""
    bad_resp  = MagicMock(); bad_resp.choices  = [MagicMock()]; bad_resp.choices[0].message.content  = "not-json{{{"
    good_resp = MagicMock(); good_resp.choices = [MagicMock()]; good_resp.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Alice", "extraction_class": "Person", "attributes": {}},
    ]})
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=[bad_resp, good_resp])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities("Alice works here.", "doc.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["Alice"]
    assert client.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_extract_chunks_on_repeated_failure():
    """Both attempts on the full doc fail → fall back to chunked extraction and merge."""
    bad = MagicMock(); bad.choices = [MagicMock()]; bad.choices[0].message.content = "not-json"
    chunk_ok_a = MagicMock(); chunk_ok_a.choices = [MagicMock()]; chunk_ok_a.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Alice", "extraction_class": "Person", "attributes": {}},
    ]})
    chunk_ok_b = MagicMock(); chunk_ok_b.choices = [MagicMock()]; chunk_ok_b.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Acme", "extraction_class": "Org", "attributes": {}},
    ]})
    client = AsyncMock()
    # sequence: full-doc attempt 1 fails, full-doc retry fails, then 2 chunk calls succeed
    client.chat.completions.create = AsyncMock(side_effect=[bad, bad, chunk_ok_a, chunk_ok_b])
    # Text sized to split into exactly 2 chunks at CHUNK_SIZE_CHARS=8000.
    # "Alice works here. "=18 chars * 300 = 5400. "Acme is a company. "=19 * 300 = 5700. Total 11100 → 2 chunks.
    text = ("Alice works here. " * 300) + ("Acme is a company. " * 300)
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "doc.md", SCHEMA, "gemini-2.5-flash")
    assert {e.name for e in result.entities} == {"Alice", "Acme"}
    assert client.chat.completions.create.await_count >= 3


@pytest.mark.asyncio
async def test_extract_handles_empty_choices_and_falls_through():
    """If Gemini returns empty choices (content-safety block), treat as malformed and retry/chunk.

    This prevents IndexError on resp.choices[0] from crashing the pipeline.
    """
    empty = MagicMock(); empty.choices = []
    good = MagicMock(); good.choices = [MagicMock()]; good.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Alice", "extraction_class": "Person", "attributes": {}},
    ]})
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=[empty, good])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities("Alice works here.", "doc.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["Alice"]


@pytest.mark.asyncio
async def test_extract_entities_handles_bare_list_response():
    """Gemini sometimes returns a raw JSON array instead of {"entities": [...]}.

    Must be treated as a happy-path response, not an error to retry.
    """
    text = "Alice works at Acme."
    resp = MagicMock()
    resp.choices = [MagicMock()]
    # Bare list at top level — no "entities" wrapper
    resp.choices[0].message.content = json.dumps([
        {"extraction_text": "Alice", "extraction_class": "Person", "attributes": {}},
        {"extraction_text": "Acme",  "extraction_class": "Org",    "attributes": {}},
    ])
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=resp)

    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "doc.md", SCHEMA, "gemini-2.5-flash")

    assert {e.name for e in result.entities} == {"Alice", "Acme"}
    # Exactly ONE call — bare list must be treated as success, not failure to retry
    assert client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_extract_entities_unexpected_shape_returns_empty():
    """If Gemini returns something that's neither a list nor a dict (e.g. a string), return no entities."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps("some random string")
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=resp)

    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities("x", "d.md", SCHEMA, "gemini-2.5-flash")

    assert result.entities == []
