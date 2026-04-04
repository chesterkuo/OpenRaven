# New Engineer Onboarding Guide

## Week 1: Setup & Orientation

### Day 1
- HR paperwork and badge pickup
- Laptop setup: MacBook Pro M3, request via IT portal
- Install required tools: VS Code, Docker Desktop, Homebrew, Node.js 20 LTS
- Clone main repositories: `platform-api`, `customer-portal`, `infra-config`
- Set up VPN access (required for staging/production environments)

### Day 2-3
- Architecture overview session with your buddy
- Read ADR documents in `/docs/adr/` — focus on ADR-001 through ADR-010
- Set up local development environment using `make dev-setup`
- Run the test suite: `make test` should pass all 2,400+ tests

### Day 4-5
- Attend team standup and sprint planning
- Pick your first ticket: labeled `good-first-issue` in Jira
- Make your first PR — buddy will review

## Week 2: Deep Dive

### Development Workflow
- Branch naming: `feature/JIRA-123-short-description`
- PR requires: 1 approval, passing CI, no merge conflicts
- CI pipeline: lint → unit tests → integration tests → security scan (Snyk)
- Deploy: merge to main → auto-deploy to staging → manual promote to production

### Key Services to Understand
1. Platform API (Node.js/Express): Core business logic, REST + GraphQL
2. Auth Service (Go): OAuth 2.0, JWT, RBAC — handles all authentication
3. Event Bus (Kafka): Async messaging between services
4. Data Pipeline (Python/Airflow): ETL jobs, analytics, reporting

### On-Call
- Engineers join on-call rotation after 3 months
- Rotation: 1 week per quarter, PagerDuty alerts
- Escalation: L1 (you) → L2 (senior on-call) → L3 (CTO)
- Incident response playbook: `/docs/runbooks/incident-response.md`

## Useful Links
- Internal wiki: wiki.techcorp.internal
- CI/CD dashboard: ci.techcorp.internal
- Monitoring: datadog.techcorp.internal
- Design system: design.techcorp.internal
