from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_create_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent
    agent = create_agent(
        agents_dir=tmp_path,
        name="Legal Expert",
        description="Answers legal questions",
        kb_path="/home/user/my-knowledge",
    )
    assert agent.name == "Legal Expert"
    assert agent.description == "Answers legal questions"
    assert agent.id
    assert agent.is_public is True
    assert agent.rate_limit_anonymous == 10
    assert (tmp_path / f"{agent.id}.json").exists()


def test_get_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent, get_agent
    agent = create_agent(agents_dir=tmp_path, name="Test", description="test", kb_path="/tmp")
    loaded = get_agent(agents_dir=tmp_path, agent_id=agent.id)
    assert loaded is not None
    assert loaded.name == "Test"
    assert loaded.id == agent.id


def test_get_agent_not_found(tmp_path) -> None:
    from openraven.agents.registry import get_agent
    assert get_agent(agents_dir=tmp_path, agent_id="nonexistent") is None


def test_list_agents(tmp_path) -> None:
    from openraven.agents.registry import create_agent, list_agents
    create_agent(agents_dir=tmp_path, name="Agent 1", description="first", kb_path="/tmp")
    create_agent(agents_dir=tmp_path, name="Agent 2", description="second", kb_path="/tmp")
    agents = list_agents(agents_dir=tmp_path)
    assert len(agents) == 2
    names = {a.name for a in agents}
    assert names == {"Agent 1", "Agent 2"}


def test_delete_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent, delete_agent, list_agents
    agent = create_agent(agents_dir=tmp_path, name="Doomed", description="bye", kb_path="/tmp")
    assert delete_agent(agents_dir=tmp_path, agent_id=agent.id) is True
    assert list_agents(agents_dir=tmp_path) == []


def test_delete_agent_not_found(tmp_path) -> None:
    from openraven.agents.registry import delete_agent
    assert delete_agent(agents_dir=tmp_path, agent_id="nope") is False


def test_update_agent(tmp_path) -> None:
    from openraven.agents.registry import create_agent, update_agent, get_agent
    agent = create_agent(agents_dir=tmp_path, name="Old Name", description="old", kb_path="/tmp")
    updated = update_agent(agents_dir=tmp_path, agent_id=agent.id, name="New Name", is_public=False)
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.is_public is False
    reloaded = get_agent(agents_dir=tmp_path, agent_id=agent.id)
    assert reloaded.name == "New Name"


def test_generate_token(tmp_path) -> None:
    from openraven.agents.registry import create_agent, generate_token, get_agent
    agent = create_agent(agents_dir=tmp_path, name="Secured", description="tokens", kb_path="/tmp")
    raw_token = generate_token(agents_dir=tmp_path, agent_id=agent.id)
    assert len(raw_token) >= 32
    reloaded = get_agent(agents_dir=tmp_path, agent_id=agent.id)
    assert len(reloaded.access_tokens) == 1


def test_verify_token(tmp_path) -> None:
    from openraven.agents.registry import create_agent, generate_token, verify_token
    agent = create_agent(agents_dir=tmp_path, name="Auth", description="check", kb_path="/tmp")
    raw_token = generate_token(agents_dir=tmp_path, agent_id=agent.id)
    assert verify_token(agents_dir=tmp_path, agent_id=agent.id, token=raw_token) is True
    assert verify_token(agents_dir=tmp_path, agent_id=agent.id, token="wrong-token") is False
