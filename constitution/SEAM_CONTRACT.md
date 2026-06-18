# SEAM_CONTRACT.md — onboarding ↔ domain

This file is mostly app-independent: it defines *how* the two halves talk, not
*what* your domain is. Copy it as-is and fill only the authority mapping table.

---

## 1. The one rule

**The domain depends on onboarding. Onboarding never depends on the domain.**
The dependency arrow points one way. If you ever find an onboarding file importing
a domain type, or the domain writing an onboarding table, the seam is broken.

The domain **reads** identity, tier, role, and entitlements. It **never**
re-implements auth, re-derives a tier, or stores its own copy of who the user is.

---

## 2. What crosses the seam

The domain consumes a single read-only context object, resolved per request by
onboarding (from the session + `/app` state):

```typescript
interface OnboardingContext {
  actor:        { userId: string; aal: 0 | 2 | 3 };
  org:          { orgId: string };                 // tenant — REQUIRED for every domain op
  tier:         0 | 1 | 2 | 3 | 4;
  role:         string;                            // from RBAC.yaml
  entitlements: Record<string, boolean | number>;  // plan features

  // Capability checks — the domain ASKS, onboarding ANSWERS.
  hasPermission(permission: string): boolean;      // checks RBAC.yaml server-side
  getEntitlement(feature: string): boolean | number;

  // May return a step-up requirement instead of throwing — the domain surfaces
  // it to the UI exactly like any other risk.evaluate STEP_UP.
  requireTier(min: 0 | 1 | 2 | 3 | 4, action: string):
    { ok: true } | { ok: false; stepUpTo: number; reason: string };
}
```

The domain calls `requireTier(...)` / `hasPermission(...)` at the start of any
gated action. A `STEP_UP` result is handed back through the same path as
onboarding's own gates — the domain does not invent its own step-up UI.

---

## 3. Tenancy

Every domain entity carries `org_id`, set from `context.org.orgId` on write and
filtered on every read. There is no domain query without a tenant scope. Cross-org
references are forbidden (a domain invariant, not a suggestion).

---

## 4. Authority mapping (the only part you fill in)

Map each gated domain action to a permission and minimum tier. Namespace domain
permissions and append them to `/app/RBAC.yaml` so the same checker enforces them.

| Domain action | Permission (→ RBAC.yaml) | Min tier | Approval |
|---|---|---|---|
| `<domain.action>` | `<domain.permission>` | `<0-4>` | `<y/n>` |

---

## 5. Failure modes the domain must handle

The actor's onboarding state can change *while domain work is in flight*. Define
the behavior; do not let an agent guess.

| Onboarding event | Domain must |
|---|---|
| Account **suspended** | Block new gated writes; preserve in-flight work; allow read of own data per policy. |
| Plan **downgraded** (entitlement lost) | Stop offering the gated feature; never delete data the customer already created; mark it read-only / archived. |
| Tier **dropped** (e.g., failed re-verification) | Re-gate actions at the new tier; a `STEP_UP` reappears on next attempt. |
| Org **deleted** | Domain data follows the tenant deletion + retention policy in `DATA_GOVERNANCE.yaml`; regulated records honor their retention schedule. |
| Role **changed** (SCIM/manual) | Re-evaluate `hasPermission` on next action; no cached permission decisions. |

---

## 6. What must NOT cross the seam

- Onboarding importing domain types or tables — **never**.
- Domain writing to `User`, `Membership`, `Subscription`, etc. — **never** (read-only).
- Domain caching tier/role/permission decisions — **never** (always ask live).
- Raw PII flowing from domain into onboarding events — ids/hashes only.
