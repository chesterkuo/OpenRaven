# Engineering All-Hands Meeting Notes — March 28, 2026

## Attendees
Alex Wong (CTO), Maria Garcia (VP Eng), James Lee (Staff Eng), Lisa Park (EM Platform), Tom Chen (EM Product), 42 other engineers

## Announcements

### Q2 OKRs
Alex presented the Q2 engineering OKRs:
1. Reduce p99 API latency from 450ms to under 200ms
2. Achieve 99.95% uptime (currently 99.8%)
3. Ship customer portal v2 by end of June
4. Migrate 60% of services to Kubernetes (currently 35%)

### New Hires
- 15 new engineers starting in April (8 backend, 4 frontend, 3 SRE)
- Onboarding bootcamp runs April 7-11
- Buddy assignments will be posted by April 3

### Infrastructure Update (Lisa Park)
- AWS costs reduced 22% in Q1 by rightsizing EC2 instances and switching to Graviton
- Database migration from MySQL to PostgreSQL is 70% complete — Order Service migrates next
- New monitoring stack: DataDog replacing custom Prometheus setup (rollout starts April 15)

## Q&A Highlights
- Q: "When will we deprecate the v1 API?" — James: "v1 sunset is September 30, 2026. Migration guide published next week."
- Q: "Can we get M2 MacBooks?" — Alex: "Approved for all engineers. IT placing order next week."
- Q: "What about the on-call rotation issue?" — Maria: "New rotation starts April 1. Maximum 1 week per quarter per engineer."

## Action Items
- [ ] James: Publish v1 API migration guide by April 4
- [ ] Lisa: Share Kubernetes migration runbook by April 7
- [ ] Tom: Finalize portal v2 sprint plan by April 1
