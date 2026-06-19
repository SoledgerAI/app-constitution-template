# CODEX.md

Operating instructions for **Codex** in this repository.

The shared agent rules — prime directive, required reading order, required build
sequence, required implementation sequence, validation/readiness checklist, stop
conditions, non-negotiable rules, agent behavior (including the refactoring rule),
and the final rule — live in one place:

> **[`agent/BUILD_HANDOFF.md`](BUILD_HANDOFF.md) — the single source of truth.**

Read it first and follow it exactly. Nothing in this file overrides it.

---

## Codex specifics

- Codex may assist with implementation planning, code generation, test
  generation, refactoring, and validation — **only after** the app-specific
  package is complete and aligned with the constitution
  (see `BUILD_HANDOFF.md` → *Prime Directive*).
- When acting on this repo, Codex follows the constitution, `REPO_MAP.md`,
  `BUILD_HANDOFF.md`, the CI checks in `ci/`, and the app-specific domain package.
