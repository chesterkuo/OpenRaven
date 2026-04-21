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
