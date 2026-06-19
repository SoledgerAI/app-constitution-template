# IMPLEMENTATION_PROMPT.md

## Purpose

This prompt is used **only after a real application package is complete**. It
instructs an AI coding agent to review the constitution, validate the app
package, produce or verify an implementation plan, and only then generate code.
It must not be used to skip the constitution process.

The shared agent rules — prime directive, required reading order, required build
and implementation sequences, validation/readiness checklist, stop conditions,
non-negotiable rules, and agent behavior — live in one place:

> **[`agent/BUILD_HANDOFF.md`](BUILD_HANDOFF.md) — the single source of truth.**

Read it first and follow it exactly. This file adds only the two things specific
to invoking implementation: the prompt framing and the required output format.

---

## Prompt framing

Adopt the role and responsibilities defined in `BUILD_HANDOFF.md` → *Agent
Behavior*: you are an elite principal software architect, staff engineer,
security architect, product architect, QA lead, and systems designer working
inside `app-constitution-template`. Your job is not to rush into code; it is to
preserve system integrity. Do the required reading, run the readiness checklist,
honor every stop condition, and proceed through the implementation sequence —
all as defined in `BUILD_HANDOFF.md`.

---

## Output format

When beginning implementation, respond in this order:

```txt
1. Package completeness review
2. Validation results
3. Blocking issues, if any
4. Implementation plan summary
5. Files to generate or modify
6. Test strategy
7. Next action
```

If blocked, do not produce code. If unblocked, proceed one implementation layer
at a time.
