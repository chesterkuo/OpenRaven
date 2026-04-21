"""Legal-Taiwan domain extraction schema for court rulings, statutes, and legal documents."""

from openraven.extraction.schemas.types import Example as ExampleData, Extraction

LEGAL_TAIWAN_EXAMPLES = [
    ExampleData(
        text=(
            "最高法院 112 年度台上字第 1234 號民事判決，依民法第 184 條第 1 項前段，"
            "認定被告應負侵權行為損害賠償責任。原告主張其因被告之過失行為受有損害，"
            "法院審酌相關事證後，判決被告應賠償原告新台幣 500 萬元。"
        ),
        extractions=[
            Extraction(
                extraction_class="court_ruling",
                extraction_text="最高法院 112 年度台上字第 1234 號民事判決",
            ),
            Extraction(
                extraction_class="statute",
                extraction_text="民法第 184 條第 1 項前段",
            ),
            Extraction(
                extraction_class="legal_principle",
                extraction_text="侵權行為損害賠償責任",
            ),
            Extraction(
                extraction_class="party",
                extraction_text="原告",
            ),
            Extraction(
                extraction_class="party",
                extraction_text="被告",
            ),
            Extraction(
                extraction_class="court",
                extraction_text="最高法院",
            ),
        ],
    ),
    ExampleData(
        text=(
            "臺灣高等法院法官王大明審理本案，引用司法院大法官釋字第 748 號解釋，"
            "認為憲法保障人民之婚姻自由。本判決推翻地方法院之原判決。"
        ),
        extractions=[
            Extraction(
                extraction_class="judge",
                extraction_text="法官王大明",
            ),
            Extraction(
                extraction_class="court",
                extraction_text="臺灣高等法院",
            ),
            Extraction(
                extraction_class="legal_document",
                extraction_text="司法院大法官釋字第 748 號解釋",
            ),
            Extraction(
                extraction_class="legal_principle",
                extraction_text="憲法保障人民之婚姻自由",
            ),
        ],
    ),
]

LEGAL_TAIWAN_SCHEMA: dict = {
    "name": "Legal (Taiwan)",
    "description": "Optimized for Taiwan court rulings, statutes, and legal documents. Extracts statutes, court_ruling, legal_principle, party, judge, court, and legal_document entities.",
    "prompt_description": (
        "Extract knowledge entities from this Taiwan legal document. "
        "Focus on: statute references (法條, e.g. 民法第 X 條), "
        "court_ruling identifiers (判決, e.g. 案號), "
        "legal_principle concepts (法律原則, e.g. 侵權行為, 契約自由), "
        "party names (當事人 — 原告/被告), "
        "judge names (法官), "
        "court names (法院, e.g. 最高法院, 臺灣高等法院), "
        "and legal_document references (法律文件, e.g. 大法官解釋, 行政命令). "
        "Capture the relationships: cites (引用), interprets (解釋), "
        "overrules (推翻), applies_to (適用於), filed_by (提起). "
        "Preserve original Chinese terms alongside extracted entities."
    ),
    "examples": LEGAL_TAIWAN_EXAMPLES,
}
