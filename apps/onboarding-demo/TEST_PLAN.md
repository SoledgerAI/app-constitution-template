# TEST_PLAN.md — access-grants (app instance: onboarding-demo)

The test plan is organized by invariant. Every invariant in
`domain/INVARIANTS.yaml` has at least one test that proves it holds and at least
one that proves the enforcement point rejects a violation.

## INV-1 — a request is decided exactly once

- **Holds:** a `submitted` request transitions to `approved`, and a second
  approve/deny attempt on the same request is rejected at `request_decision`.
- **Violation rejected:** attempting `approved -> denied` (or `denied -> approved`)
  raises and leaves the original decision intact.
- **Observable:** `double_decided_requests` stays at zero across the suite.

## INV-2 — grant lifetimes are positive and bounded

- **Holds:** minting a grant with `expires_at = granted_at + 1h` succeeds; the
  emitted `access_granted` carries both timestamps.
- **Violation rejected:** `expires_at <= granted_at` is rejected at `grant_create`;
  `expires_at > granted_at + max_grant_ttl_hours` (72h) is rejected.
- **Boundary:** exactly `granted_at + 72h` is accepted; one second past is rejected.
- **Observable:** `invalid_grant_lifetimes` stays at zero.

## INV-3 — tenant isolation

- **Holds:** every repository query is org-scoped; reading another org's request
  returns nothing.
- **Violation rejected:** a forged cross-org `request_id` reference is rejected at
  the repository and increments `cross_tenant_access_attempts`.

## Seam tests

- `access.approve` is denied below Tier 3 and allowed at Tier 3 (matches
  `onboarding/RBAC.yaml`).
- `access.revoke` requires step-up re-auth even for a Tier-3 `security_admin`.

## State-machine tests

- All legal transitions in `domain/STATE_MACHINES.yaml` are exercised once.
- Every `forbidden_transitions` entry is asserted to raise.

## Event tests

- Each transition that declares an `emits:` publishes exactly that event with the
  schema from `domain/EVENT_MODEL.yaml`; transitions with `emits: null` publish
  nothing.
