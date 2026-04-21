from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import langextract as lx


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


def _run_langextract(text: str, schema: dict, model_id: str):
    # Defaults (max_char_buffer=1000, max_workers=10, batch_length=10) split a
    # 77K-char doc into 77 tiny chunks processed in 8 sequential batches ~= 7min.
    # Larger chunks + more parallel workers bring this under 1 min on Gemini flash.
    return lx.extract(
        text_or_documents=text,
        prompt_description=schema["prompt_description"],
        examples=schema.get("examples", []),
        model_id=model_id,
        max_char_buffer=5000,
        max_workers=20,
        batch_length=20,
    )


async def extract_entities(
    text: str,
    source_document: str,
    schema: dict,
    model_id: str = "gemini-2.5-flash",
) -> ExtractionResult:
    result = await asyncio.to_thread(_run_langextract, text, schema, model_id)

    entities = []
    for extraction in result.extractions:
        char_interval = getattr(extraction, "char_interval", None)
        extraction_text = getattr(extraction, "extraction_text", str(extraction))
        extraction_class = getattr(extraction, "extraction_class", "concept")
        attributes = getattr(extraction, "attributes", {})

        entities.append(Entity(
            name=extraction_text,
            entity_type=extraction_class,
            context=extraction_text,
            source_document=source_document,
            char_start=getattr(char_interval, "start", None) if char_interval else None,
            char_end=getattr(char_interval, "end", None) if char_interval else None,
            attributes=attributes if isinstance(attributes, dict) else {},
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
