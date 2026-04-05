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
) -> RavenConfig:
    """Create a tenant-scoped RavenConfig with isolated working_dir."""
    if tenants_root is None:
        tenants_root = Path("/data/tenants")

    tenant_dir = tenants_root / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)

    return replace(base_config, working_dir=tenant_dir)


def get_tenant_pipeline(
    base_config: RavenConfig,
    tenant_id: str,
    tenants_root: Path | None = None,
) -> RavenPipeline:
    """Get or create a tenant-scoped RavenPipeline. Cached by tenant_id."""
    if tenant_id in _pipeline_cache:
        return _pipeline_cache[tenant_id]

    tenant_config = get_tenant_config(base_config, tenant_id, tenants_root)
    pipeline = RavenPipeline(tenant_config)
    _pipeline_cache[tenant_id] = pipeline
    return pipeline


def clear_pipeline_cache() -> None:
    """Clear the pipeline cache. Used in tests."""
    _pipeline_cache.clear()
