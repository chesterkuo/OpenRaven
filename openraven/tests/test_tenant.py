import pytest
from pathlib import Path
from openraven.auth.tenant import get_tenant_config, get_tenant_pipeline, clear_pipeline_cache
from openraven.config import RavenConfig


@pytest.fixture(autouse=True)
def cleanup_cache():
    yield
    clear_pipeline_cache()


@pytest.fixture
def base_config(tmp_path):
    return RavenConfig(working_dir=tmp_path / "base")


def test_get_tenant_config_creates_tenant_dir(base_config, tmp_path):
    tenant_config = get_tenant_config(base_config, "tenant-abc-123", tmp_path / "tenants")
    assert tenant_config.working_dir == tmp_path / "tenants" / "tenant-abc-123"
    assert tenant_config.working_dir.exists()


def test_get_tenant_config_preserves_llm_settings(base_config, tmp_path):
    tenant_config = get_tenant_config(base_config, "t1", tmp_path / "tenants")
    assert tenant_config.llm_provider == base_config.llm_provider
    assert tenant_config.llm_model == base_config.llm_model


def test_get_tenant_config_isolates_paths(base_config, tmp_path):
    c1 = get_tenant_config(base_config, "t1", tmp_path / "tenants")
    c2 = get_tenant_config(base_config, "t2", tmp_path / "tenants")
    assert c1.working_dir != c2.working_dir
    assert c1.db_path != c2.db_path
    assert c1.lightrag_dir != c2.lightrag_dir
    assert c1.wiki_dir != c2.wiki_dir


def test_get_tenant_pipeline_returns_pipeline(base_config, tmp_path):
    pipeline = get_tenant_pipeline(base_config, "t1", tmp_path / "tenants")
    assert pipeline is not None
    assert pipeline.config.working_dir == tmp_path / "tenants" / "t1"


def test_get_tenant_pipeline_caches_instance(base_config, tmp_path):
    p1 = get_tenant_pipeline(base_config, "t1", tmp_path / "tenants")
    p2 = get_tenant_pipeline(base_config, "t1", tmp_path / "tenants")
    assert p1 is p2
