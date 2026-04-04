"""Base (generic) extraction schema for knowledge extraction."""

from langextract.core.data import ExampleData, Extraction

BASE_EXAMPLES = [
    ExampleData(
        text=(
            "We decided to use PostgreSQL for the primary database because of its "
            "strong ACID compliance and JSONB support. The team also considered MongoDB "
            "but rejected it due to consistency concerns."
        ),
        extractions=[
            Extraction(
                extraction_class="decision",
                extraction_text="use PostgreSQL for the primary database",
            ),
            Extraction(
                extraction_class="technology",
                extraction_text="PostgreSQL",
            ),
            Extraction(
                extraction_class="concept",
                extraction_text="ACID compliance",
            ),
        ],
    ),
]

BASE_SCHEMA: dict = {
    "name": "Base",
    "description": "Generic knowledge extraction for any document type. Extracts concepts, decisions, methods, technologies, people, organizations, and claims.",
    "prompt_description": (
        "Extract key knowledge entities from this document. "
        "Identify: concepts, decisions, methods/frameworks, technologies, "
        "people, organizations, and specific claims or findings. "
        "For each entity, capture the type and the surrounding context."
    ),
    "examples": BASE_EXAMPLES,
}
