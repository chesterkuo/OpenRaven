from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import openai

from openraven.extraction.alignment import align_span


@dataclass
class Entity:
    name: str
    entity_type: str
    context: str
    source_document: str
    char_start: int | None = None
    char_end: int | None = None
    attributes: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    entities: list[Entity]
    source_document: str


_SYSTEM = (
    "You are an information-extraction system. Return a JSON object with a single key "
    '"entities" whose value is an array of objects. Each object must have keys '
    '"extraction_text" (verbatim span copied character-for-character from the document), '
    '"extraction_class" (the entity type label), and optional "attributes" (object). '
    "Do not invent text that is not present. Do not return character offsets — only the "
    "verbatim span. Output JSON only, no prose."
)


def _normalize_examples(examples: list) -> list[dict]:
    """Convert langextract ExampleData/Extraction dataclass instances (or dicts)
    into the structured JSON shape the LLM is asked to produce.

    Robust to both dataclass instances and plain dicts.
    """
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    normalized: list[dict] = []
    for ex in examples:
        text = _get(ex, "text", "") or ""
        extractions = _get(ex, "extractions", []) or []
        normalized.append({
            "text": text,
            "entities": [
                {
                    "extraction_text": _get(e, "extraction_text", "") or "",
                    "extraction_class": _get(e, "extraction_class", "") or "",
                    "attributes": _get(e, "attributes", {}) or {},
                }
                for e in extractions
            ],
        })
    return normalized


def _build_prompt(schema: dict, text: str) -> str:
    parts = [schema.get("prompt_description", "")]
    examples = schema.get("examples") or []
    if examples:
        normalized = _normalize_examples(examples)
        parts.append("\n\nExamples:\n" + json.dumps(normalized, ensure_ascii=False))
    parts.append("\n\nDocument:\n" + text)
    return "".join(parts)


async def _extract_single_call(
    text: str, schema: dict, model_id: str, api_key: str, base_url: str,
) -> list[dict]:
    client = openai.AsyncOpenAI(api_key=api_key or "none", base_url=base_url)
    resp = await client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(schema, text)},
        ],
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return data.get("entities", []) or []


CHUNK_SIZE_CHARS = 8000      # happy-path single-call preferred; only used on retry failure


async def _try_single_call(
    text: str, schema: dict, model_id: str, api_key: str, base_url: str,
) -> list[dict] | None:
    """Single call returning parsed entities, or None on malformed/empty response.

    Catches json.JSONDecodeError (truncation/repetition bugs) and IndexError
    (empty choices from content-safety blocks) so the caller can retry or chunk.
    """
    try:
        return await _extract_single_call(text, schema, model_id, api_key, base_url)
    except (json.JSONDecodeError, ValueError, IndexError, AttributeError):
        return None


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [text]


async def extract_entities(
    text: str,
    source_document: str,
    schema: dict,
    model_id: str = "gemini-2.5-flash",
) -> ExtractionResult:
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get(
        "OPENRAVEN_LLM_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    raw_entities: list[dict] | None = None
    # Happy path: one call. Retry once on malformed JSON / empty choices (known flash quirk).
    for _ in range(2):
        raw_entities = await _try_single_call(text, schema, model_id, api_key, base_url)
        if raw_entities is not None:
            break

    # Fallback: chunk and merge. Only kicks in on repeated failure.
    if raw_entities is None:
        raw_entities = []
        seen = set()
        for chunk in _chunk_text(text, CHUNK_SIZE_CHARS):
            items = await _try_single_call(chunk, schema, model_id, api_key, base_url) or []
            for item in items:
                key = (item.get("extraction_text", ""), item.get("extraction_class", ""))
                if key in seen:
                    continue
                seen.add(key)
                raw_entities.append(item)

    entities: list[Entity] = []
    for item in raw_entities:
        span = (item.get("extraction_text") or "").strip()
        if not span:
            continue
        start, end = align_span(text, span)
        if start is None:
            continue                       # drop hallucinated / unalignable spans
        entities.append(Entity(
            name=span,
            entity_type=item.get("extraction_class") or "concept",
            context=span,
            source_document=source_document,
            char_start=start,
            char_end=end,
            attributes=item.get("attributes") if isinstance(item.get("attributes"), dict) else {},
        ))

    return ExtractionResult(entities=entities, source_document=source_document)


def enrich_text_for_rag(text: str, extraction_result: ExtractionResult) -> str:
    if not extraction_result.entities:
        return text

    entity_lines = []
    for e in extraction_result.entities:
        loc = ""
        if e.char_start is not None and e.char_end is not None:
            loc = f" [source:{e.source_document}:{e.char_start}-{e.char_end}]"
        entity_lines.append(f"[ENTITY:{e.entity_type}] {e.name}{loc}")

    header = "=== Extracted Entities ===\n" + "\n".join(entity_lines) + "\n=== End Entities ===\n\n"
    return header + text
