# app-constitution-template

An AI-native application constitution and software factory template for building governed, domain-driven software before code generation begins.

Most AI-generated applications start with a prompt and rush into code.

This repo starts with the operating truth of the application:

```txt
constitution
domain model
invariants
domain rules
state machines
event model
observability
test plan
implementation plan
code
```

The purpose is simple:

> Prevent AI coding agents from inventing business logic, permissions, state transitions, financial rules, risk policies, or domain truth.

---

## Why this exists

AI coding tools are powerful, but they can create brittle systems when the domain is unclear.

This template forces the important questions before implementation:

* What is true?
* What must never be false?
* Who has authority?
* What states are legal?
* What events matter?
* What must be observable?
* What must be tested?
* What should the agent stop and ask?

The goal is not slower software.

The goal is safer, clearer, more repeatable software generation.

---

## Core principle

No app begins with code.

Every app begins with:

```txt
truth
state
authority
events
observability
tests
```

Code generation happens only after the application package is complete.

---

## Repository structure

```txt
app-constitution-template/

  constitution/          # governing principles and reusable onboarding architecture
  policies/              # reusable policy templates
  domain-templates/      # blank domain package templates
  examples/              # worked examples
  agent/                 # Claude/Codex/agent operating instructions
  ci/                    # constitution validation checks
  apps/                  # future real app packages

  APP_BUILD_PROCESS.md
  REPO_MAP.md
  README.md
```

---

## Build sequence

The numbered build sequence is maintained in one place — see
[`APP_BUILD_PROCESS.md`](APP_BUILD_PROCESS.md) for the canonical, fourteen-step
order (from *Define the app* through *Deploy*).

If a business rule, invariant, permission, risk policy, event, or lifecycle transition is unclear, the agent must stop and ask.

---

## Template vs example vs app instance

| Type           | Location                         | Purpose                            |
| -------------- | -------------------------------- | ---------------------------------- |
| Template       | `domain-templates/`, `policies/` | Reusable blank/instructional files |
| Worked example | `examples/`                      | Completed reference package        |
| App instance   | `apps/<app-name>/`               | Real application package           |

These must never be mixed.

---

## Agent rules

Agents must not invent:

```txt
business logic
permissions
risk policies
financial rules
state transitions
events
invariants
```

Agents may scaffold, validate, plan, generate, and test.

They do not originate domain truth.

---

## Current included example

This repo includes a worked reconciliation ledger example:

```txt
examples/reconciliation-ledger/
  DOMAIN_MODEL.md
  INVARIANTS.yaml
  DOMAIN_RULES.yaml
  STATE_MACHINES.yaml
  EVENT_MODEL.yaml
  OBSERVABILITY.md
```

The example is not production code.

It exists to show what a completed domain package looks like before implementation begins.

---

## Intended users

This template is for builders using AI coding agents such as Claude Code, Codex, or similar tools who want stronger control over:

```txt
domain-driven design
agentic code generation
governance
auditability
testability
state management
risk controls
implementation readiness
```

---

## Final rule

Governance before generation.

Truth before code.
