# Running the Constitution Gate

`ci/constitution-checks.md` describes the rules. `ci/constitution_validate.py`
**enforces** them. This turns the "final gate" from a paragraph an agent is
trusted to obey into a build that actually fails when the package is wrong.

## What it checks

| Check | What it catches | Severity |
|---|---|---|
| YAML validity | A `.yaml` file that won't parse | error |
| Schema conformance | A schema-governed artifact (`INVARIANTS`/`DOMAIN_RULES`/`STATE_MACHINES`/`EVENT_MODEL`) that parses but has the wrong **shape** — e.g. `invariants` as a list where a map is required, a transition with no `to`, a mis-nested `authority_map` that would otherwise yield an empty set and pass vacuously | error |
| Template purity | A `_TEMPLATE` file or a `copy`/`(1)` duplicate living in `examples/` or `apps/` | error |
| Package completeness | A real app missing a required domain/onboarding artifact | error |
| **Invariant consistency** | `INVARIANTS.yaml` and `DOMAIN_RULES.yaml` disagreeing on any invariant's `on_violation`, `enforced_at`, or `scope` | error |
| Event consistency | An event the state machine *emits* that the event model never defines | error |
| Seam consistency | An `authority_map` permission missing from `RBAC.yaml` | error |
| Invariant observability | An invariant with no metric in `OBSERVABILITY.md` | error |
| Data governance | A real app with no `DATA_GOVERNANCE.yaml` entries | warn |
| Unresolved placeholders | `TBD` / `TODO` / `FILL IN` left in a package | warn |
| Unmodeled triggers | A state-machine trigger not yet in the event model | warn |

Errors close the gate (exit code 1). Warnings don't, unless you pass `--strict`.

## How to run it

Locally, from the repo root:

```bash
pip install pyyaml jsonschema
python3 ci/constitution_validate.py                 # check everything
python3 ci/constitution_validate.py --package reconciliation-ledger
python3 ci/constitution_validate.py --strict        # warnings fail too
python3 tests/run_validator_tests.py                # prove the gate still CATCHES every failure mode
```

The JSON Schemas the gate validates against live in `ci/schemas/`. Each governs
both the real artifact (`INVARIANTS.yaml`) and its `_TEMPLATE.yaml` twin.

Automatically: the workflow in `.github/workflows/constitution.yml` runs this on
every push and pull request to `main`. A failing run shows a red X on the commit
and the PR. Turn on branch protection for `main` (Settings → Branches → require
the "Validate app constitution package" check) so a package that fails the gate
**cannot be merged**.

## Reading the output

```
ERRORS (1):
  x [INV-DRIFT] reconciliation-ledger: INV-1 'on_violation' disagrees
      (INVARIANTS.yaml='halt' vs DOMAIN_RULES.yaml='reject')

RESULT: GATE CLOSED — do not generate code until these are resolved.
```

The tag in brackets tells you which check fired. `GATE CLOSED` means at least
one error; fix it and re-run until you get `GATE OPEN`.

## The honest caveat

This validator checks **structure and consistency** — that the files agree, that
nothing referenced is undefined, that nothing required is missing. It cannot tell
you whether an invariant is *correct* for your business. That judgment still
belongs to a human. What it removes is the silent drift: two files quietly
disagreeing, an emitted event no one defined, a permission with no home.
