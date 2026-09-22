"""GOLDEN-02: local LLM through H3, real Playwright S6 against bad host → fail → H4."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["S6_EXECUTION_MODE"] = "playwright"
os.environ.setdefault("CI_GATE_MODE", "mock")
os.environ.setdefault("LLM_GATEWAY_TIMEOUT_SECONDS", "600")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.runner import approve_gate_and_resume, start_run  # noqa: E402


def main() -> None:
    print("Starting GOLDEN-02 (S6=playwright, bad host)...", flush=True)
    raw = (
        "UR-FAIL: Users must log in to https://this-host-does-not-exist.invalid "
        "with standard_user / secret_sauce and see the inventory list."
    )
    result = start_run(
        {
            "raw": raw,
            "base_url": "https://this-host-does-not-exist.invalid",
            "environment": "test",
        }
    )
    run_id = result["run_id"]
    print(f"run_id={run_id} next={result.get('next')}", flush=True)

    for gate in ("H1", "H2", "H3"):
        print(f"Approving {gate}...", flush=True)
        result = approve_gate_and_resume(run_id, gate, reviewer="qa-lead", comment=f"GOLDEN-02 {gate}")
        print(f"  next={result.get('next')}", flush=True)

    run = db.get_run(run_id)
    print(
        f"AFTER_H3 status={run['status']} stage={run['current_stage']}",
        flush=True,
    )

    # Continue H4/H5 so S11 reflects failure-aware gate outcome
    for gate in ("H4", "H5"):
        if run["current_stage"] == f"{gate}_pending" or (
            run.get("pending_gate") == gate if hasattr(run, "get") else False
        ):
            pass
        run = db.get_run(run_id)
        if run["current_stage"] != f"{gate}_pending":
            print(f"Skip {gate}: stage={run['current_stage']}", flush=True)
            continue
        print(f"Approving {gate}...", flush=True)
        result = approve_gate_and_resume(run_id, gate, reviewer="qa-lead", comment=f"GOLDEN-02 {gate}")
        print(f"  next={result.get('next')}", flush=True)
        run = db.get_run(run_id)

    run = db.get_run(run_id)
    s6 = result.get("state", {}).get("s6_output") if isinstance(result, dict) else None
    s7 = result.get("state", {}).get("s7_output") if isinstance(result, dict) else None
    s11 = result.get("state", {}).get("s11_output") if isinstance(result, dict) else None
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": run["status"],
                "stage": run["current_stage"],
                "s6_results": (s6 or {}).get("results") if isinstance(s6, dict) else None,
                "s7_keys": list(s7.keys()) if isinstance(s7, dict) else None,
                "s11": s11,
            }
        ),
        flush=True,
    )
    print("GOLDEN02_DONE", flush=True)


if __name__ == "__main__":
    main()
