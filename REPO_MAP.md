# REPO_MAP.md

One page. Where everything lives, what's reusable vs per-app, and how onboarding
and domain meet.

---

## The tree

```txt
repo/
├── REPO_MAP.md                      # this file
│
├── constitution/                    # ── LAYER 1: built once, reused ──
│   ├── CONSTITUTION.md              # the principles every app aligns with
│   └── onboarding/                  # the reusable acquisition→activation horizontal
│       ├── ONBOARDING_ARCHITECTURE.md
│       ├── IMPLEMENTATION_SPEC.md
│       ├── SEAM_CONTRACT.md         # the one-way domain↔onboarding membrane
│       └── TEST_PLAN.md             # onboarding test expectations (template)
│
├── policies/                        # reusable onboarding policy TEMPLATES
│   ├── RISK_POLICIES_TEMPLATE.yaml
│   ├── RBAC_TEMPLATE.yaml
│   ├── DATA_GOVERNANCE_TEMPLATE.yaml
│   └── EVENTS_TEMPLATE.yaml
│
├── domain-templates/                # blank/instructional domain templates
│   ├── DOMAIN_MODEL_TEMPLATE.md
│   ├── INVARIANTS_TEMPLATE.yaml
│   ├── DOMAIN_RULES_TEMPLATE.yaml
│   ├── STATE_MACHINES_TEMPLATE.yaml
│   ├── EVENT_MODEL_TEMPLATE.yaml
│   └── OBSERVABILITY_TEMPLATE.md
│
├── agent/                           # agent operating rules
│   └── BUILD_HANDOFF.md             # how an agent uses this repo
├── ci/                              # validation + quality gates (see below)
│
├── examples/                        # ── worked, filled-in references (NOT production) ──
│   └── reconciliation-ledger/
│       ├── DOMAIN_MODEL.md
│       ├── INVARIANTS.yaml
│       ├── DOMAIN_RULES.yaml
│       ├── STATE_MACHINES.yaml
│       ├── EVENT_MODEL.yaml
│       └── OBSERVABILITY.md
│
└── apps/                            # ── LAYER 2 + 3: real applications ──
    └── <app-name>/                  # e.g. snf-admissions-ai
        ├── onboarding/              # thin config INSTANCES (cloned from /policies)
        │   ├── RISK_POLICIES.yaml
        │   ├── RBAC.yaml
        │   ├── DATA_GOVERNANCE.yaml
        │   └── EVENTS.yaml
        ├── domain/                  # the app's AUTHORED truth
        │   ├── DOMAIN_MODEL.md
        │   ├── INVARIANTS.yaml
        │   ├── DOMAIN_RULES.yaml     # authority_map = the per-app seam binding
        │   ├── STATE_MACHINES.yaml
        │   ├── EVENT_MODEL.yaml
        │   └── OBSERVABILITY.md
        ├── TEST_PLAN.md
        ├── IMPLEMENTATION_PLAN.md    # agent-produced, before code
        └── generated/               # ── LAYER 3 ── db, services, api, ui, tests, deploy
```

---

## Reusable vs per-app

| Reusable (author once) | Per-app (author/clone each time) |
|---|---|
| `constitution/` (principles, onboarding architecture, spec, seam) | `apps/<app>/onboarding/*` — tuned policy instances |
| `policies/*_TEMPLATE.yaml` | `apps/<app>/domain/*` — the authored domain package |
| `domain-templates/*` | `apps/<app>/TEST_PLAN.md`, `IMPLEMENTATION_PLAN.md` |
| `examples/` (reference only) | `apps/<app>/generated/*` |

Onboarding is a **template you clone**. The domain is a **model you author**.

---

## How onboarding and domain meet (the seam)

```
   apps/<app>/onboarding/            apps/<app>/domain/
   ┌───────────────────┐            ┌───────────────────┐
   │ identity, tier,    │  reads →   │ entities, rules,   │
   │ role, entitlements │            │ invariants, state  │
   │ (the WHO/WHAT-CAN) │  ← never   │ (the PRODUCT)      │
   └───────────────────┘  depends   └───────────────────┘
```

- The domain **reads** the onboarding context (identity, tier, role, entitlements)
  and calls `requireTier()` / `hasPermission()`. It never re-implements auth.
- The per-app binding is the `authority_map` in `domain/DOMAIN_RULES.yaml`, which
  maps domain actions to permissions appended to `onboarding/RBAC.yaml`.
- Dependency is one-way. Onboarding must never import a domain type.

Full contract: `constitution/onboarding/SEAM_CONTRACT.md`.

---

## Minimum required app package (gate before code)

```txt
[ ] onboarding/RISK_POLICIES.yaml      [ ] domain/DOMAIN_MODEL.md
[ ] onboarding/RBAC.yaml               [ ] domain/INVARIANTS.yaml
[ ] onboarding/DATA_GOVERNANCE.yaml    [ ] domain/DOMAIN_RULES.yaml
[ ] onboarding/EVENTS.yaml             [ ] domain/STATE_MACHINES.yaml
[ ] TEST_PLAN.md                       [ ] domain/EVENT_MODEL.yaml
[ ] IMPLEMENTATION_PLAN.md (step 9)    [ ] domain/OBSERVABILITY.md
```

---

## CI / validation gates (`ci/`)

- **yaml-valid** — every YAML parses.
- **pii-registered** — every PII field has a `DATA_GOVERNANCE` entry.
- **events-defined** — every event emitted in state machines exists in an event file.
- **invariant-observable** — every `INVARIANTS.yaml` entry has a metric in `OBSERVABILITY.md`.
- **seam-consistent** — every `authority_map` permission exists in `RBAC.yaml`.
- **policy-externalized** — no thresholds/tiers hardcoded in generated code.
- **template-purity** — no template/example/instance mixing; no `(1)`/`2` filenames.

---

## Where today's work maps

What we've already built slots in directly:

- the `app/` set → `constitution/onboarding/` + `policies/` (templates) and, per app, `apps/<app>/onboarding/`.
- the `domain/` templates → `domain-templates/` (rename with `_TEMPLATE`).
- `domain/examples/reconciliation-ledger/` → `examples/reconciliation-ledger/` (already correct).

The only mechanical work to adopt this map is the `_TEMPLATE` rename pass and
moving the onboarding spec under `constitution/onboarding/`.
