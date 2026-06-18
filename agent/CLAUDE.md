# CLAUDE.md

## Purpose

This file gives Claude Code operating instructions for using this repository.

Claude Code may assist with architecture review, artifact validation, implementation planning, test generation, and code generation only after the required application package is complete.

Claude Code must follow the constitution, repo map, build handoff, and CI checks.

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

No app begins with code.

Every app begins with:

```txt
purpose
domain model
invariants
domain rules
state machines
event model
observability
test plan
implementation plan
```

---

## Claude Code behavior

Claude Code must:

1. Preserve the constitution.
2. Keep templates, examples, and app instances separate.
3. Treat invariants as non-negotiable truth.
4. Treat policies as external YAML configuration.
5. Stop when domain logic is missing or ambiguous.
6. Never invent business rules, permissions, lifecycle transitions, risk policies, or invariants.
7. Generate implementation plans before generating code.
8. Generate tests from the domain package, not from assumptions.
9. Keep onboarding and domain separated by the seam contract.
10. Ensure every critical invariant is observable.

---

## Stop conditions

Stop and ask if any of the following are true:

```txt
A business rule is unclear.
An invariant is missing.
A permission is undefined.
A risk policy is missing.
An event is referenced but not defined.
A lifecycle transition is unclear.
A domain rule conflicts with a state machine.
An invariant is not observable.
A test expectation cannot be derived.
The user asks for code before the app package is complete.
```

---

## Required implementation sequence

When implementation is allowed, proceed in this order:

```txt
1. Validate app package completeness.
2. Validate YAML parsing.
3. Validate seam consistency.
4. Validate event consistency.
5. Validate invariant observability.
6. Produce IMPLEMENTATION_PLAN.md.
7. Generate database schema.
8. Generate domain services.
9. Generate API contracts.
10. Generate tests.
11. Generate UI only after API/domain contracts exist.
12. Run tests.
13. Report gaps.
14. Prepare deployment notes.
```

---

## Final rule

Correctness before speed.

Governance before generation.

Truth before code.
