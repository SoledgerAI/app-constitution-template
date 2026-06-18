# Apps

This folder contains real application packages created from this constitution.

Do not create generated implementation code directly in this folder until the app-specific package is complete and validated.

Each real application should follow this structure:

```txt
apps/<app-name>/
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
  generated/
```

## Rule

No app begins with code.

A real app begins with its onboarding policy instances, domain package, test plan, and implementation plan.

Generated code belongs under:

```txt
apps/<app-name>/generated/
```

only after the package is complete and constitution checks pass.
