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

**Structural conformance.** Parsing is necessary but not sufficient. The four core
domain artifacts are additionally validated against a JSON Schema in `ci/schemas/`:

```txt
INVARIANTS.yaml      ci/schemas/invariants.schema.json
DOMAIN_RULES.yaml    ci/schemas/domain_rules.schema.json
STATE_MACHINES.yaml  ci/schemas/state_machines.schema.json
EVENT_MODEL.yaml     ci/schemas/event_model.schema.json
```

The schemas check **shape, not value semantics**, so template placeholders like
`<INV-1>` and a string `min_tier: "<0-4>"` still conform — each schema governs both
the real artifact and its `_TEMPLATE.yaml` twin. They exist to make *malformed-but-
parseable* YAML fail loudly instead of passing vacuously: `invariants` as a list
where a map is required (or vice-versa), a transition missing its `to:` target
(which the validator's own logic never reads), or a mis-nested `authority_map` /
`data_fields` block that would otherwise resolve to an empty set and sail through
the seam or governance check. A schema violation is an ERROR (`[SCHEMA]`).

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
- **Direction (principle #5).** The domain may read onboarding context, but onboarding must never depend on the domain. Any `onboarding/*.yaml` whose data references a domain **entity name**, **invariant id** (`INV-*`), or **state-machine state name** is an ERROR. The domain vocabulary is derived from `DOMAIN_MODEL.md`, `INVARIANTS.yaml`, and `STATE_MACHINES.yaml` — nothing is hardcoded — and only parsed data is scanned, so comments mentioning the domain in prose are not flagged. **Exception (events):** in `onboarding/EVENTS.yaml`, the names declared under that file's own `events:` and `triggers:` maps are exempt from the match — onboarding owns its event vocabulary, and event names like `exception_resolved`/`period_closed` legitimately collide with domain state names. Only those declaration keys are exempt; their **values** (payload schemas, causes) are still scanned, so a domain entity referenced inside an event payload is still caught. **Exception (governance):** `onboarding/DATA_GOVERNANCE.yaml` is exempt from the direction scan **as a whole**. State the tradeoff plainly: this means principle #5 is **not machine-enforced for that one file** — onboarding *could* reference domain internals inside `DATA_GOVERNANCE.yaml` and the gate would not catch it. The justification is that the governance coverage check (§7) *requires* that file to name domain data by design — every entry is keyed by the governed `Entity.attribute` / `Entity` and justified in prose that necessarily names the domain — and its content is inert data-policy configuration, not executable onboarding logic that could create a runtime dependency on the domain. This is a **deliberate, narrower-than-ideal** tradeoff: unlike the surgical keys-only exemption used for `EVENTS.yaml` (where declared names are exempt but their values are still scanned), the whole file is skipped, because the governance notes legitimately describe domain behavior in prose and a keys-only carve-out would still false-positive. The blast radius is bounded by filename — every *other* `onboarding/*.yaml` is still fully scanned — and `tests/run_validator_tests.py` pins both that the exemption works for `DATA_GOVERNANCE.yaml` and that it does **not** leak to any other onboarding file. (A flat worked example keeps governance beside the domain, not under `onboarding/`, so this only matters for app instances.)

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

Thresholds, limits, roles, tiers, risk settings, entitlements, and event definitions must be externalized into YAML configuration. They must not be hardcoded in generated code.

The **automated** source-scan below covers numeric policy thresholds from the `policies:` block specifically (values `>= 10`); the broader items in the list above — tiers, entitlements, event definitions — are enforced structurally elsewhere (seam tier-alignment in §6, the event model in §5), not by source-scanning, so this section's scan does not promise to catch them in code.

Generated application code lives in:

```txt
apps/<app>/src/      # one source tree per app instance
```

Enforcement (`ci/constitution_validate.py`): for each app instance, if `apps/<app>/src/` exists, the validator scans its source files (`.py`, `.ts`, `.go`, `.java`, …) for literals equal to a numeric value declared under `policies:` in `DOMAIN_RULES.yaml` (e.g. `materiality_minor`, `auto_post_limit_minor`). A match means the value was hardcoded instead of read from config — ERROR.

- Only distinctive numeric thresholds are scanned (values with `|value| >= 10`); ubiquitous literals like `0`, `1`, `3` and string values like a currency code are skipped to avoid false positives. Matching is boundary-precise, so `10000` does not match inside `10000000`.
- **This check is dormant until generated code exists.** When an app instance has no `apps/<app>/src/` directory yet, the validator emits an informational **NOTE** (not a pass and not a failure) so its silence is never mistaken for a clean result. It activates automatically once the code tree appears.
- Flat worked examples ship no generated code, so the check does not apply to them.

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
