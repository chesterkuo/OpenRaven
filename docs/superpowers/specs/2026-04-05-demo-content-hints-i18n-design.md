# Demo Content, Suggested Questions & i18n

**Date**: 2026-04-05
**Status**: Approved

## Overview

Three enhancements to make the demo sandbox a compelling onboarding experience:

1. **Quality demo documents** — 30 real, educational markdown files (10 per theme) with interconnected content that produces a rich knowledge graph
2. **Suggested question chips** — 4 clickable starter questions per theme, data-driven from `.theme.json`
3. **Multi-locale demo UI** — New `demo.json` i18n namespace across 12 locales

---

## 1. Demo Documents

### Approach

Each theme gets 10 well-crafted markdown documents (1-3 pages each) with real educational content. Documents cross-reference each other to create a rich knowledge graph with meaningful entity connections.

After creating the files, run the ingestion pipeline on each theme directory to build the LightRAG knowledge graph.

### Legal Documents (~/demo/legal-docs/)

| File | Title | Key Entities |
|------|-------|-------------|
| nda.md | Non-Disclosure Agreement Guide | confidentiality, trade secrets, breach remedies |
| employment-agreement.md | Employment Agreement Essentials | compensation, termination, benefits, at-will |
| saas-tos.md | SaaS Terms of Service | SLA, liability caps, data ownership |
| privacy-policy.md | Privacy Policy (GDPR & CCPA) | personal data, consent, data subject rights |
| ip-assignment.md | IP Assignment Agreement | intellectual property, work product, inventions |
| consulting-agreement.md | Consulting Services Agreement | scope, deliverables, payment, independent contractor |
| dpa.md | Data Processing Agreement | sub-processors, data breach notification, GDPR Art.28 |
| software-license.md | Software License Agreement | open source, proprietary, warranties, indemnification |
| non-compete.md | Non-Compete & Non-Solicit Guide | enforceability, jurisdiction, blue-pencil doctrine |
| compliance-checklist.md | Regulatory Compliance Checklist | SOC 2, HIPAA, ISO 27001, audit requirements |

### Tech Wiki (~/demo/tech-wiki/)

| File | Title | Key Entities |
|------|-------|-------------|
| api-design.md | REST API Design Principles | endpoints, versioning, pagination, HATEOAS |
| microservices.md | Microservices Architecture | service mesh, decomposition, eventual consistency |
| database-scaling.md | Database Scaling Strategies | sharding, replication, read replicas, caching |
| ci-cd.md | CI/CD Pipeline Guide | GitHub Actions, testing pyramid, blue-green deploy |
| authentication.md | Authentication & OAuth 2.0 | JWT, OIDC, session management, refresh tokens |
| docker-kubernetes.md | Docker & Kubernetes Essentials | containers, pods, Helm, service discovery |
| graphql-vs-rest.md | GraphQL vs REST Comparison | schemas, resolvers, N+1, batching |
| monitoring.md | Monitoring & Observability | Prometheus, Grafana, distributed tracing, SLOs |
| security.md | Application Security Best Practices | OWASP Top 10, CSRF, XSS, SQL injection |
| performance.md | Performance Optimization Guide | caching layers, CDN, profiling, lazy loading |

### Research Papers (~/demo/research-papers/)

| File | Title | Key Entities |
|------|-------|-------------|
| transformers.md | Transformer Architecture Deep Dive | attention mechanism, self-attention, positional encoding |
| rag.md | Retrieval-Augmented Generation (RAG) | retrieval, grounding, hallucination reduction |
| llm-overview.md | Large Language Models Overview | GPT, scaling laws, emergent abilities, tokenization |
| vector-databases.md | Vector Databases & Embeddings | similarity search, ANN, HNSW, cosine distance |
| knowledge-graphs.md | Knowledge Graphs in AI | entity extraction, ontologies, graph reasoning |
| fine-tuning.md | Fine-tuning vs Prompt Engineering | LoRA, few-shot, instruction tuning, adapter layers |
| ai-safety.md | AI Safety & Alignment | reward hacking, constitutional AI, red-teaming |
| multimodal.md | Multimodal AI Systems | vision-language models, CLIP, cross-modal attention |
| rlhf.md | RLHF: Training from Human Feedback | preference learning, PPO, DPO, reward modeling |
| nas.md | Neural Architecture Search | AutoML, search spaces, one-shot NAS, efficiency |

---

## 2. Suggested Question Chips

### Data Model

Extend `.theme.json` with a `suggested_questions` array:

```json
{
  "name": "Legal Documents",
  "description": "Sample legal contracts, NDAs, and compliance documents",
  "suggested_questions": [
    "What are the key differences between an NDA and a non-compete agreement?",
    "What GDPR obligations does a data processor have?",
    "How should IP ownership be handled in consulting agreements?",
    "What are the essential clauses in a SaaS Terms of Service?"
  ]
}
```

### Backend

Extend `ThemeInfo` model and `_list_themes()` in `demo.py` to include `suggested_questions: list[str]`.

### Frontend

In `AskPage` (when in demo mode): when `messages.length === 0`, show a 2x2 grid of clickable question chips below the hero heading. Clicking a chip fills the input and auto-submits.

The chips come from the theme data — `DemoAppShell` or `useAuth` passes the theme's suggested questions down. Simplest: fetch `/api/demo/themes` and find the active theme's questions.

---

## 3. i18n — demo.json Namespace

### New Keys

```json
{
  "heroTitle": "Try OpenRaven",
  "heroSubtitle": "Explore a sample knowledge base — no account required.",
  "starting": "Starting...",
  "ctaText": "Want the full experience?",
  "ctaLink": "Create an account",
  "banner": "You're exploring a demo",
  "bannerSignup": "Sign up",
  "bannerCta": "to create your own knowledge base.",
  "switchTheme": "Switch theme"
}
```

### Locales

12 locales: en, zh-TW, zh-CN, ja, ko, fr, es, nl, it, vi, th, ru

### What Stays English

- Theme names, descriptions, suggested questions (KB content is English)
- Document content

### Files to Update

- Create `openraven-ui/public/locales/{locale}/demo.json` x12
- Update `DemoLandingPage.tsx` — use `useTranslation("demo")`
- Update `DemoAppShell` in `App.tsx` — use demo namespace for banner
- `ConversationSidebar.tsx` already uses common namespace — keep as-is

---

## Out of Scope

- Translating document content into other languages
- Auto-generating suggested questions from the knowledge graph
- Theme-specific icons or images
