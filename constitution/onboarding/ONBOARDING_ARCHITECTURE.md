# ONBOARDING_ARCHITECTURE.md

**Status:** Proposed design. Not verified until signed off (see end of file).
**Audience:** Humans — founders, security, compliance, product. Agents read `IMPLEMENTATION_SPEC.md` and the YAML configs, not this file.
**Scope:** Customer acquisition → authentication → activation → identity → entitlements → billing → lifecycle, plus agent-readiness as a horizon layer.

> This workflow is a product / security architecture, **not legal advice**; regulated implementations require counsel and compliance signoff.

---

## Core rule

**Move friction to risk.** Collect nothing early unless it improves activation, security, compliance, or revenue. This is not a form sequence — it is an **assurance ladder**: low risk gets low friction, high risk gets proof, regulated activity gets compliance.

---

## The assurance ladder (the spine)

Every gated action maps to the lowest tier that clears it. A customer climbs only as far as their next action requires.

| Tier | Name | Cleared by | Assurance | Unlocks | Owner |
|---|---|---|---|---|---|
| 0 | Anonymous | Bot / human signal only | none | Browse, seeded sandbox, view value | Growth |
| 1 | Reachable | Email + passkey enrolled | AAL2 | Persistent workspace, save work, invite-by-link | Identity |
| 2 | Billable | Profile context + tokenized payment method *(commercial readiness, not identity)* | AAL2 | Paid plan, higher usage tier, team admin | Product / Finance |
| 3 | Verified | mDL / VC (or doc + liveness), sanctions clear | AAL2 + proofing fit to use case | Money movement, regulated activity, high-value txn | Compliance / Risk |
| 4 | High-assurance | Non-exportable, device-bound phishing-resistant authenticator + step-up | AAL3 | Privileged admin, large transfers, agent authorization | Security |

Tier definitions are the source of truth in `RISK_POLICIES.yaml`.

---

## The risk engine (the central chokepoint)

Triggers do not live scattered across stages. Every gated action calls one function:

```
risk.evaluate(actor, action, context) -> decision
```

- **Inputs / signals:** requested action + its required tier; customer's current tier & AAL; bot score; device fingerprint; IP/geo; email risk; velocity & behavioral anomaly; liveness/deepfake score (at IDV); sanctions status.
- **Evaluate:** policy rules + risk score → required tier. If `current_tier ≥ required` and signals are clean → pass. If there's a gap → minimum step-up to close it. If signals are adverse → review or deny.
- **Output — one decision:** `ALLOW` · `STEP_UP` · `REVIEW` · `DENY`.

Adding a new gated action means **adding a policy, not editing a stage.**

---

## Stages (the flow that serves the ladder)

| # | Stage | Tier | Owner | Verifies |
|---|---|---|---|---|
| 00 | Acquisition & intent capture | T0 | Growth | human-likely, email deliverable, consent timestamped |
| 01 | Account creation — passkey-first | → T1 | Identity | phishing-resistant AAL2, domain-bound, public key only stored |
| R | Recovery & device rotation (always-on) | — | Identity + Trust & Safety | recovery never lowers assurance; step-up logged |
| 02 | First value — the "aha" | T1 | Product | `activation_reached` fired |
| 03 | Progressive profile | → T2 | Product | data classified, consent recorded |
| 04 | Identity — VC + selective disclosure | → T3 | Compliance / Risk | issuer signature valid, liveness clear, sanctions screened continuously, minimal PII |
| 05 | Entitlements & provisioning | admin → T4 | Platform / Security | scoped, auditable, revocable; admin = AAL3 |
| 06 | Billing | T2 | Finance / RevOps | $0 auth validates, billing state synced |
| 07 | Lifecycle & customer success | T2+ | Customer Success | no customer left "almost activated" |
| 08 | Agent readiness (horizon) | T4 gate | Platform/Security + Compliance | human binding, auditable delegation, immutable trail |

**Launch gate for Stage 08 (concrete, not "when mature"):** ship only when (1) a payment network you use publishes agent acceptance, (2) the liability model is signed off by counsel, and (3) consent UX passes review. Until all three: build the primitives, keep the door closed.

---

## Two flows that close prior deficits

**Returning user & identity linking** — single email entry point; the system decides sign-in vs sign-up, never the customer. Known email → offer enrolled passkey. Unknown → account creation. Known email + new device → recovery, not a failed login. **Linking/merge:** match on *verified* email only; never auto-merge on an unverified claim (takeover vector); keep conflicting profile data and flag for the customer; linking a method does not change tier.

**B2B invite & domain auto-join** — invite carries `org_id`, role, expiry. Invitee enrolls passkey → joins at the set role. Verified domain → optional domain auto-join (admin-approved or per policy). Enterprise → SAML SSO + SCIM from the IdP. Seats bill on *accepted join*, not on invite sent. Admin grants trigger a Tier 4 step-up.

---

## Standards & assumptions (validation backbone — and its limits)

| Standard | How to treat it |
|---|---|
| NIST SP 800-63-4 | AAL2 = synced passkeys; **AAL3 requires non-exportable keys**. In force. |
| FIDO2 / WebAuthn | Stable, shipping across browsers/OSes. Build on directly. |
| FIDO CXP / CXF | **Design-compatible, not production-dependent.** Interoperability path; don't rely on as universal behavior. |
| ISO 18013-5 / -7 | mDL in-person / remote (OpenID4VP). In active DMV rollout; coverage varies by state. |
| W3C Verifiable Credentials | Signed, selectively disclosable claims; carrier for agent mandates. |
| NIST SP 1800-42A | **Initial public draft guidance** for mDL in FI identity verification — not final law/standard. |
| eIDAS 2.0 / EUDI | EU wallet acceptance for banking/finance/telecom; deadline Nov 2027 — relevant only with an EU footprint. |
| PCI DSS 4.0 · NIS2 · DORA | Phishing-resistant-MFA requirements passkeys satisfy. In force. |
| AP2 (FIDO) · KYA | Agent payments + human binding. Multi-protocol and early — horizon only. |

---

## Data governance contract

No field enters the workflow until all seven attributes are defined: `purpose`, `classification`, `retention`, `deletion`, `system_of_record`, `downstream_processors`, `audit_event`. The binding registry is `DATA_GOVERNANCE.yaml`.

---

## Regulated domain overlays (apply only to the domain you operate in)

The core ladder is domain-neutral. Bolt on the overlay for the domain you actually serve; none is optional once the domain applies.

- **Healthcare — HIPAA / BAA** (Owner: Privacy Officer + Compliance + Security): PHI is its own classification; minimum-necessary access, every access audited. Signed BAA with every PHI processor before go-live. **PHI access requires Tier 3 or stronger, based on role, data sensitivity, and threat model**; administrative PHI access requires Tier 4. Breach-notification workflow; six-year minimum log retention.
- **Fintech — CIP / AML** (Owner: BSA/AML Officer + Compliance): CIP at or before account opening for covered activity — product preference cannot move this line. KYB beneficial ownership; OFAC/sanctions at onboarding and continuously. Monitoring & risk scores feed `risk.evaluate`; SAR path defined. Money movement ≥ Tier 3; BSA recordkeeping (commonly five years).
- **Children & education — COPPA / minors** (Owner: Privacy / Legal): age signal at acquisition before any profile data. Under the COPPA threshold → verifiable parental consent before collecting any child PII. Hard minimization; no behavioral ads to minors; honor FERPA/school authorization. Default to most-restrictive processing; parent-initiated deletion. Verify status rather than assume adulthood.

---

## Verification & signoff

"Verified" means a defined thing: this architecture is considered verified only once the accountable owners have reviewed and signed — **Security** (auth & assurance), **Compliance / AML or Privacy Officer** (domain-dependent), **Legal**, and **Product**. Until those signoffs exist, treat this as a proposed design, not an approved one.

| Owner | Role | Signed | Date |
|---|---|---|---|
| Security | Auth & assurance | ☐ | |
| Compliance / AML / Privacy | Domain-dependent | ☐ | |
| Legal | Counsel | ☐ | |
| Product | Owner of record | ☐ | |
