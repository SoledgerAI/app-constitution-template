#!/usr/bin/env python3
"""
constitution_validate.py
========================

Executable enforcement for the App Constitution template.

ci/constitution-checks.md describes nine checks in prose and promises a "final
gate" that blocks code generation until they pass. Until now nothing actually
ran. This script runs them, and adds one the prose version misses: that
INVARIANTS.yaml and DOMAIN_RULES.yaml agree on every shared invariant.

Usage
-----
    python3 ci/constitution_validate.py                 # validate the whole repo
    python3 ci/constitution_validate.py --package examples/reconciliation-ledger
    python3 ci/constitution_validate.py --strict        # warnings also fail the build

Exit codes
----------
    0  all required checks passed (the gate is open)
    1  at least one ERROR (the gate is closed -- do not generate code)

Dependencies: PyYAML  (pip install pyyaml)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Run:  pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# --------------------------------------------------------------------------- #
# Result plumbing
# --------------------------------------------------------------------------- #

@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def merge(self, other: "Result") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


PLACEHOLDERS = ["TBD", "TODO", "UNKNOWN", "ASK LATER", "FILL IN", "FIXME"]

# Directories that legitimately contain blank-fill markers like <INV-1>.
# Placeholder / drift scanning must skip these or it cries wolf on templates.
TEMPLATE_DIRS = ("domain-templates", "policies")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def load_yaml(path: Path, res: Result):
    """Parse a YAML file; record an error and return None on failure."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        res.error(f"[YAML] {path}: does not parse ({exc.__class__.__name__})")
        return None
    except OSError as exc:
        res.error(f"[YAML] {path}: cannot read ({exc})")
        return None


def normalize_invariants(blob) -> dict[str, dict]:
    """
    INVARIANTS.yaml stores invariants as a MAP {INV-1: {...}}.
    DOMAIN_RULES.yaml stores them as a LIST [{id: INV-1, ...}].
    Return a single id -> fields dict either way.
    """
    out: dict[str, dict] = {}
    if not blob:
        return out
    inv = blob.get("invariants") if isinstance(blob, dict) else None
    if isinstance(inv, dict):
        for key, body in inv.items():
            if isinstance(body, dict):
                out[str(key)] = body
    elif isinstance(inv, list):
        for item in inv:
            if isinstance(item, dict) and "id" in item:
                out[str(item["id"])] = item
    return out


def discover_packages(root: Path) -> list[Path]:
    """A package is any examples/* or apps/* directory containing INVARIANTS.yaml
    (flat worked example) or a domain/INVARIANTS.yaml (full app instance)."""
    packages: list[Path] = []
    for parent in ("examples", "apps"):
        base = root / parent
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            if (child / "INVARIANTS.yaml").exists() or (child / "domain" / "INVARIANTS.yaml").exists():
                packages.append(child)
    return packages


def domain_dir(pkg: Path) -> Path:
    """Full app instances keep domain artifacts under domain/; flat examples don't."""
    return pkg / "domain" if (pkg / "domain").is_dir() else pkg


def is_app_instance(pkg: Path) -> bool:
    return pkg.parts[-2] == "apps" if len(pkg.parts) >= 2 else False


# --------------------------------------------------------------------------- #
# Repo-wide checks
# --------------------------------------------------------------------------- #

def check_yaml_validity(root: Path, res: Result) -> None:
    for path in sorted(root.rglob("*.yaml")):
        if ".git" in path.parts:
            continue
        load_yaml(path, res)


def check_template_purity(root: Path, res: Result) -> None:
    # No _TEMPLATE files living inside examples/ or apps/.
    for parent in ("examples", "apps"):
        base = root / parent
        if base.is_dir():
            for path in base.rglob("*_TEMPLATE.*"):
                res.error(f"[PURITY] template file found outside templates: {path}")
    # No duplicate-copy filenames like "INVARIANTS (1).yaml" or "...copy.yaml".
    dup = re.compile(r"\(\d+\)|(?:^|[ _-])copy(?:[ _.-]|$)", re.IGNORECASE)
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts and dup.search(path.name):
            res.error(f"[PURITY] duplicate-copy filename: {path}")


def check_no_placeholders(packages: list[Path], res: Result) -> None:
    """Unresolved placeholders are a defect only inside a worked example or a real
    app package -- never in the deliberately-blank templates, and not in the repo's
    own docs (e.g. the checks file legitimately lists the words TBD/TODO)."""
    for pkg in packages:
        for path in pkg.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix.lower() not in (".md", ".yaml", ".yml"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for token in PLACEHOLDERS:
                if re.search(rf"\b{re.escape(token)}\b", text):
                    res.warn(f"[PLACEHOLDER] '{token}' in {path}")


# --------------------------------------------------------------------------- #
# Package checks
# --------------------------------------------------------------------------- #

REQUIRED_DOMAIN = [
    "DOMAIN_MODEL.md", "INVARIANTS.yaml", "DOMAIN_RULES.yaml",
    "STATE_MACHINES.yaml", "EVENT_MODEL.yaml", "OBSERVABILITY.md",
]
REQUIRED_ONBOARDING = ["RISK_POLICIES.yaml", "RBAC.yaml", "DATA_GOVERNANCE.yaml", "EVENTS.yaml"]
REQUIRED_APP_ROOT = ["TEST_PLAN.md", "IMPLEMENTATION_PLAN.md"]


def check_completeness(pkg: Path, res: Result) -> None:
    dom = domain_dir(pkg)
    for fname in REQUIRED_DOMAIN:
        if not (dom / fname).exists():
            res.error(f"[COMPLETE] {pkg.name}: missing required domain file {fname}")
    if is_app_instance(pkg):
        for fname in REQUIRED_ONBOARDING:
            if not (pkg / "onboarding" / fname).exists():
                res.error(f"[COMPLETE] {pkg.name}: missing onboarding/{fname}")
        for fname in REQUIRED_APP_ROOT:
            if not (pkg / fname).exists():
                res.error(f"[COMPLETE] {pkg.name}: missing {fname}")


def check_invariant_consistency(pkg: Path, res: Result) -> None:
    """The headline check: INVARIANTS.yaml and DOMAIN_RULES.yaml must agree on
    every invariant they both name. Enforcement and severity living in two files
    is how drift happens; this catches it."""
    dom = domain_dir(pkg)
    inv_blob = load_yaml(dom / "INVARIANTS.yaml", res)
    rules_blob = load_yaml(dom / "DOMAIN_RULES.yaml", res)
    inv = normalize_invariants(inv_blob)
    rules = normalize_invariants(rules_blob)
    if not inv or not rules:
        return

    only_inv = set(inv) - set(rules)
    only_rules = set(rules) - set(inv)
    for i in sorted(only_inv):
        res.error(f"[INV-DRIFT] {pkg.name}: {i} is in INVARIANTS.yaml but not DOMAIN_RULES.yaml")
    for i in sorted(only_rules):
        res.error(f"[INV-DRIFT] {pkg.name}: {i} is in DOMAIN_RULES.yaml but not INVARIANTS.yaml")

    # Fields that must match exactly where both files specify them.
    for i in sorted(set(inv) & set(rules)):
        for fieldname in ("on_violation", "enforced_at", "scope"):
            a = inv[i].get(fieldname)
            b = rules[i].get(fieldname)
            if a is not None and b is not None and str(a).strip() != str(b).strip():
                res.error(
                    f"[INV-DRIFT] {pkg.name}: {i} '{fieldname}' disagrees "
                    f"(INVARIANTS.yaml='{a}' vs DOMAIN_RULES.yaml='{b}')"
                )


def _emitted_events_from_state_machines(blob) -> set[str]:
    emitted: set[str] = set()
    if not isinstance(blob, dict):
        return emitted
    for ent in (blob.get("entities") or {}).values():
        if not isinstance(ent, dict):
            continue
        for tr in ent.get("transitions", []) or []:
            ev = tr.get("emits") if isinstance(tr, dict) else None
            if ev and str(ev).lower() != "null":
                emitted.add(str(ev))
    return emitted


def _trigger_events_from_state_machines(blob) -> set[str]:
    triggers: set[str] = set()
    if not isinstance(blob, dict):
        return triggers
    for ent in (blob.get("entities") or {}).values():
        if not isinstance(ent, dict):
            continue
        for tr in ent.get("transitions", []) or []:
            ev = tr.get("event") if isinstance(tr, dict) else None
            if ev:
                triggers.add(str(ev))
    return triggers


def _defined_events(pkg: Path, res: Result) -> set[str]:
    defined: set[str] = set()
    dom = domain_dir(pkg)
    em = load_yaml(dom / "EVENT_MODEL.yaml", res)
    if isinstance(em, dict) and isinstance(em.get("events"), dict):
        defined |= set(map(str, em["events"].keys()))
    onboarding_events = pkg / "onboarding" / "EVENTS.yaml"
    if onboarding_events.exists():
        ev = load_yaml(onboarding_events, res)
        if isinstance(ev, dict) and isinstance(ev.get("events"), dict):
            defined |= set(map(str, ev["events"].keys()))
    return defined


def check_event_consistency(pkg: Path, res: Result) -> None:
    sm = load_yaml(domain_dir(pkg) / "STATE_MACHINES.yaml", res)
    defined = _defined_events(pkg, res)
    if not defined:
        res.warn(f"[EVENTS] {pkg.name}: no events defined in EVENT_MODEL.yaml")
        return
    # Hard rule: anything actually emitted must be defined.
    for ev in sorted(_emitted_events_from_state_machines(sm) - defined):
        res.error(f"[EVENTS] {pkg.name}: emitted event '{ev}' is not defined in the event model")
    # Soft rule: transition triggers that aren't modeled yet (the example admits this).
    for ev in sorted(_trigger_events_from_state_machines(sm) - defined):
        res.warn(f"[EVENTS] {pkg.name}: transition trigger '{ev}' has no event-model entry yet")


def _authority_permissions(rules_blob) -> set[str]:
    perms: set[str] = set()
    if not isinstance(rules_blob, dict):
        return perms
    amap = rules_blob.get("authority_map") or {}
    if isinstance(amap, dict):
        for key, body in amap.items():
            perms.add(str(body.get("permission", key)) if isinstance(body, dict) else str(key))
    return perms


def check_seam_consistency(pkg: Path, res: Result) -> None:
    rules_blob = load_yaml(domain_dir(pkg) / "DOMAIN_RULES.yaml", res)
    perms = _authority_permissions(rules_blob)
    rbac_path = pkg / "onboarding" / "RBAC.yaml"
    if not rbac_path.exists():
        if perms:
            res.warn(f"[SEAM] {pkg.name}: authority_map defines {len(perms)} permission(s) "
                     f"but no onboarding/RBAC.yaml is present to verify them against")
        return
    rbac = load_yaml(rbac_path, res)
    declared = set((rbac or {}).get("permissions", {}).keys()) if isinstance(rbac, dict) else set()
    for p in sorted(perms - set(map(str, declared))):
        res.error(f"[SEAM] {pkg.name}: authority_map permission '{p}' is not declared in RBAC.yaml")


def check_invariant_observability(pkg: Path, res: Result) -> None:
    dom = domain_dir(pkg)
    inv = normalize_invariants(load_yaml(dom / "INVARIANTS.yaml", res))
    obs_path = dom / "OBSERVABILITY.md"
    if not obs_path.exists():
        res.error(f"[OBSERVE] {pkg.name}: OBSERVABILITY.md missing")
        return
    obs_text = obs_path.read_text(encoding="utf-8")
    for inv_id, body in inv.items():
        metric = str(body.get("observable_as", "")).strip()
        seen = (inv_id in obs_text) or (metric and metric in obs_text)
        if not seen:
            res.error(f"[OBSERVE] {pkg.name}: {inv_id} has no metric/entry in OBSERVABILITY.md")
            continue
        if str(body.get("severity", "")).lower() == "critical":
            # Critical invariants must have alerting somewhere near their mention.
            if "critical" not in obs_text.lower():
                res.warn(f"[OBSERVE] {pkg.name}: {inv_id} is critical but no 'Critical' alert found")


def check_data_governance(pkg: Path, res: Result) -> None:
    """Only meaningful for full app instances; the worked example has no onboarding."""
    if not is_app_instance(pkg):
        return
    gov_path = pkg / "onboarding" / "DATA_GOVERNANCE.yaml"
    if not gov_path.exists():
        res.error(f"[GOVERN] {pkg.name}: onboarding/DATA_GOVERNANCE.yaml missing")
        return
    gov = load_yaml(gov_path, res)
    if not (isinstance(gov, dict) and gov.get("fields")):
        res.warn(f"[GOVERN] {pkg.name}: DATA_GOVERNANCE.yaml has no field entries")


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def run(root: Path, only_package: str | None) -> Result:
    res = Result()

    # Repo-wide gates
    check_yaml_validity(root, res)
    check_template_purity(root, res)

    packages = discover_packages(root)
    if only_package:
        packages = [p for p in packages if p.name == only_package or str(p).endswith(only_package)]
        if not packages:
            res.error(f"[CONFIG] no package matched '{only_package}'")

    check_no_placeholders(packages, res)

    if not packages:
        res.warn("[CONFIG] no app/example packages found to validate (apps/ is empty so far)")

    for pkg in packages:
        check_completeness(pkg, res)
        check_invariant_consistency(pkg, res)
        check_event_consistency(pkg, res)
        check_seam_consistency(pkg, res)
        check_invariant_observability(pkg, res)
        check_data_governance(pkg, res)

    return res, packages


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an app constitution package.")
    ap.add_argument("--root", default=".", help="repo root (default: current dir)")
    ap.add_argument("--package", default=None, help="validate only this package (name or path suffix)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    res, packages = run(root, args.package)

    print("=" * 64)
    print("  APP CONSTITUTION VALIDATOR")
    print(f"  root: {root}")
    print(f"  packages checked: {', '.join(p.name for p in packages) or '(none)'}")
    print("=" * 64)

    if res.warnings:
        print(f"\nWARNINGS ({len(res.warnings)}):")
        for w in res.warnings:
            print(f"  ! {w}")

    if res.errors:
        print(f"\nERRORS ({len(res.errors)}):")
        for e in res.errors:
            print(f"  x {e}")

    print()
    failed = bool(res.errors) or (args.strict and bool(res.warnings))
    if failed:
        print("RESULT: GATE CLOSED — do not generate code until these are resolved.")
        return 1
    print("RESULT: GATE OPEN — all required checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
