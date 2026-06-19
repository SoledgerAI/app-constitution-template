# OBSERVABILITY.md — TEMPLATE

> Every invariant in `INVARIANTS.yaml` gets a row here. The point: **operations and
> engineering watch the same truth.** An invariant that can't be measured in
> production isn't enforced — it's assumed. Fill one block per invariant.

## Machine-readable coverage (authoritative)

The constitution gate parses the fenced block below — not the prose. Provide one
entry per invariant in `INVARIANTS.yaml`:

- `metric` — the production signal that measures it (required).
- `alert` — `true` if a breach pages someone, `false` if it's dashboard/trend only.
  **Every `severity: critical` invariant must be `alert: true`.**
- `threshold` — the value that means the invariant is at risk or broken (required;
  quote it so YAML doesn't choke on `>`/`%`).

```yaml
observability:
  "<INV-1>": { metric: "<metric_name>", alert: true,  threshold: "<breach condition>" }
  "<INV-2>": { metric: "<metric_name>", alert: false, threshold: "<breach condition>" }
  # ... one line per invariant ...
```

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
