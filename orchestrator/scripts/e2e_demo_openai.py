"""Optional e2e: OpenAI + demo BRD through H1-H5 with real Playwright S6.

Does not print secrets. Requires:
  - Postgres up
  - LLM Gateway with LLM_PROVIDER=openai (default URL below)
  - Playwright browsers installed under playwright/
  - MinIO optional (upload failure falls back to local://)

Run:
  cd orchestrator
  $env:DATABASE_URL = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
  $env:LLM_GATEWAY_URL = "http://127.0.0.1:8011"
  $env:S6_EXECUTION_MODE = "playwright"
  ..\\.venv\\Scripts\\python.exe scripts\\e2e_demo_openai.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("S6_EXECUTION_MODE", "playwright")
os.environ.setdefault("CI_GATE_MODE", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runner import approve_gate_and_resume, start_run  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
BRD_PATH = REPO / "examples" / "demo-brd" / "brd.md"


def main() -> None:
    brd = BRD_PATH.read_text(encoding="utf-8")
    print(f"Starting OpenAI+Playwright e2e from {BRD_PATH.name} ({len(brd)} chars)...")
    result = start_run({"raw": brd, "source": "examples/demo-brd/brd.md"})
    run_id = result["run_id"]
    print(f"run_id={run_id} next={result['next']}")
    assert result["next"] == ["s3"], result["next"]

    for gate, reviewer, expect in [
        ("H1", "qa-lead", ["s5"]),
        ("H2", "qa-lead", ["s6"]),
        ("H3", "qa-engineer", ["s10"]),
        ("H4", "qa-lead", ["s11"]),
        ("H5", "release-owner", []),
    ]:
        print(f"Approving {gate}...")
        result = approve_gate_and_resume(run_id, gate, reviewer=reviewer)
        print(f"  next={result['next']}")
        assert result["next"] == expect, f"after {gate}: expected {expect}, got {result['next']}"
        if gate == "H3":
            s9 = result["state"].get("s9_output") or {}
            metrics = s9.get("aggregate_metrics") or {}
            print(f"  S9 metrics: {json.dumps(metrics)}")
            summary = (s9.get("human_readable_summary") or "")[:500]
            print(f"  S9 summary (truncated):\n{summary}")
            s8 = result["state"].get("s8_output") or {}
            print(f"  S8 violations: {len(s8.get('violations') or [])}")
        if gate == "H4":
            s10 = result["state"].get("s10_output") or {}
            print(f"  S10 app_bugs: {len(s10.get('outstanding_app_bugs') or [])}")
        if gate == "H5":
            s11 = result["state"].get("s11_output") or {}
            print(f"  S11 status_pushed: {s11.get('status_pushed')}")

    print("E2E OK — completed through H5.")


if __name__ == "__main__":
    main()
