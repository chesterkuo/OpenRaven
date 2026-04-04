from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openraven.api.server import create_app
from openraven.config import RavenConfig


@pytest.fixture
def client(config: RavenConfig) -> TestClient:
    app = create_app(config)
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_files" in data
    assert "total_entities" in data


def test_ask_endpoint_requires_question(client: TestClient) -> None:
    response = client.post("/api/ask", json={})
    assert response.status_code == 422


def test_discovery_endpoint(client: TestClient) -> None:
    response = client.get("/api/discovery")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_status_returns_zeros_on_empty_kb(client: TestClient) -> None:
    response = client.get("/api/status")
    data = response.json()
    assert data["total_files"] == 0
    assert data["total_entities"] == 0
    assert data["topic_count"] == 0


def test_graph_endpoint(client: TestClient) -> None:
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "is_truncated" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_graph_endpoint_with_max_nodes(client: TestClient) -> None:
    response = client.get("/api/graph?max_nodes=10")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data


def test_graph_endpoint_rejects_invalid_max_nodes(client: TestClient) -> None:
    response = client.get("/api/graph?max_nodes=0")
    assert response.status_code == 422

    response = client.get("/api/graph?max_nodes=-1")
    assert response.status_code == 422


def test_wiki_list_endpoint(client: TestClient) -> None:
    response = client.get("/api/wiki")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_wiki_article_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/api/wiki/nonexistent-article")
    assert response.status_code == 404


def test_wiki_export_endpoint(client: TestClient, config) -> None:
    config.wiki_dir.mkdir(parents=True, exist_ok=True)
    (config.wiki_dir / "test_article.md").write_text("# Test\n\nContent.")
    response = client.get("/api/wiki/export")
    assert response.status_code == 200
    assert "zip" in response.headers.get("content-disposition", "").lower()
    assert len(response.content) > 0


def test_graph_export_endpoint(client: TestClient) -> None:
    response = client.get("/api/graph/export")
    assert response.status_code == 200
    assert "graphml" in response.headers.get("content-disposition", "").lower()


def test_ingest_status_unknown_job(client: TestClient) -> None:
    response = client.get("/api/ingest/status/nonexistent")
    assert response.status_code == 404


def test_provider_endpoint(client: TestClient) -> None:
    response = client.get("/api/config/provider")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "llm_model" in data
    assert "embedding_model" in data


def test_wiki_article_endpoint_reads_file(client: TestClient, config) -> None:
    config.wiki_dir.mkdir(parents=True, exist_ok=True)
    (config.wiki_dir / "apache_kafka.md").write_text(
        "# Apache Kafka\n\n**Confidence:** 85%\n\nA streaming platform.\n"
    )
    response = client.get("/api/wiki/apache_kafka")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "apache_kafka"
    assert data["title"] == "Apache Kafka"
    assert "streaming platform" in data["content"]


def test_health_insights_endpoint(client: TestClient) -> None:
    response = client.get("/api/health/insights")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_health_run_endpoint(client: TestClient) -> None:
    response = client.post("/api/health/run")
    assert response.status_code == 200
    data = response.json()
    assert "insights_count" in data


def test_connectors_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/connectors/status")
    assert response.status_code == 200
    data = response.json()
    assert "gdrive" in data
    assert "gmail" in data
    assert data["gdrive"]["connected"] is False
    assert data["gmail"]["connected"] is False


def test_connectors_auth_url_requires_credentials(client: TestClient) -> None:
    response = client.get("/api/connectors/google/auth-url")
    assert response.status_code == 400


def test_connectors_sync_requires_auth(client: TestClient) -> None:
    response = client.post("/api/connectors/gdrive/sync")
    assert response.status_code == 401


def test_ask_response_includes_sources_field(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "What is Kafka?"})
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)


def test_ask_response_sources_are_structured(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "test"})
    data = response.json()
    assert "sources" in data
    assert "answer" in data
    assert "mode" in data


def test_connectors_status_includes_meet_and_otter(client: TestClient) -> None:
    response = client.get("/api/connectors/status")
    assert response.status_code == 200
    data = response.json()
    assert "meet" in data
    assert "otter" in data
    assert data["meet"]["connected"] is False
    assert data["otter"]["connected"] is False


def test_meet_sync_requires_auth(client: TestClient) -> None:
    response = client.post("/api/connectors/meet/sync")
    assert response.status_code == 401


def test_otter_save_key_endpoint(client: TestClient) -> None:
    response = client.post("/api/connectors/otter/save-key", json={"api_key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True


def test_schemas_endpoint(client: TestClient) -> None:
    response = client.get("/api/schemas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    ids = [s["id"] for s in data]
    assert "base" in ids
    assert "legal-taiwan" in ids
    assert "finance-taiwan" in ids
    for s in data:
        assert "id" in s
        assert "name" in s
        assert "description" in s


def test_otter_sync_requires_key(client: TestClient) -> None:
    response = client.post("/api/connectors/otter/sync")
    assert response.status_code == 401
