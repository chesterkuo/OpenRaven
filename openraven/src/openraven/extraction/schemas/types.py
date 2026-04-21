"""Minimal schema types for extraction examples.

These replace `langextract.core.data.ExampleData` / `Extraction` so the
runtime dependency on LangExtract can be removed. Field names match the
original so `_normalize_examples` in extractor.py works without change.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Extraction:
    extraction_class: str
    extraction_text: str
    attributes: dict = field(default_factory=dict)


@dataclass
class Example:
    text: str
    extractions: list[Extraction] = field(default_factory=list)
