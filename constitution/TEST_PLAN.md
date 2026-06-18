# TEST_PLAN.md

**Goal:** Prove the build matches the contract — not just that screens render. Tests are grouped by layer. The build is **accepted** only when every acceptance gate (A1–A10 in `IMPLEMENTATION_SPEC.md`) passes and the tabletop passes.

---

## 1. Auth & assurance

- Passkey register → authenticate round-trip succeeds; only the public key is persisted.
- Conditional UI (autofill) surfaces an existing passkey on `/start` for a known email.
- Device without WebAuthn falls back to OTP and emits `fallback_triggered`.
- **Negative:** no password field, hash, or reset route exists anywhere in the codebase (grep gate in CI).
- **Negative:** no SMS path is reachable for recovery of a Tier 3–4 account.
- AAL labelling: a synced passkey is recorded as `aal: 2`; only a non-exportable device-bound authenticator is recorded as `aal: 3`.

## 2. Risk engine (`risk.evaluate`)

- Each decision is forced via test doubles on context: `allow`, `step_up`, `review`, `deny` — and the caller obeys it.
- `sanctions_status == 'hit'` → `deny` regardless of tier.
- `liveness_score` below threshold at IDV → `review`.
- Tier gap → `step_up` to exactly the required tier (not higher).
- Sufficient tier + high anomaly → `review`; sufficient tier + high velocity → `step_up`.
- Every call writes exactly one `AuditLog` row.
- **Negative:** no threshold or action→tier value is hardcoded; mutating `RISK_POLICIES.yaml` changes behavior with no code change.

## 3. Tiers & progression

- New user climbs 0→1 on passkey enroll; `tier_changed` emitted with correct `from/to`.
- Identity verification is unreachable until a `STEP_UP` to T3 occurs (A5).
- Granting an admin role does not raise tier; the user must clear T4 independently.

## 4. Returning user & linking

- Single `/start` entry decides known vs unknown; user never self-classifies.
- Known email + new device → routed to recovery, not a failed login.
- Account link succeeds on verified-email match; **unverified-email merge is rejected** (A6).
- Conflicting profile data on merge is preserved and flagged, never overwritten.

## 5. B2B invite & domain join

- Invite carries org_id, role, expiry; invitee joins at the set role.
- Verified-domain auto-join request follows policy (auto or admin-approved).
- **Billing fires on accepted join, not on invite sent** (A7).
- SCIM-provisioned roles are authoritative; manual edits disabled when SCIM on.

## 6. Identity / KYC

- mDL/VC path requested first; doc+liveness only as fallback.
- IDV webhook verifies signature and rejects replays (A10).
- Sanctions screening is continuous (re-screen job runs and updates status).
- Raw ID images/selfies are not stored in-app (vendor ref only).

## 7. Billing

- $0 auth validates the payment method; 3DS/SCA invoked where required.
- Webhook signed + idempotent; subscription state syncs.
- PCI: no PAN stored; only token + last4.

## 8. Events & metrics

- Every event in `EVENTS.yaml` fires at its named point with exact properties.
- Each North Star metric is computable from emitted events alone.
- **`dead_end` count is zero** across happy-path and every fallback (A8).
- No secret or raw PII appears in any event property (scan gate).

## 9. Data governance

- Every PII column in the schema has a `DATA_GOVERNANCE.yaml` entry (A9, CI-enforced).
- Right-to-delete removes user PII and cascades to caches; regulated fields are retained per their schedule and excluded from user-initiated deletion with a logged reason.

## 10. Regulated overlays (only if enabled under signoff)

- Overlays are behind feature flags and default OFF, tagged `REQUIRES_COMPLIANCE_SIGNOFF`.
- HIPAA: every PHI access emits `phi_accessed`; no PHI processor lacks a BAA flag.
- COPPA: under-threshold age signal blocks all PII collection until parental consent recorded.
- CIP: covered activity cannot open an account before CIP completes.

---

## Tabletop (A4) — run these three end-to-end

1. **Move money** (T3): user at T1 attempts `move_money` → `risk.evaluate` returns `step_up` to T3 → `/verify-identity` → on pass, `tier_changed 1→3`, `identity_verification result=passed`, action proceeds.
2. **Admin invite** (T4): owner grants `role.grant_admin` → `step_up` to T4 → device-bound passkey challenge → on pass, grant succeeds, `AuditLog` written.
3. **Authorize agent** (T4, gated): `authorize_agent` is refused while the Stage 08 launch flag is OFF, with reason `agent_layer_not_launched` — confirming the door stays closed.

Each must route to the correct gate and emit the expected events. A tabletop failure blocks release.

---

## CI gates (must be green to merge)

- `no-passwords`: grep for password/bcrypt/argon in auth paths → fail if present.
- `no-sms-highrisk`: SMS adapter not referenced in Tier 3–4 recovery → fail if present.
- `policy-externalized`: no numeric thresholds or action→tier literals in `lib/risk/**`.
- `pii-registered`: every PII column has a governance entry.
- `events-complete`: every metric resolves to emitted events.
- `webhooks-signed`: all webhook handlers verify signature + idempotency.
