"""Finance domain extraction schema for research reports and earnings calls."""

from openraven.extraction.schemas.types import Example as ExampleData, Extraction

FINANCE_EXAMPLES = [
    ExampleData(
        text=(
            "台積電 2026 年第一季營收達 8,692 億元，年增 35%。"
            "先進製程（7nm 以下）佔營收 73%。目前本益比為 22 倍。"
        ),
        extractions=[
            Extraction(
                extraction_class="company",
                extraction_text="台積電",
            ),
            Extraction(
                extraction_class="financial_metric",
                extraction_text="營收達 8,692 億元，年增 35%",
            ),
            Extraction(
                extraction_class="financial_metric",
                extraction_text="本益比為 22 倍",
            ),
            Extraction(
                extraction_class="industry_trend",
                extraction_text="先進製程（7nm 以下）佔營收 73%",
            ),
        ],
    ),
]

FINANCE_SCHEMA: dict = {
    "name": "Finance",
    "description": "Optimized for financial research reports and earnings calls. Extracts companies, financial metrics, industry trends, analyst opinions, and risk factors.",
    "prompt_description": (
        "Extract knowledge entities from this financial/investment document. "
        "Focus on: companies and tickers, financial metrics (P/E, revenue, margins), "
        "industry trends, analyst opinions and price targets, risk factors, "
        "competitive dynamics, regulatory impacts, and valuation methodologies. "
        "Capture specific numbers, dates, and sources of claims."
    ),
    "examples": FINANCE_EXAMPLES,
}
