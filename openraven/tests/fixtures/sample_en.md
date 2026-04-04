
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
