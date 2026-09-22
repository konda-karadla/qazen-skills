"""Ollama-backed e2e through H1-H5 (S6 mock for speed).

Prereqs:
  - Ollama running with qwen2.5:7b
  - LLM Gateway on LLM_GATEWAY_URL with LLM_PROFILE=ollama
    (repo-root .env; do not set LLM_PROVIDER=mock on the gateway process)
  - Postgres up; S6_EXECUTION_MODE=mock (default here); CI_GATE_MODE=mock

Switch to cloud OpenAI later: LLM_PROFILE=openai + OPENAI_API_KEY in .env, restart gateway.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("S6_EXECUTION_MODE", "mock")
os.environ.setdefault("CI_GATE_MODE", "mock")
os.environ.setdefault("LLM_GATEWAY_TIMEOUT_SECONDS", "600")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runner import approve_gate_and_resume, start_run  # noqa: E402


def main() -> None:
    print("Starting Ollama e2e (S6=mock)...", flush=True)
    raw = (
        "UR-1: Users must log in to https://www.saucedemo.com with "
        "standard_user / secret_sauce and see the inventory list."
    )
    result = start_run({"raw": raw})
    run_id = result["run_id"]
    print(f"run_id={run_id} next={result['next']}", flush=True)
    assert result["next"] == ["s3"]

    for gate, expect in [
        ("H1", ["s5"]),
        ("H2", ["s6"]),
        ("H3", ["s10"]),
        ("H4", ["s11"]),
        ("H5", []),
    ]:
        print(f"Approving {gate}...", flush=True)
        result = approve_gate_and_resume(run_id, gate, reviewer="qa-lead")
        print(f"  next={result['next']}", flush=True)
        assert result["next"] == expect, (gate, result["next"])
        if gate == "H3":
            s9 = result["state"]["s9_output"]
            print(f"  S9={json.dumps(s9['aggregate_metrics'])}", flush=True)
        if gate == "H4":
            s10 = result["state"]["s10_output"]
            print(f"  S10 passed={s10['pass_fail_summary']['passed']}", flush=True)
        if gate == "H5":
            s11 = result["state"]["s11_output"]
            print(f"  S11 status_pushed={s11['status_pushed']}", flush=True)

    print("OLLAMA_E2E_OK", flush=True)


if __name__ == "__main__":
    main()
