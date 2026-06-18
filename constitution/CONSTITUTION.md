# CONSTITUTION.md

The constitution is built **once** and reused across every application in this
repository. Every app — its onboarding config and its domain package — must
*align with* this document. When an app artifact conflicts with the constitution,
the constitution wins or the conflict is escalated; it is never silently resolved
in code.

---

## The layered stack

Every application is specified top-down. Code is the **last** artifact produced,
never the first.

```
Constitution        ← this file: principles that don't change
   ↓
Architecture        ← onboarding (shared horizontal) + how the app is shaped
   ↓
Domain Model        ← the entities and language of THIS app
   ↓
Invariants          ← truths that must never be false
   ↓
Domain Rules        ← enforcement points + tunable policies + authority map
   ↓
State Machines      ← legal and forbidden lifecycle transitions
   ↓
Event Model         ← the nervous system; state made explicit
   ↓
Observability       ← every invariant watched in production
   ↓
Test Plan           ← expectations derived from the above
   ↓
Implementation Plan → Code → Tests → Review → Deploy
```

---

## Principles (non-negotiable)

1. **Governance before generation. Truth before code.** No application begins
   with code. It begins with the domain package. When uncertain, stop and ask.

2. **Move friction to risk.** Collect nothing and gate nothing early unless it
   improves activation, security, compliance, or revenue. Low risk gets low
   friction; high risk gets proof; regulated activity gets compliance.

3. **Invariants are truth; policies are settings.** Invariants (debits equal
   credits; posted records are immutable) never change and live in
   `INVARIANTS.yaml`. Policies (a tolerance, a threshold, a tier mapping) change
   and live in policy YAML. Never conflate them, and never hardcode a policy
   value in application code.

4. **Config, not code.** Tiers, risk thresholds, RBAC, data fields, events, and
   domain policies are read from YAML at runtime. Changing behavior is a config
   edit, not a code change.

5. **The seam is one-way.** The domain depends on onboarding; onboarding never
   depends on the domain. The domain *reads* identity, tier, role, and
   entitlements across the seam and never re-implements auth, re-derives a tier,
   or writes onboarding tables. (See `constitution/onboarding/SEAM_CONTRACT.md`.)

6. **Assurance ladder + least privilege.** Access is granted at the lowest tier
   that clears an action, and at the least privilege a role requires.
   Admin-class authority requires AAL3 (a non-exportable, device-bound
   authenticator).

7. **Immutability and auditability.** Posted financial records are immutable;
   corrections are new postings, never edits. Every consequential action is
   recorded, attributable, and reconstructable.

8. **Tenancy isolation.** Every tenant-scoped entity carries `org_id`. No query
   runs without a tenant scope; no reference crosses tenants.

9. **Idempotency and no dead-ends.** Operations that can be retried or re-delivered
   are safe to repeat. Every flow has a forward path or a defined fallback; a
   dead-end is a defect.

10. **Data minimization and selective disclosure.** Collect the minimum field for
    the purpose; prefer disclosing only the required attribute over collecting the
    whole record. Every personal-data field has a governance entry.

11. **The agent does not invent business logic.** Invariants, domain rules, and
    permissions are authored by humans. The agent scaffolds, generates, and
    enforces — it never originates the truth of the domain.

12. **Standards-anchored, honest about limits.** Cutting-edge choices map to named
    standards, with their maturity stated. Regulated correctness (HIPAA, CIP/AML,
    COPPA) is decided by counsel and compliance signoff, not by the agent.

13. **"Verified" means signed off.** An architecture or release is "verified" only
    when the accountable owners — Security, Compliance/Privacy (domain-dependent),
    Legal, and Product — have reviewed and signed. Until then it is proposed.

---

## What the constitution layer contains

```
constitution/
  CONSTITUTION.md                       ← this file
  onboarding/                           ← the reusable acquisition→activation horizontal
    ONBOARDING_ARCHITECTURE.md
    IMPLEMENTATION_SPEC.md
    SEAM_CONTRACT.md
    TEST_PLAN.md                        ← onboarding test expectations (template)
```

The onboarding horizontal is shared because ~80% of it is identical across apps.
Each application clones the **policy templates** (`policies/`) into thin,
app-specific config instances; it does not fork the architecture.

> This document is product/security architecture, **not legal advice**. Regulated
> implementations require counsel and compliance signoff.
