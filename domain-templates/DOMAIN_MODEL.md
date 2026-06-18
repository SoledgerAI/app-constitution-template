# DOMAIN_MODEL.md — TEMPLATE

> **How to use.** Copy this file into your app's `/domain` folder and fill every
> `<...>` and every checklist. The *structure and rigor* port across apps; the
> *content* does not — and content is yours to author, because inventing domain
> invariants is more dangerous than inventing login screens (the errors are
> silent and business-shaped, not loud and security-shaped). An agent may
> scaffold from a completed copy of this file; it must not author the invariants.
>
> See `examples/reconciliation-ledger/DOMAIN_MODEL.md` for a filled-in instance.

---

## 0. Scope & non-scope

- **This domain owns:** `<the product's core entities and rules>`
- **This domain does NOT own:** identity, tier, org/tenant, role, entitlements, billing, auth — those live in onboarding and are *read* across the seam (`SEAM_CONTRACT.md`). The domain never re-implements them.

---

## 1. Ubiquitous language (glossary)

Every term used in code, UI, and these docs means exactly one thing. Resolve synonyms here before modeling.

| Term | Definition | Not to be confused with |
|---|---|---|
| `<Term>` | `<one-sentence precise definition>` | `<the near-synonym you are NOT using>` |

---

## 2. Entities

For **each** entity, complete the block. An entity with no invariants is a red flag — revisit.

### `<EntityName>`
- **Definition:** `<what it represents in the real world>`
- **Identity / key:** `<the field(s) that make it unique; natural vs surrogate>`
- **Aggregate:** `<which aggregate root owns it; or "root">`
- **Tenancy:** carries `org_id` — `<yes/no; must be yes for any tenant-scoped entity>`
- **Attributes:**

  | Attribute | Type | Required | Governed?* | Notes |
  |---|---|---|---|---|
  | `<name>` | `<type>` | `<y/n>` | `<y/n>` | `<constraint / default>` |

  *Governed = holds personal data → must have a `DATA_GOVERNANCE.yaml` entry in `/app`.
- **Relationships:** `<to which entities, cardinality, ownership direction>`
- **Lifecycle:** state machine in `STATE_MACHINES.yaml` → `<entity key>` (`<yes/no — does it have states?>`)
- **Mutability:** `<mutable | append-only | immutable-after-<event>>`

*(repeat per entity)*

---

## 3. Aggregates & consistency boundaries

| Aggregate root | Contains | Transactional boundary | Cross-aggregate refs by |
|---|---|---|---|
| `<root>` | `<entities>` | `<what must commit atomically together>` | `<id only — never object>` |

Rule of thumb: an invariant that must always hold sits *inside* one aggregate's transaction; an invariant that may be briefly stale crosses aggregates and is reconciled by an event.

---

## 4. Invariant checklist (the rigor)

For **every** category, write the invariant or explicitly mark `N/A — <why>`. A blank is not allowed. Each invariant gets an `id` and is enforced in `DOMAIN_RULES.yaml`.

- [ ] **Identity** — what makes each entity unique; no duplicates possible. → `<INV-...>`
- [ ] **Conservation** — what totals/counts must always balance (nothing lost or created). → `<INV-...>`
- [ ] **Lifecycle** — which state transitions are legal; which are forbidden. → `STATE_MACHINES.yaml`
- [ ] **Authority** — which actions require which onboarding permission/tier. → `SEAM_CONTRACT.md` + `DOMAIN_RULES.yaml authority_map`
- [ ] **Temporal** — ordering, periods, effective dates, what "now" means. → `<INV-...>`
- [ ] **Idempotency** — which operations must be safe to repeat (re-ingest, retry, webhook). → `<INV-...>`
- [ ] **Tenancy** — every entity scoped to `org_id`; no cross-tenant reference. → `<INV-...>`
- [ ] **Auditability** — what must be recorded, immutable, and reconstructable. → `<INV-...>`
- [ ] **Monetary / unit integrity** — currency, rounding, minor-unit storage, double-entry if financial. → `<INV-... or N/A>`

---

## 5. The seam (onboarding ↔ domain)

This domain depends on onboarding; onboarding never depends on this domain. The full contract is in `SEAM_CONTRACT.md`. Summarize the dependency here:

- **Reads from onboarding:** `<actor, org_id, tier, aal, role, entitlements>`
- **Domain actions gated by the seam:** `<list the sensitive actions and the tier/permission each needs>`
- **New permissions this domain registers** (namespaced, appended to `/app/RBAC.yaml`): `<domain.*>`

---

## 6. Decisions & open questions

| # | Question | Decision | Date | Owner |
|---|---|---|---|---|
| 1 | `<modeling decision that wasn't obvious>` | `<what was chosen and why>` | | |
