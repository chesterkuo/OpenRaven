from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


class AskRequest(BaseModel):
    question: str
    mode: str = "mix"


class AskResponse(BaseModel):
    answer: str
    mode: str


class StatusResponse(BaseModel):
    total_files: int
    total_entities: int
    total_connections: int
    topic_count: int
    top_topics: list[str]
    confidence_avg: float


class IngestResponse(BaseModel):
    files_processed: int
    entities_extracted: int
    articles_generated: int
    errors: list[str]


class DiscoveryInsightResponse(BaseModel):
    insight_type: str
    title: str
    description: str
    related_entities: list[str]


class GraphNodeResponse(BaseModel):
    id: str
    labels: list[str]
    properties: dict


class GraphEdgeResponse(BaseModel):
    id: str
    type: str
    source: str
    target: str
    properties: dict


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    is_truncated: bool


def create_app(config: RavenConfig | None = None) -> FastAPI:
    if config is None:
        config = RavenConfig(working_dir="~/my-knowledge")

    app = FastAPI(
        title="OpenRaven API", version="0.1.0",
        description="OpenRaven knowledge engine API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    pipeline = RavenPipeline(config)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/status", response_model=StatusResponse)
    async def status():
        report = pipeline.get_health_report()
        return StatusResponse(
            total_files=report.total_files,
            total_entities=report.total_entities,
            total_connections=report.total_connections,
            topic_count=report.topic_count,
            top_topics=report.top_topics,
            confidence_avg=report.confidence_avg,
        )

    @app.post("/api/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        answer = await pipeline.ask(req.question, mode=req.mode)
        return AskResponse(answer=answer, mode=req.mode)

    @app.post("/api/ingest", response_model=IngestResponse)
    async def ingest(files: list[UploadFile] = File(...)):
        saved_paths: list[Path] = []
        config.ingestion_dir.mkdir(parents=True, exist_ok=True)
        for upload in files:
            dest = config.ingestion_dir / upload.filename
            content = await upload.read()
            dest.write_bytes(content)
            saved_paths.append(dest)

        result = await pipeline.add_files(saved_paths)
        return IngestResponse(
            files_processed=result.files_processed,
            entities_extracted=result.entities_extracted,
            articles_generated=result.articles_generated,
            errors=result.errors,
        )

    @app.get("/api/graph", response_model=GraphResponse)
    async def graph(max_nodes: int = Query(default=500, ge=1, le=5000)):
        # Run blocking NetworkX read in thread pool to avoid blocking event loop
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: pipeline.graph.get_graph_data(max_nodes=max_nodes)
        )
        return GraphResponse(**data)

    @app.get("/api/wiki")
    async def wiki_list():
        wiki_dir = config.wiki_dir
        if not wiki_dir.exists():
            return []
        articles = []
        for f in sorted(wiki_dir.glob("*.md")):
            first_line = f.read_text(encoding="utf-8").split("\n", 1)[0]
            title = first_line.lstrip("# ").strip() if first_line.startswith("#") else f.stem
            articles.append({"slug": f.stem, "title": title})
        return articles

    @app.get("/api/wiki/{slug}")
    async def wiki_article(slug: str):
        from fastapi.responses import JSONResponse
        wiki_file = config.wiki_dir / f"{slug}.md"
        if not wiki_file.exists():
            return JSONResponse({"error": "Article not found"}, status_code=404)
        content = wiki_file.read_text(encoding="utf-8")
        first_line = content.split("\n", 1)[0]
        title = first_line.lstrip("# ").strip() if first_line.startswith("#") else slug
        return {"slug": slug, "title": title, "content": content}

    @app.get("/api/discovery", response_model=list[DiscoveryInsightResponse])
    async def discovery():
        from openraven.discovery.analyzer import analyze_themes
        graph_stats = pipeline.graph.get_stats()
        insights = analyze_themes(graph_stats)
        return [
            DiscoveryInsightResponse(
                insight_type=i.insight_type, title=i.title,
                description=i.description, related_entities=i.related_entities,
            )
            for i in insights
        ]

    return app


def run_server(config: RavenConfig | None = None) -> None:
    import uvicorn
    if config is None:
        config = RavenConfig(working_dir="~/my-knowledge")
    app = create_app(config)
    uvicorn.run(app, host=config.api_host, port=config.api_port)
