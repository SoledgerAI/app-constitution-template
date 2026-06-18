# App Build Process

This repository is the App Constitution template.

No application begins with code.

This file is the **single source of truth for the numbered build sequence**.
Any other document that needs the sequence references this file rather than
restating it, so the steps can never drift out of sync.

---

## Build sequence (canonical)

Every application must proceed in this order:

1. Define the app (purpose, domain boundary, which regulated overlays apply)
2. Clone onboarding policy templates → `apps/<app>/onboarding/` and tune them
3. Complete the domain model
4. Define invariants
5. Define domain rules (including the `authority_map` seam binding)
6. Define state machines
7. Define event model
8. Define observability (one metric per invariant)
9. Define the test plan
10. Generate the implementation plan
11. Generate code
12. Run tests
13. Review
14. Deploy

Step 2 is not optional: every app clones the reusable policy templates in
`policies/` into thin, app-specific config instances. This mirrors the layered
stack in `constitution/CONSTITUTION.md`, where architecture (the onboarding
horizontal) sits directly beneath the constitution and above the domain model.

## Rule

If a business rule, invariant, permission, risk policy, event, or lifecycle
transition is unclear, stop and ask.

Do not invent domain logic.
