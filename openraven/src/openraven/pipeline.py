from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from openraven.config import RavenConfig
from openraven.extraction.extractor import (
    Entity,
    enrich_text_for_rag,
    extract_entities,
)
from openraven.extraction.schemas.base import BASE_SCHEMA
from openraven.graph.rag import RavenGraph
from openraven.health.reporter import HealthReport, generate_health_report
from openraven.ingestion.hasher import compute_file_hash
from openraven.ingestion.parser import ParsedDocument, parse_document
from openraven.storage import FileRecord, MetadataStore
from openraven.wiki.compiler import compile_wiki_for_graph

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".html"}


@dataclass
class PipelineResult:
    files_processed: int
    entities_extracted: int
    articles_generated: int
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def _detect_schema(file_path: Path, text: str = "") -> dict:
    name = file_path.name.lower()
    eng_keywords = ("adr", "architecture", "spec", "technical", "design", "system", "api", "infra")
    fin_keywords = (
        "research", "earnings", "financial", "valuation", "report", "investment", "analysis"
    )

    if any(kw in name for kw in eng_keywords):
        from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
        return ENGINEERING_SCHEMA
    elif any(kw in name for kw in fin_keywords):
        from openraven.extraction.schemas.finance import FINANCE_SCHEMA
        return FINANCE_SCHEMA

    sample = text[:2000].lower() if text else ""
    fin_content = (
        "revenue", "p/e", "earnings", "valuation", "market cap", "股價", "營收", "本益比", "殖利率"
    )
    eng_content = (
        "architecture", "microservice", "api endpoint", "database", "deploy", "kubernetes", "docker"
    )

    if any(kw in sample for kw in fin_content):
        from openraven.extraction.schemas.finance import FINANCE_SCHEMA
        return FINANCE_SCHEMA
    elif any(kw in sample for kw in eng_content):
        from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
        return ENGINEERING_SCHEMA

    return BASE_SCHEMA


class RavenPipeline:
    def __init__(self, config: RavenConfig) -> None:
        self.config = config
        self.store = MetadataStore(config.db_path)
        self.graph = RavenGraph.create_lazy(
            working_dir=config.lightrag_dir,
            llm_model=config.llm_model,
            llm_api_key=config.gemini_api_key,
        )

    async def add_files(self, paths: list[Path]) -> PipelineResult:
        errors: list[str] = []
        all_entities: list[Entity] = []
        sources_map: dict[str, list[dict]] = {}

        file_paths = self._expand_paths(paths)
        files_to_process = self._filter_unchanged(file_paths)

        if not files_to_process:
            logger.info("No new or changed files to process.")
            return PipelineResult(0, 0, 0)

        # Stage 1: Ingestion
        parsed_docs: list[ParsedDocument] = []
        for fp in files_to_process:
            try:
                doc = parse_document(fp)
                parsed_docs.append(doc)
                fp_path = Path(fp) if not isinstance(fp, Path) else fp
                self.store.upsert_file(FileRecord(
                    path=str(fp), hash=compute_file_hash(fp_path) if fp_path.exists() else "url",
                    format=doc.format, char_count=doc.char_count, status="ingested",
                ))
            except Exception as e:
                errors.append(f"Ingestion failed for {fp}: {e}")
                logger.error(f"Ingestion failed for {fp}", exc_info=True)

        # Stage 2: Extraction + Graph
        for doc in parsed_docs:
            try:
                schema = _detect_schema(doc.source_path, text=doc.text)
                result = await extract_entities(
                    text=doc.text, source_document=str(doc.source_path),
                    schema=schema, model_id=self.config.llm_model,
                )
                all_entities.extend(result.entities)

                for entity in result.entities:
                    sources_map.setdefault(entity.name, []).append({
                        "document": str(doc.source_path),
                        "excerpt": entity.context[:100],
                        "char_start": entity.char_start,
                        "char_end": entity.char_end,
                    })

                enriched = enrich_text_for_rag(doc.text, result)
                await self.graph.insert(enriched, source=str(doc.source_path))

                self.store.upsert_file(FileRecord(
                    path=str(doc.source_path),
                    hash=compute_file_hash(doc.source_path) if doc.source_path.exists() else "url",
                    format=doc.format, char_count=doc.char_count, status="graphed",
                ))
            except Exception as e:
                errors.append(f"Extraction/graph failed for {doc.source_path}: {e}")
                logger.error(f"Extraction failed for {doc.source_path}", exc_info=True)

        # Stage 3 & 4: Wiki Compilation
        entity_names = list({e.name for e in all_entities})[:50]
        articles = []
        if entity_names:
            try:
                articles = await compile_wiki_for_graph(
                    graph=self.graph, entities=entity_names, sources_map=sources_map,
                    api_key=self.config.gemini_api_key, output_dir=self.config.wiki_dir,
                    model=self.config.wiki_llm_model,
                )
            except Exception as e:
                errors.append(f"Wiki compilation failed: {e}")
                logger.error("Wiki compilation failed", exc_info=True)

        return PipelineResult(
            files_processed=len(parsed_docs),
            entities_extracted=len(all_entities),
            articles_generated=len(articles),
            errors=errors,
        )

    async def ask(self, question: str, mode: str = "mix") -> str:
        return await self.graph.query(question, mode=mode)

    def get_health_report(self) -> HealthReport:
        file_records = [
            {"path": r.path, "status": r.status, "char_count": r.char_count}
            for r in self.store.list_files()
        ]
        graph_stats = self.graph.get_stats()
        return generate_health_report(file_records, graph_stats)

    def _expand_paths(self, paths: list[Path | str]) -> list[Path | str]:
        result: list[Path | str] = []
        for p in paths:
            p_str = str(p)
            if p_str.startswith("http://") or p_str.startswith("https://"):
                result.append(p_str)
                continue
            p = Path(p).resolve()
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                        result.append(f)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                result.append(p)
        return result

    def _filter_unchanged(self, file_paths: list[Path | str]) -> list[Path | str]:
        changed: list[Path | str] = []
        for fp in file_paths:
            fp_str = str(fp)
            if fp_str.startswith("http://") or fp_str.startswith("https://"):
                changed.append(fp)
                continue
            current_hash = compute_file_hash(Path(fp))
            existing = self.store.get_file(fp_str)
            if existing is None or existing.hash != current_hash:
                changed.append(fp)
        return changed
