# DOMAIN_MODEL.md — reconciliation ledger (worked example)

> A filled-in instance of the template, modeling a multi-source reconciliation
> ledger: ingest records from two or more sources, match them, surface
> exceptions, resolve via balanced adjustments, and close a period only when it
> reconciles. Built around audit integrity — posted records are immutable.

---

## 0. Scope & non-scope

- **This domain owns:** sources, ledger entries, reconciliation runs, match sets, exceptions, adjustments (journal entries), and periods.
- **This domain does NOT own:** who the user is, their tier/role, the org/tenant, plan entitlements, or billing. Those are read across the seam.

---

## 1. Ubiquitous language

| Term | Definition | Not to be confused with |
|---|---|---|
| Source | A feed of records to be reconciled (bank, GL, sub-ledger, processor) | The customer's onboarding Account |
| Ledger entry | One normalized record from a Source, in signed minor units | A UI row |
| Run | One execution that matches entries for a period | The period itself |
| Match set | A group of entries that reconcile to zero within tolerance | A single pairing (a match set may be 1:n or n:m) |
| Exception | An entry left unmatched or out of tolerance | An application error |
| Adjustment | A balanced double-entry correction posting | Editing an entry (entries are immutable) |
| Period | The time window being reconciled and closed | A Run (a period may have several runs) |
| Residual | Signed sum of a match set; must be ~0 | The materiality threshold |

---

## 2. Entities

### Source
- **Definition:** an origin of records to reconcile.
- **Identity:** `source_id` (surrogate); unique `(org_id, name)`.
- **Aggregate:** root.
- **Tenancy:** `org_id` — yes.
- **Attributes:** `name`(string,req), `kind`(enum: bank|gl|subledger|processor,req), `currency`(ISO-4217,req), `active`(bool).
- **Relationships:** has many LedgerEntry.
- **Mutability:** mutable (config), but `currency` is locked once entries exist.

### LedgerEntry
- **Definition:** one normalized record from a Source.
- **Identity:** `entry_id` (surrogate); idempotency key `(source_id, external_ref)` unique.
- **Aggregate:** belongs to Source; referenced by MatchSet/Exception by id.
- **Tenancy:** `org_id` — yes.
- **Attributes:** `external_ref`(string,req), `source_id`(fk,req), `period_id`(fk,req), `amount_minor`(int signed,req), `currency`(req), `value_date`(date,req), `description`(string), `state`(enum,req).
- **Relationships:** in at most one MatchSet OR one Exception (see I1).
- **Mutability:** **immutable after `posted`/normalized**; corrections are new entries or adjustments.

### ReconciliationRun
- **Identity:** `run_id`. **Tenancy:** yes. **Aggregate:** root.
- **Attributes:** `period_id`(fk), `matching_profile`(ref to DOMAIN_RULES), `state`(enum), `started_at`, `completed_at`.
- **Relationships:** produces many MatchSet and Exception.

### MatchSet
- **Identity:** `match_id`. **Tenancy:** yes.
- **Attributes:** `run_id`(fk), `entry_ids`(int[],req,≥2), `match_type`(enum: 1:1|1:n|n:m), `residual_minor`(int), `state`(enum).
- **Invariant tie:** `residual_minor` within tolerance (I2).
- **Mutability:** dissolved only on run reopen; never edited in place.

### Exception
- **Identity:** `exception_id`. **Tenancy:** yes.
- **Attributes:** `entry_ids`(int[],req,≥1), `reason`(enum: unmatched|out_of_tolerance|duplicate|fx_gap), `materiality`(enum: below|above), `state`(enum), `resolution_ref`(adj_id|waiver_id|null).

### Adjustment (journal entry)
- **Identity:** `adj_id`. **Tenancy:** yes.
- **Attributes:** `lines`(array of {account, debit_minor, credit_minor}, req, ≥2), `period_id`(fk), `state`(enum), `approved_by`(user_id|null), `reverses_adj_id`(fk|null).
- **Invariant tie:** Σdebits = Σcredits (I3); immutable once `posted` (I4).

### Period
- **Identity:** `period_id`. **Tenancy:** yes.
- **Attributes:** `range_start`(date), `range_end`(date), `state`(enum), `closed_by`(user_id|null), `closed_at`.

---

## 3. Aggregates & consistency boundaries

| Aggregate root | Contains | Transactional boundary | Cross-aggregate refs by |
|---|---|---|---|
| Source | its LedgerEntries | ingest of one entry is atomic | id |
| ReconciliationRun | its MatchSets, Exceptions | a run's match results commit together | entry_id, period_id |
| Period | close decision | close + freeze commit together | run_id |
| Adjustment | its lines | all lines post atomically (balance) | account, period_id |

---

## 4. Invariant checklist

- [x] **Identity** — `(source_id, external_ref)` is unique per entry → **INV-5** (also gives idempotency).
- [x] **Conservation** — at run completion, every period entry is in exactly one MatchSet **or** exactly one Exception; `count(matched)+count(exception)=count(entries)` → **INV-1**.
- [x] **Lifecycle** — legal transitions only → `STATE_MACHINES.yaml`.
- [x] **Authority** — post-above-threshold, close, reopen, waive are gated via seam → `DOMAIN_RULES.authority_map`.
- [x] **Temporal** — an entry's `value_date` falls in its Period range unless `carried_forward` with a link to the origin period → **INV-9**.
- [x] **Idempotency** — re-ingesting the same `(source_id, external_ref)` is a no-op → **INV-5**.
- [x] **Tenancy** — every entity carries `org_id`; no cross-org reference → **INV-8**.
- [x] **Auditability** — posted entries/adjustments are immutable; corrections are new postings; closed periods freeze → **INV-4, INV-7**.
- [x] **Monetary / unit integrity** — amounts in signed minor units; single currency per match (FX gaps become exceptions); every adjustment balances (double-entry) → **INV-3**.

---

## 5. The seam

- **Reads from onboarding:** `actor`, `org_id`, `tier`, `aal`, `role`, `entitlements` (e.g. `feature.multi_source`, `feature.auto_post_limit`).
- **Domain actions gated by the seam:** post large adjustment (T4), close period (T3), reopen period (T4), waive exception (T3).
- **New permissions registered** (appended to `/app/RBAC.yaml`): `recon.run`, `recon.match`, `recon.post_adjustment`, `recon.close_period`, `recon.reopen_period`, `recon.waive_exception`.

---

## 6. Decisions

| # | Question | Decision | 
|---|---|---|
| 1 | Edit a wrong entry or post a correction? | Never edit — post a reversing/adjusting entry. Preserves audit integrity. |
| 2 | FX mismatch — match or except? | Match only within one currency; cross-currency gaps become `fx_gap` exceptions resolved by adjustment. |
| 3 | Can a match span periods? | No, unless an entry is explicitly `carried_forward` with a link to its origin period (INV-9). |
