# tests/

The standing regression guard for the constitution gate.

`ci/constitution_validate.py` only proves that the packages **currently** in the
repo pass. It says nothing about whether the validator still *catches* the things
it is supposed to catch. A loosened regex or an over-eager exemption can quietly
turn a hardened check into a no-op while every real package still goes green.

`run_validator_tests.py` closes that gap. It is the executable specification of
what the gate must catch:

- **One fixture per failure mode**, each asserting the gate **CLOSES** for the
  right reason (the expected error category is present, not just any failure):
  missing required file, placeholder, invariant drift, undefined emitted event,
  undeclared trigger, ungoverned PII field, ungoverned tenant entity (derived from
  `DOMAIN_MODEL.md`), seam permission missing from RBAC, seam tier mismatch,
  onboarding→domain direction violation, a domain entity smuggled into an event
  payload, an observability `critical` invariant set `alert: false`, an invariant
  missing from the observability block, and a hardcoded policy literal in `src/`.
- **No-false-positive fixtures**, asserting the gate stays **OPEN**: an onboarding
  event whose name legitimately collides with a domain state name, and the dormant
  policy-externalization NOTE when an app has no `src/` yet.
- **Clean references**, asserting **GATE OPEN strict** for both the worked example
  (`examples/reconciliation-ledger`) and the reference app instance
  (`apps/onboarding-demo`).

Most fixtures are derived by copying the reference app instance into a throwaway
temp mini-repo and applying exactly **one** precise mutation, so each test isolates
a single failure mode. The base app is permanent; only the per-test copy is
temporary.

## Run it

```bash
python tests/run_validator_tests.py
```

Exit code is non-zero if any fixture fails. The suite runs in CI as the second
step of `.github/workflows/constitution.yml`, right after the validator itself.

## Adding a check

When you harden a new check in the validator, add a fixture here in the same
change. A check with no fixture is a check that can rot unnoticed.
