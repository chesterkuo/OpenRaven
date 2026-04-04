from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


CORPUS_DIR = Path(__file__).parent / "corpus"
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"


def pytest_addoption(parser):
    parser.addoption("--llm-judge", action="store_true", default=False, help="Run Tier 2 LLM judge tests")


@pytest.fixture(scope="session")
def ground_truth() -> dict:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def corpus_dir() -> Path:
    return CORPUS_DIR


@pytest.fixture(scope="session")
def benchmark_kb(tmp_path_factory) -> tuple[RavenPipeline, RavenConfig, Path]:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        pytest.skip("GEMINI_API_KEY required for benchmark tests")

    kb_dir = tmp_path_factory.mktemp("benchmark_kb")
    config = RavenConfig(working_dir=kb_dir)
    pipeline = RavenPipeline(config)

    files = sorted(CORPUS_DIR.glob("*.md"))
    assert len(files) >= 5, f"Expected at least 5 corpus files, found {len(files)}"

    asyncio.get_event_loop().run_until_complete(pipeline.add_files(files))
    return pipeline, config, CORPUS_DIR


def llm_judge_score(question: str, expected: str, actual: str) -> dict:
    import openai

    api_key = os.environ.get("GEMINI_API_KEY", "")
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    prompt = f"""Rate this answer on a 1-5 scale:
- 5: Fully correct, complete, no hallucination
- 4: Mostly correct, minor omissions
- 3: Partially correct, some inaccuracies
- 2: Mostly wrong or heavily hallucinated
- 1: Completely wrong or irrelevant

Question: {question}
Expected answer: {expected}
Actual answer: {actual}

Respond with JSON only: {{"score": N, "reason": "brief explanation"}}"""

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    text = response.choices[0].message.content.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
