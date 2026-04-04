"""Engineering domain extraction schema for ADRs, tech specs, and architecture docs."""

from langextract.core.data import ExampleData, Extraction

ENGINEERING_EXAMPLES = [
    ExampleData(
        text=(
            "We chose event-driven architecture using Apache Kafka because it decouples "
            "order intake from fulfillment. Trade-off: added operational complexity for "
            "Kafka cluster management. The system handles 50,000 orders/day."
        ),
        extractions=[
            Extraction(
                extraction_class="architecture_decision",
                extraction_text="chose event-driven architecture using Apache Kafka",
            ),
            Extraction(
                extraction_class="technology",
                extraction_text="Apache Kafka",
            ),
            Extraction(
                extraction_class="trade_off",
                extraction_text="added operational complexity for Kafka cluster management",
            ),
            Extraction(
                extraction_class="performance_metric",
                extraction_text="50,000 orders/day",
            ),
        ],
    ),
]

ENGINEERING_SCHEMA: dict = {
    "prompt_description": (
        "Extract knowledge entities from this technical/engineering document. "
        "Focus on: architecture decisions (and their rationale), technology choices, "
        "trade-offs evaluated, performance metrics, system components, APIs, "
        "design patterns used, risks identified, and lessons learned. "
        "Capture WHY decisions were made, not just WHAT was decided."
    ),
    "examples": ENGINEERING_EXAMPLES,
}
