"""Tenant-scoped configuration and pipeline management."""

from dataclasses import replace
from pathlib import Path

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


_pipeline_cache: dict[str, RavenPipeline] = {}


def get_tenant_config(
    base_config: RavenConfig,
    tenant_id: str,
    tenants_root: Path | None = None,
    demo_theme: str | None = None,
) -> RavenConfig:
    """Create a tenant-scoped RavenConfig with isolated working_dir."""
    if tenants_root is None:
        tenants_root = Path("/data/tenants")

    tenant_dir = tenants_root / tenant_id
    if demo_theme:
        tenant_dir = tenant_dir / demo_theme
    tenant_dir.mkdir(parents=True, exist_ok=True)

    return replace(base_config, working_dir=tenant_dir)


def get_tenant_pipeline(
    base_config: RavenConfig,
    tenant_id: str,
    tenants_root: Path | None = None,
    demo_theme: str | None = None,
) -> RavenPipeline:
    """Get or create a tenant-scoped RavenPipeline. Cached by tenant_id+theme."""
    cache_key = f"{tenant_id}/{demo_theme}" if demo_theme else tenant_id
    if cache_key in _pipeline_cache:
        return _pipeline_cache[cache_key]

    tenant_config = get_tenant_config(base_config, tenant_id, tenants_root, demo_theme=demo_theme)
    pipeline = RavenPipeline(tenant_config)
    _pipeline_cache[cache_key] = pipeline
    return pipeline


def clear_pipeline_cache() -> None:
    """Clear the pipeline cache. Used in tests."""
    _pipeline_cache.clear()
