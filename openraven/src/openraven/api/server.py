from __future__ import annotations

import asyncio
import hashlib
import logging
import tempfile
import uuid
from dataclasses import dataclass, field as dc_field
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import BackgroundTasks, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


class AskRequest(BaseModel):
    question: str
    mode: str = "mix"


class SourceRef(BaseModel):
    document: str
    excerpt: str
    char_start: int = 0
    char_end: int = 0


class AskResponse(BaseModel):
    answer: str
    mode: str
    sources: list[SourceRef] = []


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


@dataclass
class IngestJob:
    job_id: str
    stage: str = "uploading"
    files_total: int = 0
    files_done: int = 0
    entities_extracted: int = 0
    articles_total: int = 0
    articles_done: int = 0
    errors: list[str] = dc_field(default_factory=list)
    result: dict | None = None


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
        allow_origin_regex=r"^chrome-extension://.*$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    pipeline = RavenPipeline(config)
    ingest_jobs: dict[str, IngestJob] = {}

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/schemas")
    async def schemas():
        from openraven.extraction.schemas import list_schemas
        return list_schemas()

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
        result = await pipeline.ask_with_sources(req.question, mode=req.mode)
        return AskResponse(
            answer=result.answer,
            mode=req.mode,
            sources=[SourceRef(**s) for s in result.sources],
        )

    @app.get("/api/ingest/status/{job_id}")
    async def ingest_status(job_id: str):
        from fastapi.responses import JSONResponse
        job = ingest_jobs.get(job_id)
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        return {
            "job_id": job.job_id,
            "stage": job.stage,
            "files_total": job.files_total,
            "files_done": job.files_done,
            "entities_extracted": job.entities_extracted,
            "articles_total": job.articles_total,
            "articles_done": job.articles_done,
            "errors": job.errors,
            "result": job.result,
        }

    @app.post("/api/ingest", response_model=IngestResponse)
    async def ingest(files: list[UploadFile] = File(...), schema: str | None = Form(default=None)):
        schema_name: str | None = schema if schema and schema != "auto" else None

        saved_paths: list[Path] = []
        config.ingestion_dir.mkdir(parents=True, exist_ok=True)
        for upload in files:
            dest = config.ingestion_dir / upload.filename
            content = await upload.read()
            dest.write_bytes(content)
            saved_paths.append(dest)

        job_id = str(uuid.uuid4())[:8]
        job = IngestJob(job_id=job_id, files_total=len(saved_paths), stage="processing")
        ingest_jobs[job_id] = job

        result = await pipeline.add_files(saved_paths, schema_name=schema_name)

        job.stage = "done"
        job.files_done = result.files_processed
        job.entities_extracted = result.entities_extracted
        job.articles_done = result.articles_generated
        job.errors = result.errors
        job.result = {
            "files_processed": result.files_processed,
            "entities_extracted": result.entities_extracted,
            "articles_generated": result.articles_generated,
            "errors": result.errors,
        }

        return IngestResponse(
            files_processed=result.files_processed,
            entities_extracted=result.entities_extracted,
            articles_generated=result.articles_generated,
            errors=result.errors,
        )

    @app.get("/api/graph/export")
    async def graph_export(background_tasks: BackgroundTasks):
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".graphml", delete=False)
        tmp.close()
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: pipeline.graph.export_graphml(Path(tmp.name))
        )
        background_tasks.add_task(os.unlink, tmp.name)
        return FileResponse(
            path=tmp.name,
            media_type="application/xml",
            filename="openraven-knowledge-graph.graphml",
        )

    @app.get("/api/graph", response_model=GraphResponse)
    async def graph(max_nodes: int = Query(default=500, ge=1, le=5000)):
        # Run blocking NetworkX read in thread pool to avoid blocking event loop
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: pipeline.graph.get_graph_data(max_nodes=max_nodes)
        )
        return GraphResponse(**data)

    @app.get("/api/wiki/export")
    async def wiki_export(background_tasks: BackgroundTasks):
        """Download all wiki articles as a zip of markdown files."""
        import os
        import zipfile
        wiki_dir = config.wiki_dir
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            if wiki_dir.exists():
                for f in sorted(wiki_dir.glob("*.md")):
                    zf.write(f, f.name)
        background_tasks.add_task(os.unlink, tmp.name)
        return FileResponse(
            path=tmp.name,
            media_type="application/zip",
            filename="openraven-wiki.zip",
        )

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

    @app.get("/api/config/provider")
    async def provider_info():
        return {
            "provider": config.llm_provider,
            "llm_model": config.llm_model,
            "wiki_model": config.wiki_llm_model,
            "embedding_model": config.embedding_model,
            "ollama_url": config.ollama_base_url if config.llm_provider == "ollama" else None,
        }

    @app.get("/api/health/insights")
    async def health_insights():
        from openraven.health.maintainer import HealthMaintainer
        maintainer = HealthMaintainer(store=pipeline.store, graph=pipeline.graph, config=config)
        insights = maintainer.run_all()
        return [
            {
                "insight_type": i.insight_type,
                "title": i.title,
                "description": i.description,
                "related_entities": i.related_entities,
                "severity": i.severity,
            }
            for i in insights
        ]

    @app.post("/api/health/run")
    async def health_run():
        from openraven.health.maintainer import HealthMaintainer
        maintainer = HealthMaintainer(store=pipeline.store, graph=pipeline.graph, config=config)
        insights = maintainer.run_all()
        return {"insights_count": len(insights), "insights": [
            {"insight_type": i.insight_type, "title": i.title, "severity": i.severity}
            for i in insights
        ]}

    # --- Google Connectors ---

    @app.get("/api/connectors/status")
    async def connectors_status():
        from openraven.connectors.google_auth import load_token
        token = load_token(config.google_token_path)
        google_connected = token is not None
        return {
            "gdrive": {"connected": google_connected},
            "gmail": {"connected": google_connected},
            "meet": {"connected": google_connected},
            "otter": {"connected": bool(config.otter_api_key)},
            "google_configured": bool(config.google_client_id and config.google_client_secret),
        }

    @app.get("/api/connectors/google/auth-url")
    async def google_auth_url():
        from fastapi.responses import JSONResponse
        if not config.google_client_id:
            return JSONResponse({"error": "GOOGLE_CLIENT_ID not configured"}, status_code=400)
        from openraven.connectors.google_auth import ALL_SCOPES, build_auth_url
        url = build_auth_url(
            client_id=config.google_client_id,
            scopes=ALL_SCOPES,
        )
        return {"auth_url": url}

    @app.get("/api/connectors/google/callback")
    async def google_callback(code: str):
        from fastapi.responses import HTMLResponse
        from openraven.connectors.google_auth import exchange_code, save_token
        try:
            token_data = await exchange_code(
                code=code,
                client_id=config.google_client_id,
                client_secret=config.google_client_secret,
            )
        except Exception as e:
            logger.error(f"OAuth code exchange failed: {e}")
            return HTMLResponse(
                "<html><body><h2>Connection failed.</h2>"
                "<p>Please try again.</p></body></html>",
                status_code=400,
            )
        save_token(token_data, config.google_token_path)
        return HTMLResponse(
            "<html><body><h2>Connected successfully.</h2>"
            "<p>You can close this window.</p>"
            "<script>window.close();</script></body></html>"
        )

    @app.post("/api/connectors/gdrive/sync")
    async def gdrive_sync():
        from fastapi.responses import JSONResponse
        from openraven.connectors.gdrive import sync_drive
        from openraven.connectors.google_auth import get_credentials
        creds = get_credentials(
            config.google_token_path, config.google_client_id, config.google_client_secret
        )
        if not creds:
            return JSONResponse(
                {"error": "Not authenticated. Connect Google account first."}, status_code=401
            )
        files = await sync_drive(credentials=creds, output_dir=config.ingestion_dir / "gdrive")
        if files:
            result = await pipeline.add_files(files)
            return {
                "files_synced": len(files),
                "entities_extracted": result.entities_extracted,
                "articles_generated": result.articles_generated,
                "errors": result.errors,
            }
        return {"files_synced": 0, "entities_extracted": 0, "articles_generated": 0, "errors": []}

    @app.post("/api/connectors/gmail/sync")
    async def gmail_sync():
        from fastapi.responses import JSONResponse
        from openraven.connectors.gmail import sync_gmail
        from openraven.connectors.google_auth import get_credentials
        creds = get_credentials(
            config.google_token_path, config.google_client_id, config.google_client_secret
        )
        if not creds:
            return JSONResponse(
                {"error": "Not authenticated. Connect Google account first."}, status_code=401
            )
        files = await sync_gmail(credentials=creds, output_dir=config.ingestion_dir / "gmail")
        if files:
            result = await pipeline.add_files(files)
            return {
                "files_synced": len(files),
                "entities_extracted": result.entities_extracted,
                "articles_generated": result.articles_generated,
                "errors": result.errors,
            }
        return {"files_synced": 0, "entities_extracted": 0, "articles_generated": 0, "errors": []}

    @app.post("/api/connectors/meet/sync")
    async def meet_sync():
        from fastapi.responses import JSONResponse
        from openraven.connectors.gdrive import sync_meet_transcripts
        from openraven.connectors.google_auth import get_credentials
        creds = get_credentials(
            config.google_token_path, config.google_client_id, config.google_client_secret
        )
        if not creds:
            return JSONResponse(
                {"error": "Not authenticated. Connect Google account first."}, status_code=401
            )
        files = await sync_meet_transcripts(
            credentials=creds, output_dir=config.ingestion_dir / "meet"
        )
        if files:
            result = await pipeline.add_files(files)
            return {
                "files_synced": len(files),
                "entities_extracted": result.entities_extracted,
                "articles_generated": result.articles_generated,
                "errors": result.errors,
            }
        return {"files_synced": 0, "entities_extracted": 0, "articles_generated": 0, "errors": []}

    @app.post("/api/connectors/otter/save-key")
    async def otter_save_key(body: dict):
        from openraven.connectors.otter import save_api_key
        api_key = body.get("api_key", "")
        if not api_key:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "api_key is required"}, status_code=400)
        save_api_key(api_key, config.otter_key_path)
        return {"saved": True}

    @app.post("/api/connectors/otter/sync")
    async def otter_sync():
        from fastapi.responses import JSONResponse
        from openraven.connectors.otter import sync_otter
        api_key = config.otter_api_key
        if not api_key:
            return JSONResponse(
                {"error": "Otter.ai API key not configured. Save your key first."}, status_code=401
            )
        files = await sync_otter(
            api_key=api_key, output_dir=config.ingestion_dir / "otter"
        )
        if files:
            result = await pipeline.add_files(files)
            return {
                "files_synced": len(files),
                "entities_extracted": result.entities_extracted,
                "articles_generated": result.articles_generated,
                "errors": result.errors,
            }
        return {"files_synced": 0, "entities_extracted": 0, "articles_generated": 0, "errors": []}

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

    # --- Agent Deployment ---

    agents_dir = config.working_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    from openraven.agents.ratelimit import RateLimiter
    agent_rate_limiter = RateLimiter()

    @app.post("/api/agents")
    async def create_agent_endpoint(body: dict):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import create_agent
        if not body.get("name", "").strip():
            return JSONResponse({"error": "name is required"}, status_code=400)
        agent = create_agent(
            agents_dir=agents_dir,
            name=body.get("name", ""),
            description=body.get("description", ""),
            kb_path=str(config.working_dir),
            is_public=body.get("is_public", True),
            rate_limit_anonymous=body.get("rate_limit_anonymous", 10),
            rate_limit_token=body.get("rate_limit_token", 100),
        )
        return {
            "id": agent.id, "name": agent.name, "description": agent.description,
            "is_public": agent.is_public, "tunnel_url": agent.tunnel_url,
            "rate_limit_anonymous": agent.rate_limit_anonymous,
            "rate_limit_token": agent.rate_limit_token,
            "created_at": agent.created_at,
        }

    @app.get("/api/agents")
    async def list_agents_endpoint():
        from openraven.agents.registry import list_agents
        agents = list_agents(agents_dir)
        return [
            {"id": a.id, "name": a.name, "description": a.description,
             "is_public": a.is_public, "tunnel_url": a.tunnel_url,
             "created_at": a.created_at}
            for a in agents
        ]

    @app.get("/api/agents/{agent_id}")
    async def get_agent_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return {
            "id": agent.id, "name": agent.name, "description": agent.description,
            "is_public": agent.is_public, "tunnel_url": agent.tunnel_url,
            "rate_limit_anonymous": agent.rate_limit_anonymous,
            "rate_limit_token": agent.rate_limit_token,
            "token_count": len(agent.access_tokens),
            "tokens": [{"last4": t["last4"]} for t in agent.access_tokens],
            "created_at": agent.created_at,
        }

    @app.delete("/api/agents/{agent_id}")
    async def delete_agent_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import delete_agent
        if delete_agent(agents_dir, agent_id):
            return {"deleted": True}
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    @app.post("/api/agents/{agent_id}/tokens")
    async def generate_token_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import generate_token
        try:
            token = generate_token(agents_dir, agent_id)
            return {"token": token}
        except ValueError:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

    @app.post("/api/agents/{agent_id}/deploy")
    async def deploy_agent_endpoint(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent, update_agent
        from openraven.agents.tunnel import start_tunnel
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        try:
            url = start_tunnel(port=config.api_port, working_dir=config.working_dir)
            update_agent(agents_dir, agent_id, tunnel_url=url)
            return {"tunnel_url": url}
        except RuntimeError as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/agents/{agent_id}/undeploy")
    async def undeploy_agent_endpoint(agent_id: str):
        from openraven.agents.registry import update_agent
        from openraven.agents.tunnel import stop_tunnel
        stop_tunnel(config.working_dir)
        update_agent(agents_dir, agent_id, tunnel_url="")
        return {"undeployed": True}

    # --- Public Agent Endpoints (exposed via tunnel) ---

    @app.get("/agents/{agent_id}")
    async def agent_chat_page(agent_id: str):
        from fastapi.responses import HTMLResponse, JSONResponse
        from openraven.agents.chat_page import render_chat_page
        from openraven.agents.registry import get_agent
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        page_html = render_chat_page(agent.id, agent.name, agent.description)
        return HTMLResponse(page_html)

    @app.get("/agents/{agent_id}/info")
    async def agent_info(agent_id: str):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent
        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return {"name": agent.name, "description": agent.description}

    @app.post("/agents/{agent_id}/ask")
    async def agent_ask(agent_id: str, body: dict, request: Request):
        from fastapi.responses import JSONResponse
        from openraven.agents.registry import get_agent, verify_token

        agent = get_agent(agents_dir, agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        auth_header = request.headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        if not agent.is_public and not token:
            return JSONResponse({"error": "This agent requires an access token."}, status_code=403)
        if token and not verify_token(agents_dir, agent_id, token):
            return JSONResponse({"error": "Invalid access token."}, status_code=403)

        if token:
            rate_key = f"token:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
            limit = agent.rate_limit_token
        else:
            client_ip = request.client.host if request.client else "unknown"
            rate_key = f"ip:{client_ip}:{agent_id}"
            limit = agent.rate_limit_anonymous

        allowed, remaining = agent_rate_limiter.check(rate_key, limit=limit)
        if not allowed:
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={"Retry-After": "3600", "X-RateLimit-Remaining": "0"},
            )

        question = body.get("question", "")
        mode = body.get("mode", "mix")
        result = await pipeline.ask_with_sources(question, mode=mode)
        return {
            "answer": result.answer,
            "sources": [{"document": s["document"], "excerpt": s["excerpt"]} for s in result.sources],
        }

    # --- Course Generation ---

    @dataclass
    class CourseJob:
        job_id: str
        stage: str = "planning"
        chapters_total: int = 0
        chapters_done: int = 0
        course_id: str = ""
        error: str = ""

    course_jobs: dict[str, CourseJob] = {}

    @app.post("/api/courses/generate")
    async def courses_generate(body: dict):
        from fastapi.responses import JSONResponse
        title = body.get("title", "").strip()
        audience = body.get("audience", "").strip()
        objectives = body.get("objectives", [])
        if not title:
            return JSONResponse({"error": "title is required"}, status_code=400)

        job_id = str(uuid.uuid4())[:8]
        job = CourseJob(job_id=job_id)
        course_jobs[job_id] = job

        async def run_generation() -> None:
            try:
                from openraven.courses.planner import plan_curriculum
                from openraven.courses.renderer import generate_course

                base_url = (
                    f"{config.ollama_base_url}/v1"
                    if config.llm_provider == "ollama"
                    else "https://generativelanguage.googleapis.com/v1beta/openai/"
                )

                # Get entity names from graph
                graph_stats = pipeline.graph.get_stats()
                entity_names = graph_stats.get("topics", [])[:100]

                job.stage = "planning"
                outline = await plan_curriculum(
                    title=title, audience=audience or "General",
                    objectives=objectives if objectives else [f"Learn about {title}"],
                    entity_names=entity_names,
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    base_url=base_url,
                )

                job.chapters_total = len(outline.chapters)
                job.stage = "generating"

                def on_progress(done: int, total: int) -> None:
                    job.chapters_done = done

                config.courses_dir.mkdir(parents=True, exist_ok=True)
                course_dir = await generate_course(
                    outline=outline,
                    ask_fn=pipeline.ask_with_sources,
                    output_dir=config.courses_dir,
                    api_key=config.llm_api_key,
                    model=config.llm_model,
                    base_url=base_url,
                    on_progress=on_progress,
                )

                job.course_id = course_dir.name
                job.stage = "done"
            except Exception as e:
                logger.error(f"Course generation failed: {e}", exc_info=True)
                job.stage = "error"
                job.error = str(e)

        asyncio.create_task(run_generation())
        return {"job_id": job_id}

    @app.get("/api/courses/generate/{job_id}")
    async def courses_generate_status(job_id: str):
        from fastapi.responses import JSONResponse
        job = course_jobs.get(job_id)
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        return {
            "job_id": job.job_id,
            "stage": job.stage,
            "chapters_total": job.chapters_total,
            "chapters_done": job.chapters_done,
            "course_id": job.course_id,
            "error": job.error,
        }

    @app.get("/api/courses")
    async def courses_list():
        courses_dir = config.courses_dir
        if not courses_dir.exists():
            return []
        courses = []
        for d in sorted(courses_dir.iterdir()):
            meta_file = d / "metadata.json"
            if d.is_dir() and meta_file.exists():
                import json as _json
                meta = _json.loads(meta_file.read_text(encoding="utf-8"))
                # Get created_at from directory mtime
                import datetime
                created_at = datetime.datetime.fromtimestamp(
                    d.stat().st_mtime, tz=datetime.timezone.utc
                ).isoformat()
                courses.append({
                    "id": meta["id"],
                    "title": meta["title"],
                    "audience": meta.get("audience", ""),
                    "chapter_count": len(meta.get("chapters", [])),
                    "created_at": created_at,
                })
        return courses

    @app.get("/api/courses/{course_id}")
    async def courses_get(course_id: str):
        from fastapi.responses import JSONResponse
        course_dir = config.courses_dir / course_id
        meta_file = course_dir / "metadata.json"
        if not course_dir.exists() or not meta_file.exists():
            return JSONResponse({"error": "Course not found"}, status_code=404)
        import json as _json
        meta = _json.loads(meta_file.read_text(encoding="utf-8"))
        import datetime
        created_at = datetime.datetime.fromtimestamp(
            course_dir.stat().st_mtime, tz=datetime.timezone.utc
        ).isoformat()
        return {
            "id": meta["id"],
            "title": meta["title"],
            "audience": meta.get("audience", ""),
            "objectives": meta.get("objectives", []),
            "chapters": meta.get("chapters", []),
            "created_at": created_at,
        }

    @app.get("/api/courses/{course_id}/download")
    async def courses_download(course_id: str, background_tasks: BackgroundTasks):
        import os
        import zipfile
        from fastapi.responses import JSONResponse
        course_dir = config.courses_dir / course_id
        if not course_dir.exists():
            return JSONResponse({"error": "Course not found"}, status_code=404)
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(course_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(course_dir))
        background_tasks.add_task(os.unlink, tmp.name)
        import json as _json
        meta_file = course_dir / "metadata.json"
        safe_name = "course"
        if meta_file.exists():
            meta = _json.loads(meta_file.read_text(encoding="utf-8"))
            safe_name = meta.get("title", "course").replace(" ", "-").lower()[:40]
        return FileResponse(
            path=tmp.name, media_type="application/zip",
            filename=f"{safe_name}.zip",
        )

    @app.delete("/api/courses/{course_id}")
    async def courses_delete(course_id: str):
        import shutil
        from fastapi.responses import JSONResponse
        course_dir = config.courses_dir / course_id
        if not course_dir.exists():
            return JSONResponse({"error": "Course not found"}, status_code=404)
        shutil.rmtree(course_dir)
        return {"deleted": True}

    return app


def run_server(config: RavenConfig | None = None) -> None:
    import uvicorn
    if config is None:
        config = RavenConfig(working_dir="~/my-knowledge")
    app = create_app(config)
    uvicorn.run(app, host=config.api_host, port=config.api_port)
