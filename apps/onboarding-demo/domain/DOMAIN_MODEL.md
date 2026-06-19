# DOMAIN_MODEL.md — access-grants (app instance: onboarding-demo)

> A deliberately tiny but complete domain: an org member asks for access to a
> protected resource, an approver decides, and an approval mints a time-boxed
> Grant that later expires or is revoked. It is the smallest domain that still
> exercises every hardened constitution check — tenancy, PII governance, the
> seam, observability, and the event/trigger split — so it can serve as the
> reference app instance the validator runs against.

---

## 0. Scope & non-scope

- **This domain owns:** access requests, approval decisions, and the time-boxed
  grants that result.
- **This domain does NOT own:** who the user is, their tier/role, the org/tenant,
  authentication, or billing. Those are read across the seam from onboarding.

---

## 1. Ubiquitous language

| Term | Definition | Not to be confused with |
|---|---|---|
| Access request | A member's pending ask to use a protected resource | The RBAC permission itself |
| Decision | An approver's terminal approve/deny on a request | The downstream Grant |
| Grant | A time-boxed authorization minted when a request is approved | The request that produced it |
| Lifetime | The interval from a grant's start to its expiry | The approval timestamp |

---

## 2. Entities

### AccessRequest
- **Definition:** a member's pending ask to use a protected resource.
- **Identity:** `request_id` (surrogate); unique `(org_id, requested_by, resource)` while pending.
- **Aggregate:** root.
- **Tenancy:** `org_id` — yes.
- **Attributes:** `requested_by`(user_id, req), `resource`(string, req), `reason`(string), `state`(enum, req), `decided_by`(user_id|null), `decided_at`(timestamp|null).
- **Relationships:** an approved request produces exactly one Grant.
- **Mutability:** the decision is terminal — once approved or denied, the request is immutable.

### Grant
- **Definition:** a time-boxed authorization minted when a request is approved.
- **Identity:** `grant_id` (surrogate).
- **Aggregate:** root; references its originating request by id.
- **Tenancy:** `org_id` — yes.
- **Attributes:** `request_id`(fk, req), `approved_by`(user_id, req), `granted_at`(timestamp, req), `expires_at`(timestamp, req), `state`(enum, req).
- **Invariant tie:** `expires_at` strictly after `granted_at`, bounded by `max_grant_ttl_hours` (INV-2).
- **Mutability:** terminal once `expired` or `revoked`; never edited in place.

---

## 3. Aggregates & consistency boundaries

| Aggregate root | Contains | Transactional boundary | Cross-aggregate refs by |
|---|---|---|---|
| AccessRequest | its decision | request + decision commit together | request_id |
| Grant | its lifetime window | mint commits with its source request's approval | request_id |

---

## 4. Invariant checklist

- [x] **Decisiveness** — a request resolves to exactly one terminal outcome, approve or deny, never both → **INV-1**.
- [x] **Bounded lifetime** — a grant's `expires_at` is strictly after `granted_at` and within `max_grant_ttl_hours` → **INV-2**.
- [x] **Tenancy** — every entity carries `org_id`; no cross-org reference → **INV-3**.

---

## 5. The seam

- **Reads from onboarding:** `actor`, `org_id`, `tier`, `role`.
- **Domain actions gated by the seam:** submit a request (T1), approve or deny a request (T3), revoke a grant (T3).
- **New permissions registered** (declared in `onboarding/RBAC.yaml`): `access.request`, `access.approve`, `access.revoke`.

---

## 6. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Edit a decided request or re-decide it? | Never — the decision is terminal; raise a new request. |
| 2 | Extend a live grant's expiry? | No — revoke and mint a fresh grant; lifetime stays auditable. |
