"""Manual smoke script: drives one run through
S1->S2->H1->S3->S4->H2->S5->H3->S6->S7->S8->S9->H4->S10->H5->S11,
auto-approving every gate, against real Postgres + the LLM Gateway mock provider.

Prereqs: infra docker compose up, LLM Gateway running on :8000 (LLM_PROVIDER=mock).

Run with:
    cd orchestrator
    ..\\.venv\\Scripts\\python.exe scripts\\smoke_run.py
"""
import json
import os
import sys
from pathlib import Path

# Offline smoke: keep S6 on gateway mock (real Playwright is S6_EXECUTION_MODE=playwright).
os.environ.setdefault("S6_EXECUTION_MODE", "mock")
os.environ.setdefault("CI_GATE_MODE", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runner import approve_gate_and_resume, start_run  # noqa: E402


def main() -> None:
    print("Starting run...")
    result = start_run({"raw": "Demo BRD: users must be able to log in with a valid username and password and reach the dashboard."})
    run_id = result["run_id"]
    print(f"run_id={run_id} next={result['next']}")
    assert result["next"] == ["s3"], f"expected to pause before s3 (H1), got {result['next']}"

    print("\nApproving H1...")
    result = approve_gate_and_resume(run_id, "H1", reviewer="qa-lead")
    print(f"next={result['next']}")
    assert result["next"] == ["s5"], f"expected to pause before s5 (H2), got {result['next']}"

    print("\nApproving H2...")
    result = approve_gate_and_resume(run_id, "H2", reviewer="qa-lead")
    print(f"next={result['next']}")
    assert result["next"] == ["s6"], f"expected to pause before s6 (H3), got {result['next']}"

    print("\nApproving H3...")
    result = approve_gate_and_resume(run_id, "H3", reviewer="qa-engineer")
    print(f"next={result['next']}")
    assert result["next"] == ["s10"], f"expected to pause before s10 (H4), got {result['next']}"

    s9 = result["state"].get("s9_output")
    print("\nS9 report:")
    print(json.dumps(s9, indent=2))

    print("\nApproving H4...")
    result = approve_gate_and_resume(run_id, "H4", reviewer="qa-lead")
    print(f"next={result['next']}")
    assert result["next"] == ["s11"], f"expected to pause before s11 (H5), got {result['next']}"

    s10 = result["state"].get("s10_output")
    print("\nS10 release summary:")
    print(json.dumps(s10, indent=2))

    print("\nApproving H5...")
    result = approve_gate_and_resume(run_id, "H5", reviewer="release-owner")
    print(f"next={result['next']}")
    assert result["next"] == [], f"expected run to complete, got {result['next']}"

    s11 = result["state"].get("s11_output")
    print("\nS11 CI gate:")
    print(json.dumps(s11, indent=2))

    print("\nSmoke OK.")


if __name__ == "__main__":
    main()
