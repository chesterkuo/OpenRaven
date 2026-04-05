# M7 Implementation Plan — Design Spec

**Date**: 2026-04-05
**Scope**: Remaining PRD gaps after M6 + quick wins, targeting commercial launch readiness
**PRD Reference**: `OpenRaven_PRD_v1.0.md`

---

## M7 Goal

**Make OpenRaven commercially viable.** M1-M6 built the product; M7 builds the business infrastructure. After M7, OpenRaven can accept payments, serve enterprise customers, and be installed via `pip`.

---

## M7 Phases

### M7.1: Billing & Subscriptions (Stripe)

**Priority**: P0 — No revenue without this.

**Scope:**
- Stripe integration for subscription management
- 4 tiers: Core (free), Personal ($19/mo), Expert ($49/mo), Team ($35/person/mo)
- Billing page in UI (plan selection, payment method, invoices)
- Webhook handler for subscription lifecycle (created, updated, cancelled, payment failed)
- Usage tracking: file count, storage used, API calls (for metered billing in future)
- Trial period: 14-day free trial for Personal/Expert
- Stripe Customer Portal link for self-service management

**Backend changes:**
- New `billing/` module: Stripe client, webhook handler, plan enforcement
- New DB tables: `subscriptions`, `usage_records`
- Middleware: check subscription status before premium features (connectors, agents, courses)
- Feature gating: free tier gets core features only

**UI changes:**
- New BillingPage: plan comparison, upgrade/downgrade, payment form (Stripe Elements)
- Plan badge in nav bar
- Upgrade prompts when hitting tier limits

**Estimated effort**: 5-7 days

---

### M7.2: Team Members & Invite Flow

**Priority**: P1 — Required for Team tier ($35/person/mo).

**Scope:**
- Invite members to tenant by email
- Invitation table with token + expiry (48h)
- Accept invite flow: creates account or links existing account to tenant
- Roles: owner, admin, member (start with owner + member)
- Member management UI: list members, invite, remove, change role
- Shared knowledge base: all tenant members see same KB

**Backend changes:**
- New endpoints: `POST /api/tenants/invite`, `POST /api/tenants/invite/{token}/accept`, `GET /api/tenants/members`, `DELETE /api/tenants/members/{id}`
- Email sending: use a transactional email service (SendGrid or AWS SES) for invites and password resets
- Invitation token: SHA-256 hashed, single-use, 48h expiry

**UI changes:**
- New TeamPage: member list, invite form, pending invitations
- Nav update: show team name if in team tenant

**Estimated effort**: 3-4 days

---

### M7.3: E2EE Cloud Sync

**Priority**: P1 — Core privacy differentiator per PRD section 5.4.

**Scope:**
- Client-side AES-256-GCM encryption before upload
- Encryption key derived from user passphrase (PBKDF2), never sent to server
- Server stores only ciphertext
- Sync API: upload encrypted KB snapshots, download to new device
- Conflict resolution: last-write-wins with timestamp
- Key recovery: optional recovery key (displayed once, user responsibility to save)

**Backend changes:**
- New `sync/` module: encrypted blob storage (S3 or local filesystem)
- New endpoints: `POST /api/sync/upload`, `GET /api/sync/download`, `GET /api/sync/status`
- New DB table: `sync_snapshots` (user_id, encrypted_blob_url, timestamp, checksum)

**UI changes:**
- New SyncPage: enable sync, set passphrase, sync status, device list
- Settings: encryption passphrase management, recovery key display

**Dependencies:** `cryptography` (Python) for server-side utilities, Web Crypto API (browser) for client-side encryption.

**Estimated effort**: 5-7 days

---

### M7.4: SSO/SAML (Enterprise)

**Priority**: P2 — Enterprise procurement gate.

**Scope:**
- SAML 2.0 SP (Service Provider) implementation
- Support Okta and Azure AD as IdPs (Identity Providers)
- Tenant-level SSO configuration (admin sets SAML metadata URL)
- JIT (Just-In-Time) user provisioning on first SAML login
- Enforce SSO: option to disable email/password login for SSO-enabled tenants

**Backend changes:**
- New `auth/saml.py`: SAML request/response handling
- New DB fields: `tenants.saml_metadata_url`, `tenants.sso_enforced`
- New endpoints: `GET /api/auth/saml/login`, `POST /api/auth/saml/callback`, `PUT /api/tenants/sso`

**UI changes:**
- SSO configuration in tenant settings (admin only)
- SAML login button on login page when SSO enabled

**Dependencies:** `python3-saml` or `pysaml2` package.

**Estimated effort**: 4-5 days

---

### M7.5: Audit Logs

**Priority**: P2 — SOC 2 prerequisite, enterprise requirement.

**Scope:**
- Log all significant actions: login, logout, file ingest, file delete, KB query, agent deploy, member invite/remove, settings change
- Immutable append-only log table
- Filterable audit log UI (by user, action type, date range)
- Export audit log as CSV
- Retention: 90 days default, configurable per tenant

**Backend changes:**
- New `audit/` module: `log_action(user_id, tenant_id, action, details)`
- New DB table: `audit_logs` (id, user_id, tenant_id, action, details_json, ip_address, timestamp)
- Middleware: auto-log auth events
- Decorator or helper for logging API actions

**UI changes:**
- New AuditLogPage (admin only): table with filters, CSV export button

**Estimated effort**: 2-3 days

---

### M7.6: Outlook Connector

**Priority**: P2 — Enterprise/Office 365 users.

**Scope:**
- Microsoft Graph API integration for Outlook email
- OAuth 2.0 with Azure AD app registration
- Sync sent emails (matching Gmail connector pattern)
- Extract email body, attachments, metadata
- Incremental sync via Microsoft Graph delta queries

**Backend changes:**
- New `connectors/outlook.py`: OAuth flow, email sync, attachment download
- New endpoints: `GET /api/connectors/outlook/auth-url`, `GET /api/connectors/outlook/callback`, `POST /api/connectors/outlook/sync`
- Token storage: `working_dir/outlook_token.json`

**UI changes:**
- Add Outlook card to ConnectorsPage (same pattern as Gmail)

**Dependencies:** `msal` (Microsoft Authentication Library) package.

**Estimated effort**: 3-4 days

---

### M7.7: Package Publishing (PyPI + Homebrew)

**Priority**: P1 — PRD's install hook is `pip install openraven`.

**Scope:**
- PyPI package: `openraven` with `raven` CLI entry point
- `pyproject.toml` with proper metadata, dependencies, entry points
- Homebrew formula (tap: `openraven/tap/openraven`)
- GitHub Actions CI/CD: test → build → publish on tag
- README with quick start instructions matching PRD section 4.4

**Changes:**
- `openraven/pyproject.toml`: package metadata, entry points
- `.github/workflows/publish.yml`: CI/CD pipeline
- `homebrew-openraven/` tap repo (separate repo or formula file)

**Estimated effort**: 2-3 days

---

### M7.8: Chrome Extension Polish + Web Store

**Priority**: P2 — PRD milestone M2 (deferred).

**Scope:**
- Full popup UI: save current page, view recent saves, search KB
- Content script: right-click context menu "Save to OpenRaven"
- Options page: configure API URL, auth token
- Chrome Web Store listing: screenshots, description, privacy policy
- Support both local and cloud API URLs

**Estimated effort**: 3-4 days

---

### M7.9: Account Deletion & Data Sovereignty

**Priority**: P2 — PRD section 5.6 "Delete-first".

**Scope:**
- Account deletion flow: confirm → 7-day grace period → permanent deletion
- Delete all: user record, tenant data, files, graph data, vector embeddings, sessions
- Deletion confirmation certificate (downloadable receipt)
- Data export before deletion prompt

**Estimated effort**: 2-3 days

---

## Recommended Sequence

```
Phase 1 (Week 1-2): Revenue foundation
  M7.7 Package Publishing    ← unblocks community growth
  M7.1 Billing & Stripe      ← unblocks revenue
  M7.5 Audit Logs            ← quick win, needed for enterprise

Phase 2 (Week 3-4): Team & enterprise
  M7.2 Team Members & Invite ← unblocks Team tier
  M7.4 SSO/SAML              ← unblocks enterprise sales
  M7.6 Outlook Connector     ← enterprise connector

Phase 3 (Week 5-6): Privacy & polish
  M7.3 E2EE Cloud Sync       ← core differentiator
  M7.8 Chrome Extension       ← community feature
  M7.9 Account Deletion       ← compliance
```

**Total estimated effort**: 29-40 days

---

## Dependencies & Infrastructure

| Need | For | Options |
|------|-----|---------|
| Stripe account | M7.1 Billing | Stripe standard account |
| Transactional email | M7.2 Invites, existing password reset | SendGrid (free tier: 100/day) or AWS SES |
| S3 or equivalent | M7.3 E2EE Sync | AWS S3, GCS, or MinIO (self-hosted) |
| Azure AD app registration | M7.4 SSO, M7.6 Outlook | Microsoft 365 developer account |
| PyPI account | M7.7 Publishing | PyPI trusted publisher via GitHub Actions |
| Chrome Developer account | M7.8 Extension | $5 one-time registration |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| `pip install openraven && raven add ./docs/` works | M7.7 |
| First paying customer | M7.1 |
| Team tier functional (3+ members sharing KB) | M7.2 |
| Enterprise demo-ready (SSO + audit logs) | M7.4 + M7.5 |
| E2EE sync between 2 devices | M7.3 |
| Chrome Web Store listed | M7.8 |

---

## Out of Scope for M7

- Kubernetes deployment (Docker Compose sufficient)
- Qdrant vector storage (NanoVectorDB sufficient for current scale)
- Schema Marketplace (community feature, post-launch)
- SOC 2 Type I audit (requires M7.5 audit logs first, then external auditor)
- Vertical industry add-ons (Legal/Finance enterprise pricing)
- Mobile apps (Capacitor — future milestone)
