# Architecture Decision Record: Event-Driven Architecture with Apache Kafka

## Status: Accepted (2025-06-15)

## Context
Our e-commerce platform processes 50,000 orders per day through a monolithic order processing system. Performance testing shows the system cannot scale beyond 80,000 orders/day. The engineering team evaluated three approaches: horizontal scaling of the monolith, CQRS pattern, and event-driven architecture.

## Decision
We chose event-driven architecture using Apache Kafka as the message broker because:
1. Decouples order intake from fulfillment processing, allowing each to scale independently
2. Kafka's partitioned log provides natural ordering guarantees per customer
3. Consumer groups enable horizontal scaling of downstream processors
4. Event log serves as a built-in audit trail for compliance

## Implementation Details
- Kafka cluster: 3 brokers, replication factor 2
- Key topics: `order.created`, `order.fulfilled`, `inventory.updated`, `payment.processed`
- Schema Registry using Avro for event schema evolution
- Consumer lag monitoring via Prometheus + Grafana

## Consequences
- Positive: Load tests show 5x throughput improvement (250,000 orders/day capacity)
- Positive: Deployment independence — fulfillment team ships independently
- Negative: Added operational complexity for Kafka cluster management
- Negative: Eventual consistency requires careful handling of order status queries
- Risk: Message ordering across partitions needs application-level handling
