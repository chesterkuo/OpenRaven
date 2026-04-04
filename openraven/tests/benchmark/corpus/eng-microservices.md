# Microservices Architecture Overview

## Service Inventory

### Order Service
- Responsibility: Order lifecycle management (create, update, cancel)
- Database: PostgreSQL (orders, line_items tables)
- Dependencies: Inventory Service, Payment Service
- SLA: 99.9% uptime, p99 latency < 200ms

### Inventory Service
- Responsibility: Stock tracking, reservation, replenishment alerts
- Database: Redis (real-time counts) + PostgreSQL (historical)
- Dependencies: None (event-driven updates from suppliers)
- SLA: 99.95% uptime, p99 latency < 50ms

### Payment Service
- Responsibility: Payment processing, refunds, fraud detection
- Database: PostgreSQL with encryption at rest
- Dependencies: Stripe API (primary), PayPal (fallback)
- SLA: 99.99% uptime, p99 latency < 500ms

### Notification Service
- Responsibility: Email, SMS, push notifications
- Database: MongoDB (notification templates and history)
- Dependencies: SendGrid (email), Twilio (SMS), Firebase (push)
- SLA: 99.9% uptime, best-effort delivery

## Inter-Service Communication
- Synchronous: gRPC for service-to-service calls requiring immediate response
- Asynchronous: Apache Kafka for event-driven workflows
- Service discovery: Consul with health checks every 10 seconds

## Deployment
- Container runtime: Kubernetes on AWS EKS
- CI/CD: GitHub Actions → Docker build → ArgoCD GitOps deployment
- Environments: dev, staging, production (3 regions)
