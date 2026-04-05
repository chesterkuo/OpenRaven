import pytest
from openraven.config import RavenConfig


def test_config_graph_backend_default():
    config = RavenConfig(working_dir="/tmp/test")
    assert config.graph_backend == "networkx"


def test_config_graph_backend_neo4j():
    import os
    os.environ["GRAPH_BACKEND"] = "neo4j"
    config = RavenConfig(working_dir="/tmp/test")
    assert config.graph_backend == "neo4j"
    del os.environ["GRAPH_BACKEND"]


def test_neo4j_connection():
    """Test that Neo4j is reachable."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "openraven123"))
    with driver.session() as session:
        result = session.run("RETURN 1 AS n")
        assert result.single()["n"] == 1
    driver.close()
