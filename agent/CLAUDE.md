# CLAUDE.md

Operating instructions for **Claude Code** in this repository.

The shared agent rules — prime directive, required reading order, required build
sequence, required implementation sequence, validation/readiness checklist, stop
conditions, non-negotiable rules, agent behavior (including the refactoring rule),
and the final rule — live in one place:

> **[`agent/BUILD_HANDOFF.md`](BUILD_HANDOFF.md) — the single source of truth.**

Read it first and follow it exactly. Nothing in this file overrides it.

---

## Claude Code specifics

- Claude Code may assist with architecture review, artifact validation,
  implementation planning, test generation, and code generation — **only after**
  the app-specific package is complete and aligned with the constitution
  (see `BUILD_HANDOFF.md` → *Prime Directive*).
- When acting on this repo, Claude Code follows the constitution, `REPO_MAP.md`,
  `BUILD_HANDOFF.md`, and the CI checks in `ci/`.
