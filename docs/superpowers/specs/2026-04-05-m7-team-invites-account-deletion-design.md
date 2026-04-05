# M7.2 Team Invites + M7.9 Account Deletion — Design Spec

**Date**: 2026-04-05
**Scope**: Shareable invite links for team members + account deletion with KB export, unified in a Settings page

---

## M7.2: Team Members & Invite Flow

### Goal
Let tenant owners invite members via shareable invite links. Members share the same knowledge base.

### Database Changes

**New table: `invitations`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | String(36) PK | UUID |
| `tenant_id` | String(36) FK→tenants | CASCADE on delete |
| `token` | String(64) UNIQUE | 32-char hex, URL-safe |
| `created_by` | String(36) FK→users | Who created the invite |
| `expires_at` | DateTime(tz) | 48 hours from creation |
| `max_uses` | Integer | Nullable = unlimited |
| `use_count` | Integer | Default 0 |
| `created_at` | DateTime(tz) | Default now() |

**Alembic migration**: 004_invitations.py (down_revision = "003")

### Module: `openraven/src/openraven/auth/invitations.py`

```python
def create_invitation(engine, tenant_id, created_by, expires_hours=48, max_uses=None) -> dict
def accept_invitation(engine, token, user_id) -> str  # returns tenant_id
def list_invitations(engine, tenant_id) -> list[dict]
def revoke_invitation(engine, invitation_id, tenant_id) -> bool
```

**Invitation logic:**
- `create_invitation`: generates 32-char hex token via `secrets.token_hex(16)`, inserts row, returns `{id, token, expires_at}`
- `accept_invitation`: validates token (exists, not expired, use_count < max_uses or max_uses is None), adds user to `tenant_members` with role `member`, increments `use_count`, returns `tenant_id`. Raises ValueError if invalid/expired/maxed. Raises ValueError if user already a member.
- `list_invitations`: returns active (non-expired) invitations for tenant
- `revoke_invitation`: deletes invitation by id, scoped to tenant_id for safety

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/team/invite | Owner only | Create invite link |
| GET | /api/team/invite/{token} | Public | Validate invite (check if valid) |
| POST | /api/team/invite/{token}/accept | Auth required | Accept invite, join tenant |
| GET | /api/team/members | Auth required | List tenant members |
| DELETE | /api/team/members/{user_id} | Owner only | Remove member |
| GET | /api/team/invitations | Owner only | List active invitations |
| DELETE | /api/team/invitations/{id} | Owner only | Revoke invitation |

**Ownership check:** All owner-only endpoints verify `request.state.auth.user_id` matches `tenants.owner_user_id`.

**Accept flow:**
1. User receives invite link (e.g., `https://app.openraven.com/invite/{token}`)
2. If not logged in → redirect to signup/login with `?invite={token}` param
3. After auth → POST /api/team/invite/{token}/accept
4. User's active tenant switches to the invited tenant

---

## M7.9: Account Deletion

### Goal
Let users export their knowledge base and permanently delete their account and all associated data.

### Deletion Scope

When a user deletes their account, remove (in order):
1. Tenant file directory (`/data/tenants/{tenant_id}/`) — KB data, wiki, courses, graphs
2. `audit_logs` where tenant_id matches
3. `invitations` where tenant_id matches
4. `tenant_members` where tenant_id matches
5. `tenants` record (if owner and sole member)
6. `sessions` where user_id matches
7. `password_reset_tokens` where user_id matches
8. `users` record

**Blocking condition:** If user is tenant owner AND other members exist → block deletion. Owner must remove all members or transfer ownership first.

### Module: `openraven/src/openraven/auth/account.py`

```python
def check_deletion_eligibility(engine, user_id) -> dict
    # Returns {eligible: bool, reason: str, tenant_id: str, member_count: int}

def delete_account(engine, user_id, tenant_id, data_dir: Path) -> None
    # Cascading delete: files → DB records → user

def export_knowledge_base(config, tenant_id) -> Path
    # Creates zip of wiki/ + graphml + metadata.json, returns zip path
```

**Export contents (zip file):**
- `wiki/*.md` — all wiki articles
- `knowledge_graph.graphml` — full graph export
- `metadata.json` — `{exported_at, tenant_id, file_count, entity_count, topic_count}`

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/account | Auth required | Account info + deletion eligibility |
| GET | /api/account/export | Auth required | Download KB as zip |
| DELETE | /api/account | Auth required | Delete account (password in body) |

**DELETE /api/account request body:**
```json
{"password": "user's current password"}
```
Verifies password before deletion. Returns 200 with `{deleted: true}` and clears session cookie.

---

## Settings Page UI

### Structure: `SettingsPage.tsx` at `/settings`

**Tab navigation:** Team | Account

### Team Tab
- **Member list table**: Email, Role (owner badge / member), Joined date, Remove button (owner only, not on self)
- **Create Invite Link** button (owner only) → generates link, shows in a copyable field with expiry info
- **Active invitations** table: Token (truncated to 8 chars), Created date, Uses (`use_count`/`max_uses` or "unlimited"), Expires, Revoke button

### Account Tab
- **Account info**: Email, name, member since date
- **Export section**: "Export Knowledge Base" button → downloads zip
- **Danger zone** (red-bordered section at bottom):
  - If owner with members: warning "Remove all team members before deleting your account"
  - If eligible: "Delete Account" button → confirmation dialog:
    - Warning text: "This will permanently delete your account, knowledge base, and all associated data. This cannot be undone."
    - Password input field
    - "Cancel" and "Delete My Account" (red) buttons

### BFF Proxy
Add `/api/team/*`, `/api/team`, `/api/account/*`, `/api/account` to `proxyToCore` routes.

### Nav
Add "Settings" link in nav (after Audit), using `t('nav.settings')` i18n key.

---

## Testing Strategy

### M7.2 Tests (`test_team.py`)
- `create_invitation` returns token + expiry
- `accept_invitation` adds user to tenant_members
- `accept_invitation` rejects expired token
- `accept_invitation` rejects maxed-out token
- `accept_invitation` rejects if already a member
- `revoke_invitation` deletes invitation
- API: POST /api/team/invite requires owner
- API: POST /api/team/invite/{token}/accept joins tenant
- API: DELETE /api/team/members/{id} removes member
- API: Non-owner cannot invite/remove

### M7.9 Tests (`test_account.py`)
- `check_deletion_eligibility` returns eligible for sole owner
- `check_deletion_eligibility` returns blocked for owner with members
- `delete_account` removes all DB records
- `delete_account` removes tenant directory
- `export_knowledge_base` creates valid zip with wiki + graphml
- API: DELETE /api/account requires correct password
- API: DELETE /api/account rejects wrong password
- API: DELETE /api/account blocked when members exist
- API: GET /api/account/export returns zip

---

## Out of Scope
- Email-based invitations (requires transactional email service)
- Ownership transfer (remove members first, then delete)
- Role-based access control beyond owner/member
- Invite link custom expiry UI (always 48h)
- Data retention receipts/certificates
