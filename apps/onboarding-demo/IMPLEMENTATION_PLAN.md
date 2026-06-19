# IMPLEMENTATION_PLAN.md — access-grants (app instance: onboarding-demo)

No code is written until the constitution gate reports **GATE OPEN** for this
package. The order below is deliberate: configuration and enforcement points
come before behavior.

## Phase 0 — gate

- `python3 ci/constitution_validate.py --package onboarding-demo --strict` must
  report GATE OPEN. This plan does not begin until it does.

## Phase 1 — configuration surface

- Load `domain/DOMAIN_RULES.yaml` `policies:` (`max_grant_ttl_hours`,
  `grant_sweep_interval_seconds`) from config at startup. Nothing in `src/` hard-codes
  these values — the policy-externalization check scans for exactly that.
- Load `onboarding/RBAC.yaml` and `onboarding/RISK_POLICIES.yaml` into the
  shared seam checker; the domain never re-implements tier logic.

## Phase 2 — persistence and tenancy

- One table per entity (`access_request`, `grant`), each carrying `org_id`.
- Every query is org-scoped at the repository layer (INV-3); there is no code path
  that resolves a row without an `org_id` predicate.

## Phase 3 — state machines

- Implement `access_request` and `grant` transitions exactly as
  `domain/STATE_MACHINES.yaml` declares them, including the guards and the
  `forbidden_transitions`.
- The decision transition enforces INV-1 (terminal, single-decision).
- `grant_create` enforces INV-2 against `max_grant_ttl_hours`.

## Phase 4 — events and observability

- Publish the four domain events from `domain/EVENT_MODEL.yaml` at the transitions
  that declare them.
- Wire each invariant metric in `domain/OBSERVABILITY.md` to the event that feeds
  it, so the dashboards are event-sourced.

## Phase 5 — tests

- Implement every case in `TEST_PLAN.md`. The build stays red until they pass.

Generated code lands under `apps/onboarding-demo/src/` only after Phase 0 is green.
