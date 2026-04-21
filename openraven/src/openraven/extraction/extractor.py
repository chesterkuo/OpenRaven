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


def _build_prompt(schema: dict, text: str) -> str:
    parts = [schema.get("prompt_description", "")]
    examples = schema.get("examples") or []
    if examples:
        parts.append("\n\nExamples:\n" + json.dumps(examples, ensure_ascii=False, default=str))
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
    raw_entities = await _extract_single_call(text, schema, model_id, api_key, base_url)

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
