"""Approve H3 with Playwright against an invalid host to force S6 failure (GOLDEN-02 salvage)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["S6_EXECUTION_MODE"] = "playwright"
os.environ["CI_GATE_MODE"] = "mock"
os.environ["QAZEN_BASE_URL"] = "https://this-host-does-not-exist.invalid"
os.environ.setdefault("LLM_GATEWAY_TIMEOUT_SECONDS", "600")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.runner import approve_gate_and_resume  # noqa: E402

RID = "5e13da19-55bd-4ea1-8e37-3f9f03800ed4"


def main() -> None:
    r = db.get_run(RID)
    print("before", r["status"], r["current_stage"], flush=True)
    if r["current_stage"] != "H3_pending":
        print("SKIP not at H3_pending", flush=True)
        return
    out = approve_gate_and_resume(RID, "H3", reviewer="qa-lead", comment="GOLDEN-02 force fail host")
    print("next", out.get("next"), flush=True)
    r = db.get_run(RID)
    print("after", r["status"], r["current_stage"], flush=True)
    s6 = (out.get("state") or {}).get("s6_output")
    s7 = (out.get("state") or {}).get("s7_output")
    if isinstance(s6, dict):
        print("s6_results", s6.get("results"), flush=True)
    print("s7_present", bool(s7), flush=True)
    if isinstance(s7, dict):
        print("s7_keys", list(s7.keys())[:12], flush=True)
    print("GOLDEN02_H3_DONE", flush=True)


if __name__ == "__main__":
    main()
