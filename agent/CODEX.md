# CODEX.md

## Purpose

This file gives Codex operating instructions for using this repository.

Codex may assist with implementation planning, code generation, test generation, refactoring, and validation only after the required application package is complete.

Codex must follow the constitution, repo map, build handoff, CI checks, and app-specific domain package.

---

## Required reading order

Before generating or modifying implementation code, read these files in order:

```txt
REPO_MAP.md
APP_BUILD_PROCESS.md
constitution/CONSTITUTION.md
agent/BUILD_HANDOFF.md
ci/constitution-checks.md
constitution/onboarding/SEAM_CONTRACT.md
```

Then read the complete app-specific package:

```txt
apps/<app>/onboarding/
apps/<app>/domain/
apps/<app>/TEST_PLAN.md
apps/<app>/IMPLEMENTATION_PLAN.md
```

---

## Prime directive

Do not generate application code until the app-specific package is complete and aligned with the constitution.

Codex is not allowed to invent business logic.

Codex is not allowed to infer missing permissions, policies, lifecycle transitions, events, invariants, or financial rules.

When the truth is missing, stop and ask.

---

## Required package before code

Code generation may begin only after these files exist:

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

If any required file is missing, do not generate code.

---

## Codex behavior

Codex must:

1. Preserve the constitution.
2. Keep templates, examples, and app instances separate.
3. Treat invariants as non-negotiable truth.
4. Treat policies as runtime YAML configuration.
5. Generate code from the implementation plan, not from assumptions.
6. Generate tests from the domain package, not from guessed behavior.
7. Preserve tenant isolation.
8. Preserve auditability.
9. Preserve idempotency.
10. Preserve the onboarding/domain seam.
11. Reject hardcoded thresholds, tiers, roles, risk settings, or event names when they belong in YAML.
12. Report unresolved business logic instead of filling it in.

---

## Stop conditions

Stop and ask if any of the following are true:

```txt
A business rule is unclear.
An invariant is missing or ambiguous.
A permission is undefined.
A risk policy is missing.
An event is referenced but not defined.
A lifecycle transition is unclear.
A domain rule conflicts with a state machine.
An invariant is not observable.
A test expectation cannot be derived.
A policy value appears hardcoded.
A tenant-scoped query lacks org_id.
The user asks for code before the app package is complete.
```

---

## Implementation sequence

When implementation is allowed, proceed in this order:

```txt
1. Validate required package completeness.
2. Validate YAML parsing.
3. Validate template/example/instance purity.
4. Validate seam consistency.
5. Validate event consistency.
6. Validate invariant observability.
7. Review IMPLEMENTATION_PLAN.md.
8. Generate database schema.
9. Generate domain services.
10. Generate API contracts.
11. Generate tests.
12. Generate UI only after API/domain contracts exist.
13. Run tests.
14. Report failures and unresolved assumptions.
15. Prepare deployment notes.
```

---

## Refactoring rule

Codex may refactor generated code only if the refactor preserves:

```txt
domain behavior
invariants
state transitions
event emissions
RBAC checks
risk policy checks
data governance requirements
audit trails
tenant isolation
test expectations
```

A refactor that changes behavior requires a domain artifact update first.

---

## Final rule

Correctness before speed.

Governance before generation.

Truth before code.
