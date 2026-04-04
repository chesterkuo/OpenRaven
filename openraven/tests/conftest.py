from __future__ import annotations

from pathlib import Path

import pytest

from openraven.config import RavenConfig


@pytest.fixture
def tmp_working_dir(tmp_path: Path) -> Path:
    """Provide a temporary working directory for tests."""
    wd = tmp_path / "test_kb"
    wd.mkdir()
    return wd


@pytest.fixture
def config(tmp_working_dir: Path) -> RavenConfig:
    """Provide a test RavenConfig pointing to a temp directory."""
    return RavenConfig(
        working_dir=tmp_working_dir,
        gemini_api_key="test-key",
        anthropic_api_key="test-key",
    )


SAMPLE_EN_TEXT = """
# Architecture Decision Record: Migrate to Event-Driven Architecture

## Status: Accepted

## Context
Our monolithic order processing system handles 50,000 orders/day but cannot scale beyond 80,000.
The team evaluated three approaches: horizontal scaling, CQRS, and event-driven architecture.

## Decision
We chose event-driven architecture using Apache Kafka because:
1. Decouples order intake from fulfillment processing
2. Enables independent scaling of consumer services
3. Provides natural audit trail via event log

## Consequences
- Positive: 5x throughput improvement in load tests
- Negative: Added operational complexity for Kafka cluster management
- Risk: Eventual consistency requires careful handling of order status queries
"""

SAMPLE_ZH_TEXT = """
# 投資研究報告：台灣半導體產業分析

## 摘要
台灣半導體產業在全球供應鏈中佔據關鍵地位。台積電（TSMC）在先進製程市場佔有率超過 90%。

## 關鍵發現
1. 先進封裝技術（CoWoS）產能將在 2026 年擴充 3 倍
2. AI 晶片需求推動營收年增率達 25%
3. 地緣政治風險促使客戶分散供應鏈

## 估值分析
目前本益比（P/E）為 22 倍，低於五年平均 25 倍。考慮 AI 需求成長，目標價上調 15%。

## 風險因素
- 中美貿易摩擦升級
- 先進製程良率低於預期
- 全球經濟衰退導致需求下滑
"""
