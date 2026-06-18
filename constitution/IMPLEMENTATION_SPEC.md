# IMPLEMENTATION_SPEC.md

**Purpose:** The execution contract. A coding agent (Claude Code / Codex) builds an app from *this file plus the YAML configs*. It does not infer architecture from `ONBOARDING_ARCHITECTURE.md` — that's the human strategy doc. Where this spec and the YAMLs disagree, **the YAMLs win** (they are the runtime source of truth).

**Golden rule for the agent:** Tiers, events, risk thresholds, RBAC, and data fields are **config, not code**. Read them from the YAML files at runtime. Never hardcode a threshold or a tier→action mapping inline.

---

## 1. Reference stack (swappable via adapters)

| Concern | Reference choice | Adapter seam | Swappable for |
|---|---|---|---|
| App framework | Next.js (App Router) + TypeScript | — | Remix, SvelteKit |
| Database | PostgreSQL + Prisma | `db/` | Drizzle, raw SQL |
| Auth / CIAM | Clerk (passkeys, orgs, OTP) | `AuthProvider` | WorkOS, Auth0, self-hosted SimpleWebAuthn |
| Enterprise SSO / SCIM | WorkOS | `SsoProvider` | Okta, Entra |
| Payments | Stripe (Billing, Checkout, Tax, Radar) | `BillingProvider` | — |
| Identity / KYC | Persona (doc + liveness; mDL/VC roadmap) | `IdentityVerifier` | Stripe Identity, Alloy, SpruceID |
| KYB | Middesk | `BusinessVerifier` | — |
| Sanctions | ComplyAdvantage (or vendor-native) | `SanctionsScreener` | — |
| Bot defense | Cloudflare Turnstile | `BotCheck` | hCaptcha |
| Events sink | PostHog | `EventSink` | Segment, Snowplow |
| Risk engine | internal module reading `RISK_POLICIES.yaml` | `risk.evaluate()` | — |

**Adapter rule:** every external dependency sits behind a typed interface in `lib/adapters/`. Business logic never imports a vendor SDK directly.

---

## 2. Routes / screens

| Route | Tier to access | Purpose |
|---|---|---|
| `/start` | T0 | Single entry. Email field only. Decides sign-in vs sign-up. |
| `/auth/passkey` | T0→T1 | Passkey register/authenticate (Conditional UI / autofill). |
| `/auth/otp` | T0→T1 | OTP fallback only (device lacks WebAuthn). |
| `/auth/recovery` | always-on | Device rotation / lost-access. No SMS for high-risk. |
| `/welcome` | T1 | First value: seeded sandbox + one guided action. |
| `/onboarding` | T1→T2 | Progressive profile, contextual & skippable. |
| `/verify-identity` | T2→T3 | Step-up IDV. Rendered only when `risk.evaluate` returns `STEP_UP` to T3. |
| `/billing/upgrade` | T2 | Hosted checkout (Stripe). |
| `/org/invite` | T2+ | Send invites; manage seats. |
| `/join/[token]` | T0→T1 | Accept invite → enroll passkey → join at set role. |
| `/join/domain` | T1 | Verified-domain auto-join request. |
| `/admin` | T4 | Privileged admin. Requires AAL3 + step-up. |
| `/settings/security` | T1+ | Manage passkeys, devices, recovery methods. |

Constraint: `/welcome` must be reachable at T1 with **zero** profile/identity fields collected.

---

## 3. Database schema (Prisma-style; names are the contract)

```
User            id, email(unique), email_verified(bool), status(enum: pending|active|suspended),
                tier(int 0-4), current_aal(int 0|2|3), created_at, updated_at
AuthCredential  id, user_id->User, type(enum: passkey|otp|sso), provider,
                public_key, aaguid, device_bound(bool), transports(string[]),
                created_at, last_used_at
Session         id, user_id->User, device_id->Device, created_at, expires_at, refresh_rotated_at
Device          id, user_id->User, fingerprint, first_seen, last_seen, trusted(bool)
RecoveryEvent   id, user_id->User, method, fallback_used(bool), anomaly_score,
                approved_by, created_at
Organization    id, name, domain, sso_enabled(bool), scim_enabled(bool), plan, created_at
Membership      id, org_id->Organization, user_id->User, role(enum: see RBAC.yaml),
                status(enum: invited|active|removed), invited_by, created_at
Invite          id, org_id->Organization, email, role, token(unique), expires_at, accepted_at
IdentityVerification  id, user_id->User, method(enum: vc|mdl|doc_liveness), vendor,
                status(enum: pending|passed|failed|review), proofing_result, vendor_ref, completed_at
KybVerification id, org_id->Organization, ein, status, beneficial_owners(jsonb), completed_at
SanctionsScreening    id, subject_type(enum: user|org), subject_id, status(enum: clear|hit|pending),
                continuous(bool), last_screened_at
Subscription    id, org_id->Organization, stripe_customer_id, plan, status, mrr, trial_ends_at
PaymentMethod   id, org_id->Organization, stripe_pm_id, brand, last4, validated(bool)
TierChange      id, user_id->User, from_tier, to_tier, trigger, created_at
AccountLink     id, primary_user_id->User, linked_method, linked_identity, created_at
Consent         id, user_id->User, purpose, granted(bool), policy_version, created_at
AuditLog        id, actor_id, action, target, decision, context(jsonb), created_at
```

Fields that hold personal data must each have an entry in `DATA_GOVERNANCE.yaml`. PII columns are encrypted at rest; `public_key` is stored, secrets are not.

---

## 4. API endpoints

```
POST  /api/identify                         { email } -> { state: known|unknown, next }
POST  /api/auth/passkey/register/options
POST  /api/auth/passkey/register/verify
POST  /api/auth/passkey/authenticate/options
POST  /api/auth/passkey/authenticate/verify
POST  /api/auth/otp/request | /verify        (fallback only)
POST  /api/auth/recovery/initiate | /verify
GET   /api/me                                -> { user, tier, aal, memberships }
POST  /api/risk/evaluate                     { actor, action, context } -> Decision  (internal)
POST  /api/identity/verify/start             -> redirect/url to IdentityVerifier
POST  /api/identity/webhook                  (signed; updates IdentityVerification)
POST  /api/orgs                              { name } -> Organization
POST  /api/orgs/:id/invites                  { email, role } -> Invite
POST  /api/invites/:token/accept
POST  /api/orgs/:id/domain-join
POST  /api/billing/checkout                  -> Stripe Checkout session
POST  /api/billing/webhook                   (signed; updates Subscription)
POST  /api/account/link                      { method } (verified-email match only)
```

Every endpoint that performs a **gated action** calls `risk.evaluate()` first and obeys the returned decision. All webhooks verify signatures and reject replays (timestamp + idempotency key).

---

## 5. The risk engine

```typescript
type Tier = 0 | 1 | 2 | 3 | 4;

interface Actor   { userId?: string; tier: Tier; aal: 0 | 2 | 3; orgId?: string }
interface Action  { name: string }                 // resolved to requiredTier via RISK_POLICIES.yaml
interface Context {
  botScore?: number; deviceTrusted?: boolean; emailRisk?: number;
  velocity?: number; behaviorAnomaly?: number; livenessScore?: number;
  sanctionsStatus?: 'clear' | 'hit' | 'pending'; ip?: string; geo?: string;
}
type Decision = {
  result: 'allow' | 'step_up' | 'review' | 'deny';
  requiredTier?: Tier;
  reason: string;
  auditId: string;        // every decision writes an AuditLog row
};

function evaluate(actor: Actor, action: Action, ctx: Context): Decision;
```

Resolution order (defined fully in `RISK_POLICIES.yaml`):
1. Look up `action.name` → `requiredTier`.
2. Hard blocks first: `sanctionsStatus === 'hit'` → `deny`; `livenessScore` below threshold at IDV → `review`.
3. If `actor.tier >= requiredTier` **and** signals within thresholds → `allow`.
4. If `actor.tier < requiredTier` → `step_up` to `requiredTier`.
5. Elevated anomaly/velocity even when tier is sufficient → `step_up` (re-auth/MFA) or `review` per policy.

The function is pure with respect to inputs; it reads policy config, writes one audit row, returns one decision. No side effects on user state.

---

## 6. Event emission

Emit the canonical events in `EVENTS.yaml` at the exact points named there, with the exact property names. Events are the only source for the North Star metrics — if a metric can't be computed from emitted events, an event is missing. Never put secrets or raw PII in event properties (use ids / hashes).

---

## 7. Role permissions

Roles, the permission matrix, and the per-action minimum tier are defined in `RBAC.yaml`. The agent enforces permissions server-side on every endpoint; client-side gating is cosmetic only. Admin-class permissions require AAL3 (Tier 4) regardless of role.

---

## 8. Data fields

Every personal-data field is registered in `DATA_GOVERNANCE.yaml` with its seven attributes. The agent must not add a field that collects personal data without a corresponding registry entry; CI should fail if an un-registered PII field appears in the schema.

---

## 9. Tests & acceptance criteria

Full plan in `TEST_PLAN.md`. The build is accepted when:

- **A1** A new user reaches `/welcome` (T1) using only email + passkey, collecting zero profile/identity fields. Measured `acquisition_started → activation_reached` p50 < 60s in a seeded environment.
- **A2** No password code path exists anywhere. No SMS path exists for high-risk recovery.
- **A3** Every gated endpoint calls `risk.evaluate()` and honors the decision (proven by test doubles forcing each of allow/step_up/review/deny).
- **A4** Tabletop passes: a money-movement action, an admin-invite action, and an agent-authorization action each route to the correct tier gate and emit the correct events.
- **A5** Identity verification fires only on a `STEP_UP` to T3 — never earlier.
- **A6** Account link succeeds only on verified-email match; an unverified-email merge attempt is rejected.
- **A7** Invite billing occurs on accepted join, not on invite sent.
- **A8** `dead_end` event count is zero across all happy-path and fallback flows.
- **A9** Every PII field in the schema has a `DATA_GOVERNANCE.yaml` entry (CI-enforced).
- **A10** All webhooks reject unsigned and replayed requests.

---

## 10. Do NOT build (hard constraints)

The agent must refuse or flag, not silently implement, any of the following:

1. **No passwords.** No password field, hash, or reset flow. Passkey-first; OTP only as fallback.
2. **No SMS for privileged or high-risk recovery.** SMS is never an AAL step-up for Tier 3–4.
3. **No KYC/PII before a Tier-3 trigger.** Identity verification is just-in-time, gated by `risk.evaluate`.
4. **No auto-merge on unverified email.** Linking requires a verified-email match.
5. **No billing on `invite_sent`.** Seats bill on accepted join only.
6. **No inline risk thresholds or tier mappings.** Read `RISK_POLICIES.yaml` at runtime.
7. **No regulated overlays without signoff.** Scaffold HIPAA/CIP/COPPA logic behind a feature flag, but mark it `REQUIRES_COMPLIANCE_SIGNOFF` and do not enable it. Compliance correctness is not the agent's call.
8. **No agent-authorization / AP2 layer (Stage 08) enabled** until the three launch conditions in the architecture doc are met. Build primitives, keep the door closed.
9. **No first-value gating.** `/welcome` must not sit behind profile, payment, or identity.
10. **No secrets or raw PII in logs or event properties.** Ids and hashes only.
11. **No synced/exportable credential treated as AAL3.** AAL3 = non-exportable, device-bound authenticator only.
