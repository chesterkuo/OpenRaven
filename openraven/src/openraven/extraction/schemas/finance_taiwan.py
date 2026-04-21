"""Finance-Taiwan domain extraction schema for TWSE filings and Taiwan financial reports."""

from openraven.extraction.schemas.types import Example as ExampleData, Extraction

FINANCE_TAIWAN_EXAMPLES = [
    ExampleData(
        text=(
            "台積電（2330.TW）2026 年第一季營收達 8,692 億元，年增 35%。"
            "先進製程（7nm 以下）佔營收 73%。目前本益比為 22 倍，"
            "金管會要求上市公司於每季結束後 45 日內申報財務報告。"
        ),
        extractions=[
            Extraction(
                extraction_class="listed_company",
                extraction_text="台積電（2330.TW）",
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
                extraction_class="industry_sector",
                extraction_text="先進製程（7nm 以下）",
            ),
            Extraction(
                extraction_class="regulatory_filing",
                extraction_text="每季結束後 45 日內申報財務報告",
            ),
        ],
    ),
    ExampleData(
        text=(
            "外資分析師建議買進聯發科（2454.TW），目標價上調至 1,500 元。"
            "加權指數（TAIEX）本週收在 22,350 點，電子類股表現優於大盤。"
            "鴻海為蘋果主要供應商，受惠於 AI 伺服器訂單成長。"
        ),
        extractions=[
            Extraction(
                extraction_class="analyst_recommendation",
                extraction_text="外資分析師建議買進聯發科，目標價上調至 1,500 元",
            ),
            Extraction(
                extraction_class="listed_company",
                extraction_text="聯發科（2454.TW）",
            ),
            Extraction(
                extraction_class="market_index",
                extraction_text="加權指數（TAIEX）本週收在 22,350 點",
            ),
            Extraction(
                extraction_class="industry_sector",
                extraction_text="電子類股",
            ),
            Extraction(
                extraction_class="listed_company",
                extraction_text="鴻海",
            ),
        ],
    ),
]

FINANCE_TAIWAN_SCHEMA: dict = {
    "name": "Finance (Taiwan)",
    "description": "Optimized for TWSE filings, Taiwan financial reports, and Chinese financial terminology. Extracts listed_company, financial_metric, regulatory_filing, analyst_recommendation, market_index, and industry_sector entities.",
    "prompt_description": (
        "Extract knowledge entities from this Taiwan financial document. "
        "Focus on: listed_company names and ticker symbols (上市公司, e.g. 台積電 2330.TW), "
        "financial_metric values (財務指標 — 營收, 毛利率, 本益比, EPS, 殖利率), "
        "regulatory_filing references (監管申報 — 金管會, 證交所公告), "
        "analyst_recommendation opinions and price targets (分析師建議), "
        "market_index values (市場指數 — 加權指數, 櫃買指數), "
        "and industry_sector classifications (產業別 — 半導體, 電子, 金融). "
        "Capture the relationships: reports, competes_with, supplies_to, regulated_by, recommends. "
        "Preserve original Chinese terms alongside extracted entities. "
        "Capture specific numbers, dates, ticker symbols, and sources of claims."
    ),
    "examples": FINANCE_TAIWAN_EXAMPLES,
}
