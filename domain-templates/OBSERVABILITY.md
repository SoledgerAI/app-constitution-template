# OBSERVABILITY.md — TEMPLATE

> Every invariant in `INVARIANTS.yaml` gets a row here. The point: **operations and
> engineering watch the same truth.** An invariant that can't be measured in
> production isn't enforced — it's assumed. Fill one block per invariant.

## Summary table

| Invariant | Metric | Threshold | Alert | Dashboard | Escalation |
|---|---|---|---|---|---|
| `<INV-1>` | `<metric_name>` | `<breach condition>` | `<critical/high/medium>` | `<dashboard>` | `<owner → next>` |

---

## Per-invariant detail

### `<INV-1>` — `<one-line statement>`
- **Metric:** `<metric_name>`
- **Definition:** `<exact query / how it's computed from events or state>`
- **Threshold:** `<the value that means the invariant is at risk or broken>`
- **Alert:** `<severity + channel>`
- **Dashboard:** `<where it's shown>`
- **Escalation:** `<who is paged, and who after them>`

*(repeat per invariant)*

---

## Operating rule

A `critical` invariant breach is a **stop-the-line** event: halt the affected
workflow, alert immediately, and require a human decision before resuming. A
`critical` metric that reads non-zero in steady state means either a real
violation or a broken enforcement point — both are incidents.
