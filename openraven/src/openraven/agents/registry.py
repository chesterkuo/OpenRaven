from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    id: str
    name: str
    description: str
    kb_path: str
    is_public: bool = True
    rate_limit_anonymous: int = 10
    rate_limit_token: int = 100
    access_tokens: list[dict] = field(default_factory=list)  # [{"hash": str, "last4": str}]
    tunnel_url: str = ""
    created_at: str = ""


def _agents_dir(agents_dir: Path) -> Path:
    agents_dir.mkdir(parents=True, exist_ok=True)
    return agents_dir


def _save_agent(agents_dir: Path, agent: AgentConfig) -> None:
    path = _agents_dir(agents_dir) / f"{agent.id}.json"
    path.write_text(json.dumps(asdict(agent), indent=2), encoding="utf-8")


def _load_agent(path: Path) -> AgentConfig | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentConfig(**data)


def create_agent(
    agents_dir: Path,
    name: str,
    description: str,
    kb_path: str,
    is_public: bool = True,
    rate_limit_anonymous: int = 10,
    rate_limit_token: int = 100,
) -> AgentConfig:
    agent = AgentConfig(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        kb_path=kb_path,
        is_public=is_public,
        rate_limit_anonymous=rate_limit_anonymous,
        rate_limit_token=rate_limit_token,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _save_agent(agents_dir, agent)
    logger.info(f"Created agent '{name}' ({agent.id})")
    return agent


def get_agent(agents_dir: Path, agent_id: str) -> AgentConfig | None:
    return _load_agent(_agents_dir(agents_dir) / f"{agent_id}.json")


def list_agents(agents_dir: Path) -> list[AgentConfig]:
    d = _agents_dir(agents_dir)
    agents = []
    for f in d.glob("*.json"):
        agent = _load_agent(f)
        if agent:
            agents.append(agent)
    return agents


_UPDATABLE_FIELDS = {"name", "description", "is_public", "rate_limit_anonymous", "rate_limit_token", "tunnel_url"}


def update_agent(agents_dir: Path, agent_id: str, **kwargs) -> AgentConfig | None:
    agent = get_agent(agents_dir, agent_id)
    if not agent:
        return None
    for key, value in kwargs.items():
        if key in _UPDATABLE_FIELDS:
            setattr(agent, key, value)
    _save_agent(agents_dir, agent)
    return agent


def delete_agent(agents_dir: Path, agent_id: str) -> bool:
    path = _agents_dir(agents_dir) / f"{agent_id}.json"
    if path.exists():
        path.unlink()
        logger.info(f"Deleted agent {agent_id}")
        return True
    return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(agents_dir: Path, agent_id: str) -> str:
    agent = get_agent(agents_dir, agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    raw_token = secrets.token_urlsafe(32)
    agent.access_tokens.append({"hash": _hash_token(raw_token), "last4": raw_token[-4:]})
    _save_agent(agents_dir, agent)
    return raw_token


def verify_token(agents_dir: Path, agent_id: str, token: str) -> bool:
    agent = get_agent(agents_dir, agent_id)
    if not agent:
        return False
    token_hash = _hash_token(token)
    return any(t["hash"] == token_hash for t in agent.access_tokens)
