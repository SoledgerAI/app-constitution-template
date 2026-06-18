# Onboarding Constitution

This folder contains the reusable onboarding architecture for applications generated from this constitution.

Onboarding is the shared acquisition-to-activation horizontal. It governs identity, access, tiering, risk checks, role assignment, entitlement checks, and the seam between onboarding and the app-specific domain.

The onboarding layer is reused across applications. Individual applications may clone and tune policy configuration, but they should not fork or re-implement the onboarding architecture.

## Contents

Expected files in this folder:

```txt
ONBOARDING_ARCHITECTURE.md
IMPLEMENTATION_SPEC.md
SEAM_CONTRACT.md
TEST_PLAN.md
```

## Rule

The domain layer may read onboarding context such as identity, tier, role, and entitlements.

The onboarding layer must not depend on app-specific domain entities, rules, or state machines.

The seam is one-way.
