from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from openraven.config import RavenConfig
from openraven.health.reporter import format_health_report


def _run_async(coro):
    return asyncio.run(coro)


def _resolve_working_dir(working_dir: str) -> str:
    if working_dir != "~/my-knowledge":
        return working_dir
    global_config = Path("~/.openraven/default").expanduser()
    if global_config.exists():
        return global_config.read_text(encoding="utf-8").strip()
    return working_dir


@click.group()
@click.version_option(version="0.1.0", prog_name="raven")
def cli():
    """OpenRaven — AI-powered personal knowledge asset platform."""
    pass


@cli.command()
@click.argument("path", type=click.Path(), default="~/my-knowledge")
def init(path: str):
    """Initialize a new knowledge base."""
    config = RavenConfig(working_dir=path)

    config_file = config.working_dir / "raven.json"
    if not config_file.exists():
        config_file.write_text(json.dumps({
            "working_dir": str(config.working_dir),
            "llm_model": config.llm_model,
            "wiki_llm_model": config.wiki_llm_model,
            "embedding_model": config.embedding_model,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    global_config = Path("~/.openraven/default").expanduser()
    global_config.parent.mkdir(parents=True, exist_ok=True)
    global_config.write_text(str(config.working_dir), encoding="utf-8")

    click.echo(f"Initialized knowledge base at: {config.working_dir}")
    click.echo(f"Database: {config.db_path}")
    click.echo("")

    if not config.gemini_api_key:
        click.echo("WARNING: GEMINI_API_KEY not set. Set it in your environment or .env file.")
        click.echo("  export GEMINI_API_KEY=your-key-here")
    if not config.anthropic_api_key:
        click.echo("WARNING: ANTHROPIC_API_KEY not set (needed for wiki generation).")
        click.echo("  export ANTHROPIC_API_KEY=your-key-here")

    click.echo("")
    click.echo("Next steps:")
    click.echo("  raven add ./docs/          # Add documents")
    click.echo('  raven ask "your question"   # Query your knowledge')


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=False), required=True)
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--model", "-m", default="gemini-2.5-flash", help="LLM model for extraction")
def add(paths: tuple[str, ...], working_dir: str, model: str):
    """Add documents to the knowledge base."""
    from openraven.pipeline import RavenPipeline

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir), llm_model=model)
    pipeline = RavenPipeline(config)
    file_paths = [Path(p) for p in paths]

    click.echo(f"Processing {len(file_paths)} path(s)...")
    click.echo("")

    result = _run_async(pipeline.add_files(file_paths))

    click.echo(f"Files processed:    {result.files_processed}")
    click.echo(f"Entities extracted: {result.entities_extracted}")
    click.echo(f"Articles generated: {result.articles_generated}")

    if result.has_errors:
        click.echo("")
        click.echo("Errors:")
        for err in result.errors:
            click.echo(f"  - {err}")
        sys.exit(1)


@cli.command()
@click.argument("question")
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--mode", "-m", default="mix",
              type=click.Choice(["local", "global", "mix", "hybrid", "naive"]))
def ask(question: str, working_dir: str, mode: str):
    """Ask a question to your knowledge base."""
    from openraven.pipeline import RavenPipeline

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    pipeline = RavenPipeline(config)
    answer = _run_async(pipeline.ask(question, mode=mode))
    click.echo(answer)


@cli.command()
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
def status(working_dir: str):
    """Show knowledge base health report."""
    from openraven.pipeline import RavenPipeline

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    pipeline = RavenPipeline(config)
    report = pipeline.get_health_report()
    click.echo(format_health_report(report))


@cli.command()
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--output", "-o", default="./knowledge_graph.graphml", help="Output GraphML file")
def graph(working_dir: str, output: str):
    """Export knowledge graph as GraphML."""
    from openraven.graph.rag import RavenGraph

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    raven_graph = RavenGraph.create_lazy(working_dir=config.lightrag_dir)
    output_path = Path(output).resolve()
    raven_graph.export_graphml(output_path)
    click.echo(f"Knowledge graph exported to: {output_path}")


@cli.command(name="export")
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--format", "-f", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
@click.option("--output", "-o", default="./export/", help="Output directory")
def export_cmd(working_dir: str, fmt: str, output: str):
    """Export knowledge base (wiki articles + graph)."""
    import shutil

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir))
    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    wiki_dir = config.wiki_dir
    if wiki_dir.exists():
        if fmt == "markdown":
            for md_file in wiki_dir.glob("*.md"):
                shutil.copy2(md_file, output_dir / md_file.name)
            click.echo(f"Exported wiki articles to: {output_dir}")
        elif fmt == "json":
            articles = []
            for md_file in wiki_dir.glob("*.md"):
                articles.append({
                    "title": md_file.stem,
                    "content": md_file.read_text(encoding="utf-8"),
                })
            json_path = output_dir / "knowledge_base.json"
            json_path.write_text(
                json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            click.echo(f"Exported to: {json_path}")
    else:
        click.echo("No wiki articles found. Run 'raven add' first.")


if __name__ == "__main__":
    cli()
