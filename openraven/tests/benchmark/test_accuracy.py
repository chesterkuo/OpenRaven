from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from openraven.graph.rag import QueryResult


def evaluate_facts(answer: str, expected_facts: list[str]) -> bool:
    answer_lower = answer.lower()
    return all(fact.lower() in answer_lower for fact in expected_facts)


def evaluate_citation(sources: list[dict], expected_docs: list[str]) -> bool:
    if not expected_docs:
        return True
    returned_docs = {s.get("document", "") for s in sources}
    for expected in expected_docs:
        for returned in returned_docs:
            if expected in returned:
                return True
    return False


class TestTier1Accuracy:

    def test_qa_accuracy_above_80_percent(self, benchmark_kb, ground_truth):
        pipeline, config, corpus_dir = benchmark_kb
        questions = ground_truth["questions"]

        correct = 0
        total = len(questions)
        failures = []

        for q in questions:
            result: QueryResult = asyncio.get_event_loop().run_until_complete(
                pipeline.ask_with_sources(q["question"], mode=q["mode"])
            )
            if evaluate_facts(result.answer, q["expected_facts"]):
                correct += 1
            else:
                failures.append(f"  {q['id']}: expected {q['expected_facts']}, got: {result.answer[:100]}...")

        accuracy = correct / total if total > 0 else 0
        report = f"\nTier 1 QA Accuracy: {correct}/{total} ({accuracy:.1%})"
        if failures:
            report += "\nFailed questions:\n" + "\n".join(failures[:10])
        print(report)

        assert accuracy >= 0.80, f"QA accuracy {accuracy:.1%} is below 80% threshold.\n{report}"

    def test_citation_accuracy_above_95_percent(self, benchmark_kb, ground_truth):
        pipeline, config, corpus_dir = benchmark_kb
        questions = ground_truth["questions"]

        correct = 0
        total = len(questions)
        failures = []

        for q in questions:
            result: QueryResult = asyncio.get_event_loop().run_until_complete(
                pipeline.ask_with_sources(q["question"], mode=q["mode"])
            )
            if evaluate_citation(result.sources, q["source_documents"]):
                correct += 1
            else:
                returned = [s.get("document", "") for s in result.sources]
                failures.append(f"  {q['id']}: expected {q['source_documents']}, got: {returned}")

        accuracy = correct / total if total > 0 else 0
        report = f"\nTier 1 Citation Accuracy: {correct}/{total} ({accuracy:.1%})"
        if failures:
            report += "\nFailed citations:\n" + "\n".join(failures[:10])
        print(report)

        assert accuracy >= 0.95, f"Citation accuracy {accuracy:.1%} is below 95% threshold.\n{report}"


class TestTier2LLMJudge:

    @pytest.fixture(autouse=True)
    def _require_llm_judge(self, request):
        if not request.config.getoption("--llm-judge") and "tier2" not in (request.config.option.keyword or ""):
            pytest.skip("Tier 2 requires --llm-judge flag or -k tier2")

    def test_llm_judge_qa_accuracy_above_80_percent(self, benchmark_kb, ground_truth):
        from openraven.tests.benchmark.conftest import llm_judge_score

        pipeline, config, corpus_dir = benchmark_kb
        questions = ground_truth["questions"]

        scores = []
        failures = []

        for q in questions:
            result: QueryResult = asyncio.get_event_loop().run_until_complete(
                pipeline.ask_with_sources(q["question"], mode=q["mode"])
            )
            try:
                judgment = llm_judge_score(q["question"], q["expected_answer"], result.answer)
                scores.append(judgment["score"])
                if judgment["score"] < 3:
                    failures.append(f"  {q['id']} (score={judgment['score']}): {judgment['reason']}")
            except Exception as e:
                scores.append(1)
                failures.append(f"  {q['id']}: Judge error — {e}")

        correct = sum(1 for s in scores if s >= 3)
        total = len(scores)
        accuracy = correct / total if total > 0 else 0
        avg_score = sum(scores) / total if total > 0 else 0

        report = f"\nTier 2 QA Accuracy: {correct}/{total} ({accuracy:.1%}), Avg Score: {avg_score:.1f}/5.0"
        if failures:
            report += "\nLow-scoring questions:\n" + "\n".join(failures[:10])
        print(report)

        assert accuracy >= 0.80, f"LLM judge accuracy {accuracy:.1%} below 80% threshold.\n{report}"

    def test_citation_quality_excerpts_in_source(self, benchmark_kb, ground_truth):
        pipeline, config, corpus_dir = benchmark_kb
        questions = ground_truth["questions"]

        verified = 0
        total_with_sources = 0
        failures = []

        for q in questions:
            result: QueryResult = asyncio.get_event_loop().run_until_complete(
                pipeline.ask_with_sources(q["question"], mode=q["mode"])
            )
            if not result.sources:
                continue

            total_with_sources += 1
            any_valid = False

            for s in result.sources:
                excerpt = s.get("excerpt", "").strip()
                if not excerpt:
                    continue
                for corpus_file in corpus_dir.glob("*.md"):
                    content = corpus_file.read_text(encoding="utf-8")
                    if excerpt[:50] in content:
                        any_valid = True
                        break
                if any_valid:
                    break

            if any_valid:
                verified += 1
            else:
                failures.append(f"  {q['id']}: excerpt not found — {result.sources[0].get('excerpt', '')[:60]}")

        accuracy = verified / total_with_sources if total_with_sources > 0 else 1.0
        report = f"\nTier 2 Citation Quality: {verified}/{total_with_sources} ({accuracy:.1%})"
        if failures:
            report += "\nUnverified citations:\n" + "\n".join(failures[:10])
        print(report)

        assert accuracy >= 0.95, f"Citation quality {accuracy:.1%} below 95% threshold.\n{report}"
