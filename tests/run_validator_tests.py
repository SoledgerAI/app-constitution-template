#!/usr/bin/env python3
"""
run_validator_tests.py
======================

The permanent regression guard for ci/constitution_validate.py.

Hand-checking the validator's raw output is how a hardened check silently rots:
someone loosens a regex, the example still "looks fine," and a whole failure mode
stops being caught. This suite replaces that. It is the standing contract for what
the gate must catch -- one test per failure mode, each asserting the gate CLOSES
(and closes for the *right* reason), plus the clean cases that must stay OPEN.

How it works
------------
Most tests start from the real reference app instance (apps/onboarding-demo), copy
it into a throwaway temp mini-repo, apply ONE precise mutation that breaks exactly
one thing, run the validator against that mini-repo, and assert both that the gate
closed and that an error of the expected category is present. The base app is
permanent and lives in the repo; only the per-test copy is temporary. The clean
cases run the validator against the real repo and assert GATE OPEN strict for both
the worked example and the app instance.

Usage
-----
    python tests/run_validator_tests.py          # run the suite (exit 1 on any failure)

Dependencies: PyYAML, jsonschema (same as the validator).
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN_APP = REPO / "apps" / "onboarding-demo"


# --------------------------------------------------------------------------- #
# Load the validator as a module so we can call run() directly.
# --------------------------------------------------------------------------- #

def _load_validator():
    path = REPO / "ci" / "constitution_validate.py"
    spec = importlib.util.spec_from_file_location("constitution_validate", path)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: the validator uses `from __future__ import annotations`
    # with @dataclass, and dataclasses resolves those string annotations by looking
    # the module up in sys.modules by name.
    sys.modules["constitution_validate"] = mod
    spec.loader.exec_module(mod)
    return mod


CV = _load_validator()


def validate(root: Path, package: str | None = None, strict: bool = True):
    """Return (gate_open: bool, Result). Mirrors main()'s pass/fail logic."""
    res, _packages = CV.run(Path(root), package)
    failed = bool(res.errors) or (strict and bool(res.warnings))
    return (not failed), res


# --------------------------------------------------------------------------- #
# Staging + mutation helpers
# --------------------------------------------------------------------------- #

_TMP_ROOTS: list[Path] = []


def stage_app() -> tuple[Path, Path]:
    """Copy the golden app into a fresh temp mini-repo at <tmp>/apps/onboarding-demo.
    Returns (mini_repo_root, app_dir). The mini-repo holds exactly one package, so
    the validator's repo-wide scans stay isolated to this app."""
    tmp = Path(tempfile.mkdtemp(prefix="constgate-"))
    _TMP_ROOTS.append(tmp)
    dst = tmp / "apps" / "onboarding-demo"
    shutil.copytree(GOLDEN_APP, dst)
    return tmp, dst


def stage_templates() -> tuple[Path, Path]:
    """Copy domain-templates/ into a fresh temp mini-repo. Used to prove the schema
    check actually validates the _TEMPLATE.yaml twins, not just the real artifacts.
    The mini-repo has no examples/ or apps/, so it holds nothing but the templates."""
    tmp = Path(tempfile.mkdtemp(prefix="constgate-tpl-"))
    _TMP_ROOTS.append(tmp)
    dst = tmp / "domain-templates"
    shutil.copytree(REPO / "domain-templates", dst)
    return tmp, dst


def cleanup() -> None:
    for t in _TMP_ROOTS:
        shutil.rmtree(t, ignore_errors=True)


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"anchor not found in {path.name}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def overwrite(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# convenience accessors for the golden app's files inside a staged copy
def dom(app: Path, name: str) -> Path:
    return app / "domain" / name


def onb(app: Path, name: str) -> Path:
    return app / "onboarding" / name


# --------------------------------------------------------------------------- #
# The suite.  Each test mutates a staged copy, then asserts on the result.
# A test returns (ok: bool, detail: str).
# --------------------------------------------------------------------------- #

def _has_error(res, needle: str) -> bool:
    return any(needle in e for e in res.errors)


def _has_note(res, needle: str) -> bool:
    return any(needle in n for n in res.notes)


def expect_closed(res_open: bool, res, needle: str) -> tuple[bool, str]:
    if res_open:
        return False, "gate stayed OPEN but should have CLOSED"
    if not _has_error(res, needle):
        return False, f"gate closed, but no error matched {needle!r}; errors={res.errors}"
    return True, f"closed on {needle!r}"


# ---- broken fixtures: gate must CLOSE -------------------------------------- #

def t_missing_required_file():
    _root, app = stage_app()
    (app / "TEST_PLAN.md").unlink()
    open_, res = validate(_root)
    return expect_closed(open_, res, "[COMPLETE]")


def t_placeholder_present():
    _root, app = stage_app()
    append(dom(app, "DOMAIN_MODEL.md"), "\n<!-- TODO finish this section -->\n")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[PLACEHOLDER]")


def t_invariant_drift():
    _root, app = stage_app()
    # INVARIANTS says INV-2 on_violation: reject; make DOMAIN_RULES disagree.
    edit(dom(app, "DOMAIN_RULES.yaml"),
         "    enforced_at: grant_create\n    on_violation: reject",
         "    enforced_at: grant_create\n    on_violation: review")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[INV-DRIFT]")


def t_undefined_emitted_event():
    _root, app = stage_app()
    edit(dom(app, "STATE_MACHINES.yaml"), "emits: access_granted", "emits: ghost_event")
    open_, res = validate(_root)
    return expect_closed(open_, res, "emitted event 'ghost_event' is not defined")


def t_undeclared_trigger():
    _root, app = stage_app()
    edit(dom(app, "STATE_MACHINES.yaml"), "event: grant_expired", "event: ghost_trigger")
    open_, res = validate(_root)
    return expect_closed(open_, res, "transition trigger 'ghost_trigger' is not declared")


def t_ungoverned_pii_field():
    _root, app = stage_app()
    # Declare a new sensitive field with no matching DATA_GOVERNANCE entry.
    edit(dom(app, "DOMAIN_RULES.yaml"),
         "    - field: Grant.approved_by\n      classification: personal      # user identifier of the approver",
         "    - field: Grant.approved_by\n      classification: personal      # user identifier of the approver\n"
         "    - field: AccessRequest.reason\n      classification: personal")
    open_, res = validate(_root)
    if open_:
        return False, "gate stayed OPEN but should have CLOSED"
    # Bind to the governance check: the SAME error line must carry both the [GOVERN]
    # tag and the field name, so an unrelated error mentioning the field can't satisfy it.
    if not any("[GOVERN]" in e and "AccessRequest.reason" in e for e in res.errors):
        return False, f"no [GOVERN] error named AccessRequest.reason; errors={res.errors}"
    return True, "closed on [GOVERN] for AccessRequest.reason"


def t_ungoverned_tenant_entity_from_domain_model():
    _root, app = stage_app()
    # Add an entity to DOMAIN_MODEL.md only. INV-3 scope:all makes every modeled
    # entity tenant-scoped, so this must be caught even though nobody touched
    # data_fields.tenant_scoped_entities or DATA_GOVERNANCE.yaml.
    edit(dom(app, "DOMAIN_MODEL.md"),
         "## 3. Aggregates & consistency boundaries",
         "### AuditEntry\n- **Definition:** an immutable access-audit record.\n"
         "- **Tenancy:** `org_id` — yes.\n\n## 3. Aggregates & consistency boundaries")
    open_, res = validate(_root)
    return expect_closed(open_, res, "tenant-scoped entity 'AuditEntry'")


def t_seam_permission_missing_from_rbac():
    _root, app = stage_app()
    # Add an authority_map permission that RBAC.yaml does not declare.
    edit(dom(app, "DOMAIN_RULES.yaml"),
         "    notes: Revoke a live grant before its expiry; fully audited.",
         "    notes: Revoke a live grant before its expiry; fully audited.\n"
         "  access.audit:\n    permission: access.audit\n    min_tier: 2\n"
         "    requires_approval: n\n    notes: Read the access audit log.")
    open_, res = validate(_root)
    return expect_closed(open_, res, "authority_map permission 'access.audit' is not declared in RBAC.yaml")


def t_seam_tier_mismatch():
    _root, app = stage_app()
    # authority_map says access.approve is min_tier 3; RBAC says 3. Make them disagree.
    edit(dom(app, "DOMAIN_RULES.yaml"),
         "  access.approve:\n    permission: access.approve\n    min_tier: 3",
         "  access.approve:\n    permission: access.approve\n    min_tier: 4")
    open_, res = validate(_root)
    return expect_closed(open_, res, "tier mismatch for permission 'access.approve'")


def t_onboarding_to_domain_direction_violation():
    _root, app = stage_app()
    # Smuggle a domain entity name into an onboarding policy file's DATA.
    edit(onb(app, "RISK_POLICIES.yaml"),
         "resolution:\n  order: [hard_blocks, tier_gap, velocity_stepup, allow]\n  default: allow",
         "resolution:\n  order: [hard_blocks, tier_gap, velocity_stepup, allow]\n  default: allow\n"
         "  note: AccessRequest decisions feed this")
    open_, res = validate(_root)
    return expect_closed(open_, res, "references domain token 'AccessRequest'")


def t_domain_entity_in_event_payload():
    _root, app = stage_app()
    # A domain entity referenced inside an onboarding EVENTS.yaml payload VALUE
    # (not a declared event/trigger name) must still be caught.
    append_event(onb(app, "EVENTS.yaml"),
                 "  - name: probe_event\n    when: a generic onboarding probe\n"
                 "    properties:\n      subject: AccessRequest\n    feeds: [debug]\n")
    open_, res = validate(_root)
    return expect_closed(open_, res, "references domain token 'AccessRequest'")


def t_observability_critical_alert_false():
    _root, app = stage_app()
    edit(dom(app, "OBSERVABILITY.md"),
         'alert: true,  threshold: "> 0 (a decided request changed)"',
         'alert: false, threshold: "> 0 (a decided request changed)"')
    open_, res = validate(_root)
    if open_:
        return False, "gate stayed OPEN but should have CLOSED"
    # Bind to the specific critical-must-alert message, not the bare [OBSERVE] tag, so a
    # missing/unparseable block (which also emits [OBSERVE]) can't satisfy this fixture.
    if not any("INV-1" in e and "alert: False" in e and "must be true" in e for e in res.errors):
        return False, f"no critical-alert [OBSERVE] error for INV-1; errors={res.errors}"
    return True, "closed on INV-1 critical alert:false (must be true)"


def t_observability_invariant_missing():
    _root, app = stage_app()
    edit(dom(app, "OBSERVABILITY.md"),
         '  INV-3: { metric: cross_tenant_access_attempts,   alert: true,  threshold: "> 0" }\n',
         "")
    open_, res = validate(_root)
    return expect_closed(open_, res, "INV-3 has no entry")


def t_hardcoded_policy_literal_in_src():
    _root, app = stage_app()
    # Generating code that hardcodes a policy value activates the (otherwise
    # dormant) externalization check.
    src = app / "src"
    src.mkdir()
    (src / "grants.py").write_text(
        "# generated access-grants module\n"
        "def mint_window():\n"
        "    # leaked policy literal: should read max_grant_ttl_hours from config\n"
        "    return 72\n",
        encoding="utf-8",
    )
    open_, res = validate(_root)
    return expect_closed(open_, res, "policy 'max_grant_ttl_hours' (=72) is hardcoded")


# ---- clean / no-false-positive fixtures: gate must stay OPEN --------------- #

def append_event(events_path: Path, item_yaml: str) -> None:
    """Insert a new event list item just before the `metrics:` block."""
    edit(events_path, "\nmetrics:", "\n" + item_yaml + "\nmetrics:")


def t_events_name_collision_passes():
    _root, app = stage_app()
    # An onboarding event whose NAME collides with a domain state ('approved')
    # is legitimate: onboarding owns its event vocabulary. Must NOT false-positive.
    append_event(onb(app, "EVENTS.yaml"),
                 "  - name: approved\n    when: a generic onboarding step finishes\n"
                 "    properties:\n      user_id: string\n    feeds: [step_quality]\n")
    open_, res = validate(_root)
    if not open_:
        return False, f"gate CLOSED on a legitimate name collision; errors={res.errors}"
    return True, "stayed open on event-name/state collision"


def t_schema_state_machines_missing_target():
    """STATE_MACHINES schema is live. A transition loses its `to:` target. The
    validator's own logic never reads `to`, so without JSON-Schema validation this
    passes vacuously; the schema closes it."""
    _root, app = stage_app()
    edit(dom(app, "STATE_MACHINES.yaml"),
         "from: submitted, to: approved, event: request_approved",
         "from: submitted, event: request_approved")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[SCHEMA]")


def t_schema_invariants_as_list():
    """INVARIANTS schema is live. `invariants` must be a MAP of id -> body; here it
    is rewritten as a LIST (the DOMAIN_RULES shape) -- parseable YAML, wrong shape."""
    _root, app = stage_app()
    overwrite(dom(app, "INVARIANTS.yaml"),
              "version: 1\n"
              "invariants:\n"
              "  - id: INV-1\n"
              "    severity: critical\n"
              "    statement: placeholder\n"
              "    scope: AccessRequest\n"
              "    enforced_at: request_decision\n"
              "    on_violation: reject\n")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[SCHEMA]")


def t_schema_event_model_events_as_list():
    """EVENT_MODEL schema is live. `events` must be a MAP of name -> body; here it
    is rewritten as a LIST, which would otherwise yield an empty defined-event set."""
    _root, app = stage_app()
    overwrite(dom(app, "EVENT_MODEL.yaml"),
              "version: 1\n"
              "events:\n"
              "  - name: access_granted\n"
              "    producer: decision service\n"
              "    schema: {}\n")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[SCHEMA]")


def t_schema_domain_rules_authority_map_misnested():
    """DOMAIN_RULES schema is live. `authority_map` is rewritten as a LIST instead of
    a map. WITHOUT the schema this is the vacuous-pass case: _authority_permissions()
    reads an empty set, so the seam permission check verifies nothing and the gate
    stays OPEN. The schema closes it."""
    _root, app = stage_app()
    edit(dom(app, "DOMAIN_RULES.yaml"),
         "authority_map:\n"
         "  access.request:\n"
         "    permission: access.request\n"
         "    min_tier: 1\n"
         "    requires_approval: n\n"
         "    notes: Submit a request to use a protected resource.\n"
         "  access.approve:\n"
         "    permission: access.approve\n"
         "    min_tier: 3\n"
         "    requires_approval: n\n"
         "    notes: Approve or deny a pending request.\n"
         "  access.revoke:\n"
         "    permission: access.revoke\n"
         "    min_tier: 3\n"
         "    requires_approval: y\n"
         "    notes: Revoke a live grant before its expiry; fully audited.",
         "authority_map:\n"
         "  - permission: access.request\n"
         "    min_tier: 1\n"
         "  - permission: access.approve\n"
         "    min_tier: 3\n"
         "  - permission: access.revoke\n"
         "    min_tier: 3")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[SCHEMA]")


def t_schema_template_twin_is_validated():
    """Pins that _schema_stem_for() matches the _TEMPLATE.yaml twins, not just the
    real artifacts. Without that match, the 'same schema governs both' claim is
    untested. Break a required field in INVARIANTS_TEMPLATE.yaml and the gate must
    close on [SCHEMA] -- proving the template is genuinely validated, not skipped."""
    _root, tpl = stage_templates()
    edit(tpl / "INVARIANTS_TEMPLATE.yaml",
         '    on_violation: "<reject | review | halt>"\n',
         "")
    open_, res = validate(_root)
    return expect_closed(open_, res, "[SCHEMA]")


def t_governance_exemption_tolerates_domain_tokens():
    """PIN (exemption works): DATA_GOVERNANCE.yaml may name domain internals freely.
    Inject several domain tokens (a state name, a decision verb, an invariant id)
    into that file's DATA -- not just the keyed Entity.attribute entries -- and the
    gate must stay OPEN. If someone ever narrows the whole-file exemption, this
    turns red and forces a deliberate decision."""
    _root, app = stage_app()
    append(onb(app, "DATA_GOVERNANCE.yaml"),
           '\n# pin: extra domain references here must NOT trip the direction scan.\n'
           'audit_reference: "covers the submitted -> approved decision and INV-1"\n')
    open_, res = validate(_root)
    if not open_:
        return False, f"gate CLOSED on domain tokens inside DATA_GOVERNANCE.yaml; errors={res.errors}"
    return True, "DATA_GOVERNANCE.yaml tolerates domain tokens (exemption active)"


def t_governance_exemption_does_not_leak():
    """PIN (exemption is scoped to the filename): the SAME domain token, placed in a
    DIFFERENT onboarding file, must still FAIL. This proves the carve-out is bound to
    DATA_GOVERNANCE.yaml and has not leaked to the rest of onboarding/."""
    _root, app = stage_app()
    edit(onb(app, "RISK_POLICIES.yaml"),
         "resolution:\n  order: [hard_blocks, tier_gap, velocity_stepup, allow]\n  default: allow",
         "resolution:\n  order: [hard_blocks, tier_gap, velocity_stepup, allow]\n  default: allow\n"
         '  note: "covers the submitted decision"')
    open_, res = validate(_root)
    return expect_closed(open_, res, "references domain token 'submitted'")


def t_dormant_policy_note_when_no_src():
    _root, _app = stage_app()  # golden app ships no src/ tree
    open_, res = validate(_root)
    if not open_:
        return False, f"gate CLOSED unexpectedly; errors={res.errors}"
    if not _has_note(res, "check inactive"):
        return False, f"expected a dormant POLICY note; notes={res.notes}"
    return True, "dormant POLICY note present, gate open"


def t_clean_example_open_strict():
    open_, res = validate(REPO, "reconciliation-ledger", strict=True)
    if not open_:
        return False, f"reference example did not pass strict; errors={res.errors} warnings={res.warnings}"
    return True, "reconciliation-ledger GATE OPEN strict"


def t_clean_app_instance_open_strict():
    open_, res = validate(REPO, "onboarding-demo", strict=True)
    if not open_:
        return False, f"app instance did not pass strict; errors={res.errors} warnings={res.warnings}"
    return True, "onboarding-demo GATE OPEN strict"


# --------------------------------------------------------------------------- #
# Registry + runner
# --------------------------------------------------------------------------- #

TESTS = [
    # failure modes -- gate must CLOSE
    ("missing required file",                 t_missing_required_file),
    ("placeholder present",                   t_placeholder_present),
    ("invariant drift (INVARIANTS vs RULES)", t_invariant_drift),
    ("undefined emitted event",               t_undefined_emitted_event),
    ("undeclared trigger",                    t_undeclared_trigger),
    ("ungoverned PII field",                  t_ungoverned_pii_field),
    ("ungoverned tenant entity (derived)",    t_ungoverned_tenant_entity_from_domain_model),
    ("seam permission missing from RBAC",     t_seam_permission_missing_from_rbac),
    ("seam tier mismatch",                    t_seam_tier_mismatch),
    ("onboarding->domain direction",          t_onboarding_to_domain_direction_violation),
    ("domain entity in event payload",        t_domain_entity_in_event_payload),
    ("observability critical alert:false",    t_observability_critical_alert_false),
    ("observability invariant missing",       t_observability_invariant_missing),
    ("hardcoded policy literal in src/",      t_hardcoded_policy_literal_in_src),
    ("schema: STATE_MACHINES missing target", t_schema_state_machines_missing_target),
    ("schema: INVARIANTS as list not map",    t_schema_invariants_as_list),
    ("schema: EVENT_MODEL events as list",    t_schema_event_model_events_as_list),
    ("schema: DOMAIN_RULES authority_map list", t_schema_domain_rules_authority_map_misnested),
    ("schema: _TEMPLATE twin is validated",   t_schema_template_twin_is_validated),
    # clean / no-false-positive -- gate must stay OPEN
    ("EVENTS name/state collision PASSES",    t_events_name_collision_passes),
    ("DATA_GOVERNANCE exemption tolerates token", t_governance_exemption_tolerates_domain_tokens),
    ("DATA_GOVERNANCE exemption does NOT leak",   t_governance_exemption_does_not_leak),
    ("dormant policy NOTE when no src/",      t_dormant_policy_note_when_no_src),
    ("clean example OPEN strict",             t_clean_example_open_strict),
    ("clean app instance OPEN strict",        t_clean_app_instance_open_strict),
]


def main() -> int:
    print("=" * 70)
    print("  CONSTITUTION VALIDATOR — FIXTURE REGRESSION SUITE")
    print(f"  validator: ci/constitution_validate.py")
    print(f"  base app:  apps/onboarding-demo")
    print("=" * 70)

    passed = 0
    failed = 0
    try:
        for name, fn in TESTS:
            try:
                ok, detail = fn()
            except Exception as exc:  # a test harness error is itself a failure
                ok, detail = False, f"EXCEPTION: {exc.__class__.__name__}: {exc}"
            mark = "PASS" if ok else "FAIL"
            print(f"  [{mark}] {name:<40} {detail}")
            if ok:
                passed += 1
            else:
                failed += 1
    finally:
        cleanup()

    print("-" * 70)
    print(f"  {passed} passed, {failed} failed, {len(TESTS)} total")
    print("=" * 70)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
