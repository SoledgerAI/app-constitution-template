# OBSERVABILITY.md — access-grants (app instance: onboarding-demo)

> Every invariant is watched in production. In steady state, every `critical`
> metric below should read **zero**. A non-zero reading is either a real
> violation or a broken enforcement point — both are incidents.

## Machine-readable coverage (authoritative)

The constitution gate parses the block below: one entry per invariant in
`INVARIANTS.yaml`, each declaring its `metric`, whether it `alert`s, and the
`threshold` that trips it. Every `critical` invariant must have `alert: true`.
The prose table that follows is the human-readable view of the same facts.

```yaml
observability:
  INV-1: { metric: double_decided_requests,       alert: true,  threshold: "> 0 (a decided request changed)" }
  INV-2: { metric: invalid_grant_lifetimes,        alert: false, threshold: "> 0 grants minted with bad window" }
  INV-3: { metric: cross_tenant_access_attempts,   alert: true,  threshold: "> 0" }
```

## Summary table

| Invariant | Metric | Threshold | Alert | Dashboard | Escalation |
|---|---|---|---|---|---|
| INV-1 | `double_decided_requests` | `> 0` | Critical | Access Integrity | On-call eng → Security |
| INV-2 | `invalid_grant_lifetimes` | `> 0` | High | Access Health | On-call eng |
| INV-3 | `cross_tenant_access_attempts` | `> 0` | Critical (security) | Tenant Isolation | Security on-call |

---

## Per-invariant detail

### INV-1 — a request is decided exactly once
- **Metric:** `double_decided_requests`
- **Definition:** count of requests observed transitioning out of a terminal `approved`/`denied` state.
- **Threshold:** `> 0`
- **Alert:** Critical → Access Integrity
- **Escalation:** On-call engineer → Security (a terminal-state mutation implies a missing guard).

### INV-2 — grant lifetimes are positive and bounded
- **Metric:** `invalid_grant_lifetimes`
- **Definition:** count of grants minted where `expires_at <= granted_at` or the window exceeds `max_grant_ttl_hours`.
- **Threshold:** `> 0`
- **Alert:** High → Access Health (trend; not paging)
- **Escalation:** On-call engineer reviews next business day.

### INV-3 — tenant isolation
- **Metric:** `cross_tenant_access_attempts`
- **Definition:** count of queries or references where the resolved `org_id` differs from the actor's `org_id`.
- **Threshold:** `> 0`
- **Alert:** Critical (security) → Tenant Isolation
- **Escalation:** Security on-call immediately.

---

## Operating rule

A `critical` breach halts the affected workflow and requires a human decision
before resuming. Wire each metric to the event that produces it in
`EVENT_MODEL.yaml` so the dashboard is event-sourced, not polled from guesses.
