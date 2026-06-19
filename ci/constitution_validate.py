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
                    # checks.md #9: a package carrying unresolved domain logic
                    # "may not proceed" -- this is a gate failure, not a nit.
                    res.error(f"[PLACEHOLDER] '{token}' in {path}")


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
    # A constitution with no invariants is not a spec the gate can vouch for.
    if not inv:
        res.error(f"[INV-DRIFT] {pkg.name}: INVARIANTS.yaml declares no invariants")
    if not rules:
        res.error(f"[INV-DRIFT] {pkg.name}: DOMAIN_RULES.yaml declares no invariants")
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


def _declared_triggers(pkg: Path, res: Result) -> set[str]:
    """Triggers live in their OWN namespace, separate from events. A trigger is the
    command/cause that drives a transition; it does not have to emit an event. They
    are declared under `triggers:` in EVENT_MODEL.yaml (and optionally onboarding/
    EVENTS.yaml), as either a map {name: {...}} or a list."""
    declared: set[str] = set()

    def absorb(blob) -> None:
        trig = blob.get("triggers") if isinstance(blob, dict) else None
        if isinstance(trig, dict):
            declared.update(map(str, trig.keys()))
        elif isinstance(trig, list):
            for t in trig:
                if isinstance(t, dict) and t.get("name"):
                    declared.add(str(t["name"]))
                elif isinstance(t, str):
                    declared.add(t)

    absorb(load_yaml(domain_dir(pkg) / "EVENT_MODEL.yaml", res))
    onboarding_events = pkg / "onboarding" / "EVENTS.yaml"
    if onboarding_events.exists():
        absorb(load_yaml(onboarding_events, res))
    return declared


def check_event_consistency(pkg: Path, res: Result) -> None:
    """Triggers and events are SEPARATE namespaces (the constitution's trigger/event
    separation). A transition's `event:` is the trigger that fires it; its `emits:`
    is the event it produces -- which may legitimately be null. So:
      * every `emits:` value must be a defined event  (events: in EVENT_MODEL.yaml)
      * every transition `event:` must be a declared trigger  (triggers: there)
    A trigger that emits null is valid and must never warn; a trigger is NOT
    required to have a matching events: entry."""
    sm = load_yaml(domain_dir(pkg) / "STATE_MACHINES.yaml", res)
    defined = _defined_events(pkg, res)
    declared = _declared_triggers(pkg, res)
    emitted = _emitted_events_from_state_machines(sm)       # already excludes null
    triggers = _trigger_events_from_state_machines(sm)

    # An empty event model / triggerless state machine is not a passing spec.
    if not defined:
        res.error(f"[EVENTS] {pkg.name}: no events defined in EVENT_MODEL.yaml")
    if not triggers:
        res.error(f"[EVENTS] {pkg.name}: no transition triggers declared in STATE_MACHINES.yaml")

    # Hard rule: every emitted event must be defined in the event model.
    for ev in sorted(emitted - defined):
        res.error(f"[EVENTS] {pkg.name}: emitted event '{ev}' is not defined in EVENT_MODEL.yaml events:")

    # Hard rule: every transition trigger must be declared in the trigger namespace.
    # (This is the "undeclared trigger" gate -- emitting null does not exempt it.)
    for ev in sorted(triggers - declared):
        res.error(f"[EVENTS] {pkg.name}: transition trigger '{ev}' is not declared in EVENT_MODEL.yaml triggers:")


def _authority_permissions(rules_blob) -> set[str]:
    perms: set[str] = set()
    if not isinstance(rules_blob, dict):
        return perms
    amap = rules_blob.get("authority_map") or {}
    if isinstance(amap, dict):
        for key, body in amap.items():
            perms.add(str(body.get("permission", key)) if isinstance(body, dict) else str(key))
    return perms


def _rbac_path(pkg: Path) -> Path:
    """App instances keep RBAC under onboarding/; flat worked examples keep it
    beside the domain artifacts (they have no onboarding/ dir). The old code only
    ever looked under onboarding/, so a flat example's RBAC was never found and
    its authority_map went perpetually unverified."""
    if is_app_instance(pkg):
        return pkg / "onboarding" / "RBAC.yaml"
    return domain_dir(pkg) / "RBAC.yaml"


def _authority_tiers(rules_blob) -> dict[str, str]:
    """permission -> min_tier as declared in authority_map (when present)."""
    tiers: dict[str, str] = {}
    amap = rules_blob.get("authority_map") if isinstance(rules_blob, dict) else None
    if isinstance(amap, dict):
        for key, body in amap.items():
            if isinstance(body, dict) and body.get("min_tier") is not None:
                perm = str(body.get("permission", key))
                tiers[perm] = str(body["min_tier"]).strip()
    return tiers


def _rbac_tiers(rbac) -> dict[str, str]:
    """permission -> declared tier in RBAC.yaml (min_tier, or tier as a fallback)."""
    tiers: dict[str, str] = {}
    perms = rbac.get("permissions") if isinstance(rbac, dict) else None
    if isinstance(perms, dict):
        for perm, body in perms.items():
            if isinstance(body, dict):
                t = body.get("min_tier", body.get("tier"))
                if t is not None:
                    tiers[str(perm)] = str(t).strip()
    return tiers


def _domain_vocabulary(pkg: Path, res: Result) -> set[str]:
    """Tokens that belong exclusively to the domain: entity names, invariant ids,
    and state-machine state names. Derived from DOMAIN_MODEL.md, INVARIANTS.yaml,
    and STATE_MACHINES.yaml so nothing is hardcoded -- onboarding referencing any
    of these would be a domain dependency (constitution principle #5)."""
    dom = domain_dir(pkg)
    vocab: set[str] = set(_modeled_entities(dom).keys())
    vocab |= set(normalize_invariants(load_yaml(dom / "INVARIANTS.yaml", res)).keys())
    sm = load_yaml(dom / "STATE_MACHINES.yaml", res)
    if isinstance(sm, dict):
        for ent in (sm.get("entities") or {}).values():
            if isinstance(ent, dict):
                for st in ent.get("states") or []:
                    vocab.add(str(st))
    vocab.discard("")
    return vocab


def _iter_yaml_strings(obj):
    """Yield every mapping key and scalar string in a parsed YAML structure.
    Working from the parsed tree (not raw text) means comments -- which may
    legitimately mention the domain in prose -- are not flagged; only actual data
    references are."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from _iter_yaml_strings(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_yaml_strings(item)
    elif isinstance(obj, str):
        yield obj


def _declared_event_trigger_names(blob) -> set[str]:
    """The key names declared under an onboarding EVENTS.yaml's own `events:` and
    `triggers:` maps. Onboarding owns its event/trigger vocabulary, and event names
    (e.g. exception_resolved, period_closed) legitimately collide with
    state-machine state names -- so these names are exempt from the domain-token
    match in that file. Only the declaration KEYS are exempt; their values are
    still scanned, so a domain entity smuggled into a payload is still caught."""
    names: set[str] = set()
    if not isinstance(blob, dict):
        return names
    for section in ("events", "triggers"):
        sec = blob.get(section)
        if isinstance(sec, dict):
            names |= set(map(str, sec.keys()))
        elif isinstance(sec, list):
            for item in sec:
                if isinstance(item, dict) and item.get("name"):
                    names.add(str(item["name"]))
                elif isinstance(item, str):
                    names.add(item)
    return names


def _check_seam_direction(pkg: Path, res: Result) -> None:
    """Constitution principle #5: the domain may read onboarding context, but
    onboarding must never depend on the domain. Flag any onboarding/*.yaml whose
    data references a domain entity, invariant id, or state name."""
    onboarding = pkg / "onboarding"
    if not onboarding.is_dir():
        return
    vocab = _domain_vocabulary(pkg, res)
    if not vocab:
        return
    for path in sorted(onboarding.glob("*.yaml")):
        blob = load_yaml(path, res)
        # onboarding/EVENTS.yaml declares its own events/triggers; their names may
        # legitimately collide with domain state names. Drop just those declared
        # names from this file's vocabulary -- values are still fully scanned.
        file_vocab = vocab
        if path.name == "EVENTS.yaml":
            file_vocab = vocab - _declared_event_trigger_names(blob)
        if not file_vocab:
            continue
        patterns = {term: re.compile(rf"\b{re.escape(term)}\b") for term in file_vocab}
        hits = {term for s in _iter_yaml_strings(blob)
                for term, pat in patterns.items() if pat.search(s)}
        for term in sorted(hits):
            res.error(f"[SEAM] {pkg.name}: onboarding/{path.name} references domain "
                      f"token '{term}' -- onboarding must not depend on the domain (principle #5)")


def check_seam_consistency(pkg: Path, res: Result) -> None:
    rules_blob = load_yaml(domain_dir(pkg) / "DOMAIN_RULES.yaml", res)
    perms = _authority_permissions(rules_blob)

    # Rule 2 (direction): independent of RBAC, so always check it.
    _check_seam_direction(pkg, res)

    rbac_path = _rbac_path(pkg)
    if not rbac_path.exists():
        if perms:
            res.warn(f"[SEAM] {pkg.name}: authority_map defines {len(perms)} permission(s) "
                     f"but no {rbac_path.name} is present to verify them against")
        return
    rbac = load_yaml(rbac_path, res)
    declared = set((rbac or {}).get("permissions", {}).keys()) if isinstance(rbac, dict) else set()
    for p in sorted(perms - set(map(str, declared))):
        res.error(f"[SEAM] {pkg.name}: authority_map permission '{p}' is not declared in RBAC.yaml")

    # Rule 1 (tier alignment): where both files give a tier for the same
    # permission, they must agree -- otherwise the gate enforces a tier the domain
    # never intended.
    a_tiers = _authority_tiers(rules_blob)
    r_tiers = _rbac_tiers(rbac)
    for perm in sorted(set(a_tiers) & set(r_tiers)):
        if a_tiers[perm] != r_tiers[perm]:
            res.error(f"[SEAM] {pkg.name}: tier mismatch for permission '{perm}' "
                      f"(authority_map min_tier={a_tiers[perm]} vs RBAC.yaml min_tier={r_tiers[perm]})")


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


# A field/entity is "governed" when the package declares it carries data in one of
# these classes. Tenancy is the org_id-bearing case; the rest are PII-shaped.
GOVERNED_CLASSES = ("personal", "sensitive", "regulated", "tenant")
# Minimum a governance entry must answer for a declared-sensitive field.
REQUIRED_GOV_KEYS = ("classification", "purpose", "retention")


def _governance_path(pkg: Path) -> Path:
    """App instances keep governance under onboarding/ (the seam owns data policy);
    flat worked examples keep it beside the domain artifacts."""
    if is_app_instance(pkg):
        return pkg / "onboarding" / "DATA_GOVERNANCE.yaml"
    return domain_dir(pkg) / "DATA_GOVERNANCE.yaml"


def _data_field_declarations(pkg: Path, res: Result) -> tuple[list[dict], list[str]]:
    """Read the optional `data_fields:` block from DOMAIN_RULES.yaml.

    Convention (see ci/constitution-checks.md #7):
        data_fields:
          sensitive_fields:
            - field: Entity.attribute
              classification: personal | sensitive | regulated
          tenant_scoped_entities:
            - Entity            # an entity that carries org_id

    Returns (sensitive_fields, tenant_scoped_entities)."""
    rules = load_yaml(domain_dir(pkg) / "DOMAIN_RULES.yaml", res)
    decl = rules.get("data_fields") if isinstance(rules, dict) else None
    sensitive: list[dict] = []
    tenant: list[str] = []
    if isinstance(decl, dict):
        for item in decl.get("sensitive_fields") or []:
            if isinstance(item, dict) and item.get("field"):
                sensitive.append(item)
        for ent in decl.get("tenant_scoped_entities") or []:
            tenant.append(str(ent))
    return sensitive, tenant


def _modeled_entities(dom: Path) -> dict[str, bool | None]:
    """Parse DOMAIN_MODEL.md's Entities section for the entity universe.

    Every `### <Name>` heading under the `## ... Entities` heading is a modeled
    entity. Its `Tenancy:` tag (when present) is captured as True (yes) / False
    (no) / None (unstated). The header name is normalized: '### Adjustment
    (journal entry)' -> 'Adjustment'. This is the SOURCE OF TRUTH for which
    entities exist; a hand-authored list is only ever cross-checked against it."""
    path = dom / "DOMAIN_MODEL.md"
    out: dict[str, bool | None] = {}
    if not path.exists():
        return out
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return out

    in_entities = False
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current, buf
        if current is not None:
            block = "\n".join(buf)
            m = re.search(r"Tenancy.*?\b(yes|no)\b", block, re.IGNORECASE | re.DOTALL)
            out[current] = (m.group(1).lower() == "yes") if m else None
        current, buf = None, []

    for line in text.splitlines():
        if re.match(r"##\s+", line):                 # a `## ` section heading
            flush()
            in_entities = "entit" in line.lower()
            continue
        h3 = re.match(r"###\s+(.*)", line)
        if h3:
            flush()
            if in_entities:
                name = re.sub(r"[`*]", "", h3.group(1).split("(")[0]).strip()
                current = name or None
            continue
        if current is not None:
            buf.append(line)
    flush()
    return out


def _tenancy_is_universal(pkg: Path, res: Result) -> bool:
    """True when any invariant has scope `all` (e.g. INV-8: 'every entity carries
    org_id'). In that case every modeled entity is tenant-scoped, regardless of
    its own Tenancy tag."""
    dom = domain_dir(pkg)
    for fname in ("INVARIANTS.yaml", "DOMAIN_RULES.yaml"):
        for body in normalize_invariants(load_yaml(dom / fname, res)).values():
            if str(body.get("scope", "")).strip().lower() == "all":
                return True
    return False


def check_data_governance(pkg: Path, res: Result) -> None:
    """Coverage, not mere presence. Every field the package declares as
    personal/sensitive/regulated must carry a complete DATA_GOVERNANCE.yaml entry
    (classification + purpose + retention), and every org_id-bearing entity must
    carry a tenancy governance note. A governance file that merely exists proves
    nothing about whether the protected data is actually accounted for.

    The tenant-entity universe is DERIVED from DOMAIN_MODEL.md (plus INV-8-style
    scope:all), not trusted from the hand-authored data_fields list -- that list
    is folded in as an additional check target so it can't go stale silently."""
    sensitive, tenant_hand = _data_field_declarations(pkg, res)

    # Derive the set of entities that require a tenancy note.
    modeled = _modeled_entities(domain_dir(pkg))
    universal = _tenancy_is_universal(pkg, res)
    tenant_required: set[str] = set(tenant_hand)
    for name, tenancy in modeled.items():
        if universal or tenancy is True:
            tenant_required.add(name)

    # Nothing protected -> nothing to cross-check. App instances handling real
    # users almost always have protected data, so flag the silence there.
    if not sensitive and not tenant_required:
        if is_app_instance(pkg):
            res.warn(f"[GOVERN] {pkg.name}: no sensitive fields or tenant-scoped entities "
                     f"found -- confirm the app truly handles no personal/tenant data")
        return

    gov_path = _governance_path(pkg)
    if not gov_path.exists():
        res.error(f"[GOVERN] {pkg.name}: package has governed data "
                  f"({len(sensitive)} sensitive field(s), {len(tenant_required)} tenant-scoped "
                  f"entity(ies)) but {gov_path.name} is missing")
        return

    gov = load_yaml(gov_path, res)
    fields = gov.get("fields") if isinstance(gov, dict) else None
    entities = gov.get("entities") if isinstance(gov, dict) else None
    fields = fields if isinstance(fields, dict) else {}
    entities = entities if isinstance(entities, dict) else {}

    # (a) Every declared-sensitive field needs a complete governance entry.
    for item in sensitive:
        name = str(item["field"])
        entry = fields.get(name)
        if not isinstance(entry, dict):
            cls = item.get("classification", "sensitive")
            res.error(f"[GOVERN] {pkg.name}: field '{name}' is declared {cls} "
                      f"but has no entry in {gov_path.name}")
            continue
        missing = [k for k in REQUIRED_GOV_KEYS if not str(entry.get(k, "")).strip()]
        if missing:
            res.error(f"[GOVERN] {pkg.name}: governance entry for '{name}' is "
                      f"missing {', '.join(missing)}")

    # (b) Every tenant-scoped (org_id-bearing) entity needs a governance note.
    #     tenant_required is derived from DOMAIN_MODEL.md, so a new entity added
    #     there is caught even if nobody updated data_fields.tenant_scoped_entities.
    for ent in sorted(tenant_required):
        note = entities.get(ent)
        has_note = isinstance(note, dict) and bool(str(note.get("note", "")).strip())
        # An explicit per-field org_id entry counts as covering tenancy too.
        has_field = isinstance(fields.get(f"{ent}.org_id"), dict)
        if not has_note and not has_field:
            res.error(f"[GOVERN] {pkg.name}: tenant-scoped entity '{ent}' (org_id) "
                      f"has no governance note in {gov_path.name}")


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
