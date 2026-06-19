# OBSERVABILITY.md — reconciliation ledger (worked example)

> Every invariant is watched in production. In steady state, every `critical`
> metric below should read **zero**. A non-zero reading is either a real
> violation or a broken enforcement point — both are incidents.

## Machine-readable coverage (authoritative)

The constitution gate parses the block below: one entry per invariant in
`INVARIANTS.yaml`, each declaring its `metric`, whether it `alert`s, and the
`threshold` that trips it. Every `critical` invariant must have `alert: true`.
The prose table and per-invariant detail that follow are the human-readable view
of the same facts.

```yaml
observability:
  INV-1: { metric: unassigned_entries,              alert: true,  threshold: "> 0 after run complete" }
  INV-2: { metric: out_of_tolerance_matches,        alert: true,  threshold: "> 0" }
  INV-3: { metric: unbalanced_adjustment_attempts,  alert: true,  threshold: "> 0 posted unbalanced" }
  INV-4: { metric: immutability_violation_attempts, alert: true,  threshold: "> 0" }
  INV-5: { metric: duplicate_ingest_rate,           alert: false, threshold: "> 1% of ingests" }
  INV-6: { metric: material_open_exceptions_at_close, alert: true, threshold: "> 0 at close attempt" }
  INV-7: { metric: frozen_write_attempts,           alert: true,  threshold: "> 0" }
  INV-8: { metric: cross_tenant_access_attempts,    alert: true,  threshold: "> 0" }
  INV-9: { metric: out_of_period_entries,           alert: false, threshold: "> 0" }
```

## Summary table

| Invariant | Metric | Threshold | Alert | Dashboard | Escalation |
|---|---|---|---|---|---|
| INV-1 | `unassigned_entries` | `> 0` after run complete | Critical | Reconciliation Health | On-call eng → Controller |
| INV-2 | `out_of_tolerance_matches` | `> 0` | Critical | Reconciliation Health | On-call eng → Controller |
| INV-3 | `unbalanced_adjustment_attempts` | `> 0` | Critical | Ledger Integrity | On-call eng → Controller |
| INV-4 | `immutability_violation_attempts` | `> 0` | Critical (security) | Ledger Integrity | On-call eng → Security + Controller |
| INV-5 | `duplicate_ingest_rate` | `> 1% of ingests` | High | Ingest Health | On-call eng |
| INV-6 | `material_open_exceptions_at_close` | `> 0` at close attempt | Critical | Close Readiness | Recon owner → Controller |
| INV-7 | `frozen_write_attempts` | `> 0` | Critical | Ledger Integrity | On-call eng → Controller |
| INV-8 | `cross_tenant_access_attempts` | `> 0` | Critical (security) | Tenant Isolation | Security on-call |
| INV-9 | `out_of_period_entries` | `> 0` | High | Reconciliation Health | Recon owner |

---

## Per-invariant detail

### INV-1 — every entry matched or excepted
- **Metric:** `unassigned_entries`
- **Definition:** `count(period entries where state not in [matched, exception_open, exception_resolved, written_off, carried_forward])` measured after a run reaches `matching` complete.
- **Threshold:** `> 0`
- **Alert:** Critical → eng on-call channel
- **Dashboard:** Reconciliation Health
- **Escalation:** On-call engineer; if not cleared in 30 min → Controller (close is blocked until zero).

### INV-3 — debits equal credits
- **Metric:** `unbalanced_adjustment_attempts`
- **Definition:** count of adjustment posts rejected for `sum(debit) != sum(credit)`. Posted adjustments are asserted balanced; any *posted* unbalanced row is a P1 code defect.
- **Threshold:** `> 0` posted unbalanced (P1); attempts trend is informational.
- **Alert:** Critical → Ledger Integrity
- **Escalation:** On-call engineer → Controller.

### INV-4 — posted records immutable
- **Metric:** `immutability_violation_attempts`
- **Definition:** count of UPDATE/DELETE attempts against rows where `state == posted` (caught at repository layer).
- **Threshold:** `> 0`
- **Alert:** Critical (security) → Ledger Integrity + Security
- **Escalation:** Security on-call (an attempt implies a code path that shouldn't exist).

### INV-6 — period cannot close dirty
- **Metric:** `material_open_exceptions_at_close`
- **Definition:** `count(exceptions where materiality == above and state not in [resolved, waived])` evaluated on a close request.
- **Threshold:** `> 0`
- **Alert:** Critical → Close Readiness
- **Escalation:** Reconciliation owner → Controller (close stays blocked by INV-6).

### INV-8 — tenant isolation
- **Metric:** `cross_tenant_access_attempts`
- **Definition:** count of queries or references where the resolved `org_id` differs from the actor's `org_id`.
- **Threshold:** `> 0`
- **Alert:** Critical (security) → Tenant Isolation
- **Escalation:** Security on-call immediately.

*(INV-2, INV-5, INV-7, INV-9 follow the same block structure; see the summary table for their metric, threshold, and owner.)*

---

## Operating rule

A `critical` breach halts the affected workflow (e.g., a failed INV-1 blocks the
run from advancing; a failed INV-6 blocks the close) and requires a human
decision before resuming. Wire each metric to the event that produces it in
`EVENT_MODEL.yaml` so the dashboard is event-sourced, not polled from guesses.
