"""Deterministic S8 security / boundary policy engine.

LLM may assist in later phases; for v1 the policy engine alone decides
ALLOW / DENY / ESCALATE findings that become S8 violations.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

_CONFIG_PATH = Path(__file__).resolve().parent / "policy_config.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "allowed_domains": ["saucedemo.com", "reqres.in"],
    "allowed_host_suffixes": [".saucedemo.com", ".reqres.in"],
    "blocked_host_patterns": ["prod.", "production."],
    "blocked_pii_field_names": ["ssn", "credit_card", "cvv"],
    "destructive_action_types": ["delete", "drop", "truncate", "destroy", "purge"],
    "routing_target": "security/release-owner",
}


def load_policy_config(path: Optional[Path] = None) -> dict[str, Any]:
    cfg_path = path or _CONFIG_PATH
    if not cfg_path.exists():
        return dict(_DEFAULT_CONFIG)
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    merged = dict(_DEFAULT_CONFIG)
    merged.update(data)
    return merged


def scan_boundaries(
    *,
    run_id: str,
    s5_output: Optional[dict[str, Any]] = None,
    s6_output: Optional[dict[str, Any]] = None,
    compiled_specs: Optional[dict[str, Any]] = None,
    config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    cfg = config or load_policy_config()
    routing = str(cfg.get("routing_target") or "security/release-owner")
    violations: list[dict[str, str]] = []

    actions = _collect_actions(s5_output)
    for extra in (compiled_specs or {}).get("s5_models") or []:
        if extra is s5_output or extra == s5_output:
            continue
        actions.extend(_collect_actions(extra))
    for action in actions:
        violations.extend(_scan_action(action, cfg, routing))

    # Scan string payloads in S5 / compiled source for blocked PII field names.
    blob_parts = [json.dumps(s5_output or {}), json.dumps(compiled_specs or {})]
    if s6_output:
        blob_parts.append(json.dumps(s6_output.get("environment_metadata") or {}))
        for item in s6_output.get("evidence_manifest") or []:
            blob_parts.append(str(item.get("storage_uri", "")))
    blob = "\n".join(blob_parts).lower()

    for field in cfg.get("blocked_pii_field_names") or []:
        token = str(field).lower()
        if re.search(rf"\b{re.escape(token)}\b", blob):
            violations.append(
                {
                    "action": f"pii_field_reference:{token}",
                    "source": "s5/s6_payload_scan",
                    "severity": "escalate",
                    "routing_target": routing,
                    "detail": f"Blocked PII field name '{token}' appeared in scanned payloads or evidence paths.",
                }
            )

    # Deduplicate by (action, source, detail)
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, str]] = []
    for v in violations:
        key = (v["action"], v["source"], v["detail"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)

    clean = (
        "No security or boundary violations detected in scanned S5/S6 actions for this run."
        if not unique
        else ""
    )
    return {"run_id": run_id, "violations": unique, "clean_confirmation": clean}


def _collect_actions(s5_output: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    if not s5_output:
        return []
    model = s5_output.get("automation_model") or {}
    actions: list[dict[str, Any]] = []
    for key in ("setup", "actions", "assertions", "teardown"):
        for step in model.get(key) or []:
            if isinstance(step, dict):
                enriched = dict(step)
                enriched["_section"] = key
                actions.append(enriched)
    return actions


def _scan_action(action: dict[str, Any], cfg: dict[str, Any], routing: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    action_type = str(action.get("type") or "").lower()
    source = f"s5.automation_model.{action.get('_section', 'actions')}"

    destructive = {str(x).lower() for x in (cfg.get("destructive_action_types") or [])}
    if action_type in destructive:
        found.append(
            {
                "action": action_type,
                "source": source,
                "severity": "deny",
                "routing_target": routing,
                "detail": f"Destructive action type '{action_type}' is prohibited.",
            }
        )

    for url_key in ("target", "url", "href", "endpoint"):
        raw = action.get(url_key)
        if not isinstance(raw, str) or not raw:
            continue
        host = _extract_host(raw)
        if not host:
            # Relative path (e.g. "/") — allowed under configured demo base.
            continue
        if _is_blocked_host(host, cfg):
            found.append(
                {
                    "action": f"navigate:{raw}",
                    "source": source,
                    "severity": "deny",
                    "routing_target": routing,
                    "detail": f"Host '{host}' matches a blocked production/out-of-scope pattern.",
                }
            )
        elif not _is_allowed_host(host, cfg):
            found.append(
                {
                    "action": f"navigate:{raw}",
                    "source": source,
                    "severity": "escalate",
                    "routing_target": routing,
                    "detail": f"Host '{host}' is outside the configured allowed domain list.",
                }
            )
    return found


def _extract_host(value: str) -> Optional[str]:
    """Return a hostname only for absolute/bare http(s) URLs — never CSS selectors."""
    text = value.strip()
    if not text:
        return None
    # Locators / relative paths are not hosts.
    if text.startswith(("/", ".", "#", "[", "'", '"')):
        return None
    if "://" not in text:
        # Bare host or host/path (e.g. www.saucedemo.com/inventory.html)
        if not re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/.*)?$", text):
            return None
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    return host or None


def _is_blocked_host(host: str, cfg: dict[str, Any]) -> bool:
    lowered = host.lower()
    for pattern in cfg.get("blocked_host_patterns") or []:
        if str(pattern).lower() in lowered:
            return True
    return False


def _is_allowed_host(host: str, cfg: dict[str, Any]) -> bool:
    lowered = host.lower()
    for domain in cfg.get("allowed_domains") or []:
        d = str(domain).lower()
        if lowered == d:
            return True
    for suffix in cfg.get("allowed_host_suffixes") or []:
        if lowered.endswith(str(suffix).lower()):
            return True
    return False
