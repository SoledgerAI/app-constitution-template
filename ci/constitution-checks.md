# Constitution Checks

This file defines validation checks that should run before an application generated from this repository is considered implementation-ready.

These checks are not domain logic. They are quality gates that confirm the app-specific package aligns with the constitution, policy templates, domain templates, and agent handoff.

---

## Required checks

### 1. YAML validity

Every YAML file must parse successfully.

Applies to:

```txt
policies/*_TEMPLATE.yaml
domain-templates/*_TEMPLATE.yaml
examples/**/*.yaml
apps/*/onboarding/*.yaml
apps/*/domain/*.yaml
```

Failure means the package cannot proceed.

---

### 2. Template purity

Templates, worked examples, and app instances must not be mixed.

Rules:

```txt
Templates live in:
  policies/
  domain-templates/

Worked examples live in:
  examples/

App instances live in:
  apps/<app>/
```

Forbidden patterns:

```txt
(1)
copy
2
_TEMPLATE inside examples/
non-template app files inside domain-templates/
```

Failure means the repo must be cleaned before implementation continues.

---

### 3. Required app package completeness

Before code generation, every real app must include:

```txt
apps/<app>/
  onboarding/
    RISK_POLICIES.yaml
    RBAC.yaml
    DATA_GOVERNANCE.yaml
    EVENTS.yaml
  domain/
    DOMAIN_MODEL.md
    INVARIANTS.yaml
    DOMAIN_RULES.yaml
    STATE_MACHINES.yaml
    EVENT_MODEL.yaml
    OBSERVABILITY.md
  TEST_PLAN.md
  IMPLEMENTATION_PLAN.md
```

If any file is missing, stop.

---

### 4. Invariant observability

`OBSERVABILITY.md` must carry a **machine-readable** `observability:` block — a fenced YAML code block mapping every invariant id to its production signal. The gate parses this block; it does **not** substring-match prose (a sentence saying "INV-3 is *not* observable" must never satisfy the check).

```yaml
observability:
  INV-1: { metric: unassigned_entries, alert: true,  threshold: "> 0 after run complete" }
  INV-5: { metric: duplicate_ingest_rate, alert: false, threshold: "> 1% of ingests" }
  # ... one entry per invariant ...
```

Each entry requires:

- `metric` — the production signal that measures the invariant (required, non-empty).
- `alert` — boolean `true`/`false`: does a breach page someone, or is it dashboard/trend only.
- `threshold` — the value that means the invariant is at risk or broken (required; quote it so YAML doesn't choke on `>`/`%`).

Enforcement (`ci/constitution_validate.py`), all ERRORs:

- An invariant in `INVARIANTS.yaml` (location: `apps/<app>/domain/INVARIANTS.yaml`) with no entry in the `observability:` block.
- An entry missing `metric`/`threshold`, or whose `alert` is not a boolean.
- A `severity: critical` invariant whose entry is not `alert: true` — **critical invariants must alert.**
- No `observability:` block present at all.

The location is `apps/<app>/domain/OBSERVABILITY.md` (or `examples/<example>/OBSERVABILITY.md` for flat worked examples).

---

### 5. Event consistency

Triggers and events are **separate namespaces**. A state-machine transition's `event:` is the *trigger* — the command or cause that fires the transition; its `emits:` is the *event* — the fact published as a result, which may legitimately be `null` (most lifecycle steps change state without publishing anything). The two are declared in two different blocks of the event model and are checked independently.

Two hard rules are enforced (`ci/constitution_validate.py`):

- **Emitted events must be defined.** Every non-null `emits:` value in `STATE_MACHINES.yaml` transitions must appear in `EVENT_MODEL.yaml` `events:`.
- **Triggers must be declared.** Every transition `event:` (trigger) must appear in `EVENT_MODEL.yaml` `triggers:`. A trigger that emits `null` is valid and is **not** required to have a matching `events:` entry — only a `triggers:` declaration.

Definition locations:

```txt
apps/<app>/domain/EVENT_MODEL.yaml      # events: (facts) and triggers: (causes)
apps/<app>/onboarding/EVENTS.yaml       # may also contribute events:/triggers:
examples/<example>/EVENT_MODEL.yaml     # flat worked examples
```

Undefined emitted events and undeclared triggers are both ERRORs.

---

### 6. Seam consistency

Every permission referenced in the domain authority map must exist in the app's RBAC file.

Authority map:

```txt
apps/<app>/domain/DOMAIN_RULES.yaml
```

RBAC file — its location depends on the package shape:

```txt
apps/<app>/onboarding/RBAC.yaml          # full app instances (the seam owns RBAC)
examples/<example>/RBAC.yaml             # flat worked examples (beside the domain artifacts)
```

Three things are enforced (`ci/constitution_validate.py`):

- **Permission coverage.** Every permission named in the domain `authority_map` must appear among the `permissions:` keys of the RBAC file. Missing = ERROR. (A flat example has no `onboarding/` directory, so the validator resolves its RBAC beside the domain artifacts.)
- **Tier alignment.** Where an `authority_map` entry sets `min_tier` and RBAC declares a tier for the same permission, the two must agree. A mismatch means the gate would enforce a tier the domain never intended — ERROR.
- **Direction (principle #5).** The domain may read onboarding context, but onboarding must never depend on the domain. Any `onboarding/*.yaml` whose data references a domain **entity name**, **invariant id** (`INV-*`), or **state-machine state name** is an ERROR. The domain vocabulary is derived from `DOMAIN_MODEL.md`, `INVARIANTS.yaml`, and `STATE_MACHINES.yaml` — nothing is hardcoded — and only parsed data is scanned, so comments mentioning the domain in prose are not flagged. **Exception:** in `onboarding/EVENTS.yaml`, the names declared under that file's own `events:` and `triggers:` maps are exempt from the match — onboarding owns its event vocabulary, and event names like `exception_resolved`/`period_closed` legitimately collide with domain state names. Only those declaration keys are exempt; their **values** (payload schemas, causes) are still scanned, so a domain entity referenced inside an event payload is still caught.

---

### 7. PII and data governance coverage

Every personal, sensitive, regulated, or tenant-scoped data field must have a data governance entry. This is a **coverage** check, not a presence check — a governance file that merely exists proves nothing.

**Declaration (low-friction, declare once).** In `DOMAIN_RULES.yaml`, add a `data_fields:` block naming the protected data:

```yaml
data_fields:
  sensitive_fields:                 # personal / sensitive / regulated, by Entity.attribute
    - field: Adjustment.approved_by
      classification: personal
  tenant_scoped_entities:           # OPTIONAL — see note below
    - LedgerEntry
    - Adjustment
```

> **Tenancy is derived, not declared.** The validator parses the entity universe from `DOMAIN_MODEL.md` (the `### <Entity>` headings under the Entities section, with their `Tenancy:` tags) and, when any invariant has `scope: all` (e.g. INV-8 "every entity carries org_id"), treats *every* modeled entity as tenant-scoped. So an entity added to `DOMAIN_MODEL.md` is caught even if nobody touched `tenant_scoped_entities`. The hand-list is folded in as an **additional check target** — list an entity there and it must still be governed — but it is never the source of truth, so it cannot go stale silently.

**Governance source.** Each declared item must be answered in the governance file:

```txt
apps/<app>/onboarding/DATA_GOVERNANCE.yaml      # full app instances
examples/<example>/DATA_GOVERNANCE.yaml         # flat worked examples
```

```yaml
fields:                             # one per declared sensitive_field
  Adjustment.approved_by:
    classification: personal
    purpose: "..."                  # required
    retention: "..."                # required
entities:                           # one per declared tenant_scoped_entity
  LedgerEntry:
    tenant_scope: org_id
    note: "Row-level org isolation; ..."   # required
```

Enforcement (`ci/constitution_validate.py`):

- A declared-sensitive field with **no matching `fields:` entry**, or an entry missing **classification / purpose / retention**, is an ERROR.
- A tenant-scoped (org_id-bearing) entity — **derived from `DOMAIN_MODEL.md`** (plus `scope: all`), not just the hand-list — with **no governance note** (`entities.<Entity>.note`, or an explicit `<Entity>.org_id` field entry) is an ERROR.

Missing governance coverage blocks implementation.

---

### 8. Policy externalization

Thresholds, limits, roles, tiers, risk settings, entitlements, and event definitions must be externalized into YAML configuration.

They must not be hardcoded in generated code.

---

### 9. No unresolved domain logic

The package may not proceed if any artifact contains unresolved placeholders such as:

```txt
TBD
TODO
UNKNOWN
ASK LATER
FILL IN
```

The agent must stop and ask for clarification.

---

## Final gate

Code generation may begin only when all checks pass.

If any check fails, the agent must stop and report the failed check instead of generating code.
