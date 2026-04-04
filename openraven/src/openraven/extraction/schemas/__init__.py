"""Schema registry for all extraction schemas."""

from openraven.extraction.schemas.base import BASE_SCHEMA
from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
from openraven.extraction.schemas.finance import FINANCE_SCHEMA
from openraven.extraction.schemas.finance_taiwan import FINANCE_TAIWAN_SCHEMA
from openraven.extraction.schemas.legal_taiwan import LEGAL_TAIWAN_SCHEMA

SCHEMA_REGISTRY: dict[str, dict] = {
    "base": BASE_SCHEMA,
    "engineering": ENGINEERING_SCHEMA,
    "finance": FINANCE_SCHEMA,
    "legal-taiwan": LEGAL_TAIWAN_SCHEMA,
    "finance-taiwan": FINANCE_TAIWAN_SCHEMA,
}


def get_schema(name: str) -> dict:
    """Return a schema by ID. Falls back to BASE_SCHEMA if not found."""
    return SCHEMA_REGISTRY.get(name, BASE_SCHEMA)


def list_schemas() -> list[dict]:
    """Return metadata for all registered schemas."""
    return [
        {
            "id": key,
            "name": schema.get("name", key),
            "description": schema.get("description", ""),
        }
        for key, schema in SCHEMA_REGISTRY.items()
    ]
