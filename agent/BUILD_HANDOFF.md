# BUILD_HANDOFF.md

## Purpose

This repository is an AI-native **application constitution and software factory**.
It is used to create governed, domain-driven applications. No application begins
with code. This file instructs any AI coding agent (Claude Code, Codex, or similar)
how to use the repository correctly.

It corrects three gaps present in earlier drafts: (1) the **onboarding** horizontal
is now placed explicitly, (2) the **seam contract** is a required input, and (3) the
**test plan and implementation plan** are reconciled with the required package.

---

# Prime Directive

**Do not generate application code until the application-specific package is complete
and aligned with the constitution.**

A complete application package =

```txt
apps/<app>/
  onboarding/                  # thin config instances (cloned from /policies templates)
    RISK_POLICIES.yaml
    RBAC.yaml
    DATA_GOVERNANCE.yaml
    EVENTS.yaml
  domain/                      # authored by humans — the truth of the app
    DOMAIN_MODEL.md
    INVARIANTS.yaml
    DOMAIN_RULES.yaml          # includes the authority_map = the per-app seam binding
    STATE_MACHINES.yaml
    EVENT_MODEL.yaml
    OBSERVABILITY.md
  TEST_PLAN.md                 # expectations derived from domain + onboarding
  IMPLEMENTATION_PLAN.md       # produced by the agent at step 9, before code
```

It must align with the shared inputs in `constitution/` — `CONSTITUTION.md`,
`onboarding/SEAM_CONTRACT.md`, and the onboarding architecture/spec.

If any required file is missing, incomplete, contradictory, or unclear: **stop and
ask.** Do not invent domain logic.

---

# Repository Layers

## Layer 1 — Constitution (built once, reused)

```txt
constitution/        # CONSTITUTION.md + onboarding/ (architecture, spec, SEAM_CONTRACT, test plan)
policies/            # reusable onboarding policy TEMPLATES (risk, rbac, governance, events)
domain-templates/    # blank/instructional domain templates (…_TEMPLATE.yaml / _TEMPLATE.md)
agent/               # this handoff + agent operating rules
ci/                  # validation + quality gates
examples/            # worked, filled-in examples (never mixed with templates)
```

## Layer 2 — App-specific package

```txt
apps/<app>/          # onboarding/ (instances) + domain/ (authored) + TEST_PLAN + IMPLEMENTATION_PLAN
```

This package defines the truth of the application.

## Layer 3 — Generated implementation

```txt
apps/<app>/generated/   # database, services, api, ui, tests, observability, deployment
```

Only after Layer 2 is complete and checks pass may code generation begin.

---

# Required Build Sequence (do not skip or reorder)

The canonical, fourteen-step build sequence lives in
[`APP_BUILD_PROCESS.md`](../APP_BUILD_PROCESS.md) — *Define the app* (step 1),
*Clone onboarding policy templates* (step 2), through *Deploy* (step 14). Follow
it exactly; do not restate or reorder it here.

---

# Stop Conditions

Stop immediately and ask if any are true:

1. A business rule is unclear.
2. An invariant is missing or ambiguous.
3. A permission or role is undefined **in RBAC.yaml or the domain authority_map**.
4. A risk policy is missing.
5. An event is referenced but not defined in `EVENTS.yaml` or `EVENT_MODEL.yaml`.
6. A lifecycle transition is unclear.
7. A state machine conflicts with a domain rule or an invariant.
8. A test expectation cannot be derived from the constitution or the app package.
9. The seam binding (`authority_map`) references a permission not present in `RBAC.yaml`.
10. The user asks to begin coding before the package is complete.
11. A required artifact is missing.

Do not guess.

---

# Non-Negotiable Rules

1. Do not start with code.
2. Do not invent business logic, invariants, or permissions.
3. Do not merge templates with worked examples.
4. Do not use duplicate filenames such as `(1)` or `2`.
5. Templates live in `domain-templates/` and `policies/`, suffixed `_TEMPLATE`.
6. Worked examples live in `examples/`.
7. App instances live in `apps/<app>/`.
8. Agent instructions live in `agent/`.
9. Constitution + onboarding live in `constitution/`.
10. CI and validation guidance live in `ci/`.
11. The domain depends on onboarding, never the reverse (the seam is one-way).
12. Thresholds, tiers, events, and RBAC are config — never hardcoded.

---

# Template vs Example vs Instance

| Kind | Location | Filename | Meaning |
|---|---|---|---|
| Template | `domain-templates/`, `policies/` | `INVARIANTS_TEMPLATE.yaml` | reusable blank / instructional |
| Worked example | `examples/reconciliation-ledger/` | `INVARIANTS.yaml` | a completed reference, not for production |
| App instance | `apps/<app>/domain/` | `INVARIANTS.yaml` | the real, app-specific truth |

These must never be mixed.

---

# Agent Behavior

When working in this repo the agent acts as principal software architect, staff
engineer, security architect, product architect, QA lead, and systems designer —
**responsible for preserving system integrity**, not merely generating code.

---

# Implementation Readiness Checklist

```txt
[ ] App purpose is clear
[ ] Onboarding policy instances cloned and tuned (risk, rbac, governance, events)
[ ] Domain model is complete
[ ] Invariants are defined, severity-ranked, each enforced AND observable
[ ] Domain rules are defined (including authority_map seam binding)
[ ] State machines are defined; forbidden transitions listed
[ ] Event model is defined; every emitted event exists
[ ] Observability defined: one metric per invariant
[ ] Seam consistency: every authority_map permission exists in RBAC.yaml
[ ] Test expectations are defined and derivable
[ ] Regulated overlays (HIPAA/CIP/COPPA) flagged and pending signoff if applicable
[ ] No unresolved business logic remains
```

If any item is unchecked, do not generate code.

---

# Final Instruction

When uncertain, stop and ask. Correctness before speed. Governance before
generation. Truth before code.
