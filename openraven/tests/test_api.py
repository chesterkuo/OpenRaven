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
