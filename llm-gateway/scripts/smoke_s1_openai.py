#!/usr/bin/env python3
"""Smoke a real (non-mock) S1 invoke against the LLM Gateway.

Usage (gateway must already be running with openai provider):
  ..\\.venv\\Scripts\\python.exe scripts\\smoke_s1_openai.py

Or invoke the gateway in-process (no HTTP server required):
  ..\\.venv\\Scripts\\python.exe scripts\\smoke_s1_openai.py --in-process

Never prints OPENAI_API_KEY. Refuses to run when the resolved provider is mock.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

GATEWAY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATEWAY_ROOT))

from app.config import settings  # noqa: E402
from app.gateway import invoke_skill  # noqa: E402
from app.schema_validator import validate  # noqa: E402


SAMPLE_INPUT = {
    "raw": (
        "BRD: Demo Shop QA\n"
        "Users must log in at https://www.saucedemo.com with valid credentials "
        "and reach the inventory page. Invalid credentials must show an error. "
        "API: GET https://reqres.in/api/users?page=2 must return status 200."
    )
}


def _assert_not_mock() -> None:
    if settings.provider == "mock":
        print(
            "Refusing: provider is 'mock'. Set LLM_PROVIDER=openai "
            "(or unset LLM_PROVIDER and set AI_PROVIDER=openai) and retry.",
            file=sys.stderr,
        )
        sys.exit(2)
    if settings.provider != "openai":
        print(
            f"Refusing: expected provider 'openai', got '{settings.provider}'.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not settings.openai_api_key:
        print("Refusing: OPENAI_API_KEY is empty.", file=sys.stderr)
        sys.exit(2)


def _summarize(result) -> None:
    print(f"provider={settings.provider}")
    print(f"model={settings.openai_model}")
    print(f"skill_id={result.skill_id}")
    print(f"attempts={result.attempts}")
    print(f"escalated={result.escalated}")
    if result.escalation_reason:
        print(f"escalation_reason={result.escalation_reason[:500]}")
    print(f"output_keys={sorted(result.output.keys())}")
    if not result.escalated:
        validate("S1", result.output)
        print("schema_validation=ok")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Call invoke_skill directly instead of HTTP",
    )
    parser.add_argument(
        "--gateway-url",
        default="http://127.0.0.1:8000",
        help="Gateway base URL when not using --in-process",
    )
    args = parser.parse_args()
    _assert_not_mock()

    if args.in_process:
        result = invoke_skill("S1", SAMPLE_INPUT)
        _summarize(result)
        return 1 if result.escalated else 0

    import httpx

    response = httpx.post(
        f"{args.gateway_url.rstrip('/')}/v1/skills/S1/invoke",
        json={"input": SAMPLE_INPUT},
        timeout=120.0,
    )
    response.raise_for_status()
    body = response.json()
    print(f"provider={settings.provider}")
    print(f"model={settings.openai_model}")
    print(f"skill_id={body.get('skill_id')}")
    print(f"attempts={body.get('attempts')}")
    print(f"escalated={body.get('escalated')}")
    if body.get("escalation_reason"):
        print(f"escalation_reason={str(body['escalation_reason'])[:500]}")
    output = body.get("output") or {}
    print(f"output_keys={sorted(output.keys())}")
    if not body.get("escalated"):
        validate("S1", output)
        print("schema_validation=ok")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
