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

Every invariant in:

```txt
apps/<app>/domain/INVARIANTS.yaml
```

must have at least one corresponding metric, log, audit event, or alert in:

```txt
apps/<app>/domain/OBSERVABILITY.md
```

Critical invariants must have alerting.

---

### 5. Event consistency

Every event referenced in state machines, domain rules, observability, tests, or implementation plans must be defined in an event file.

Valid event definition locations:

```txt
apps/<app>/onboarding/EVENTS.yaml
apps/<app>/domain/EVENT_MODEL.yaml
```

Undefined emitted events are not allowed.

---

### 6. Seam consistency

Every permission referenced in the domain authority map must exist in the app's RBAC file.

Authority map:

```txt
apps/<app>/domain/DOMAIN_RULES.yaml
```

RBAC file:

```txt
apps/<app>/onboarding/RBAC.yaml
```

The domain may read onboarding context, but onboarding must not depend on domain entities, rules, or state machines.

---

### 7. PII and data governance coverage

Every personal, sensitive, regulated, or tenant-scoped data field must have a data governance entry.

Governance source:

```txt
apps/<app>/onboarding/DATA_GOVERNANCE.yaml
```

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
