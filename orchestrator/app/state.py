"""LangGraph run state for the full pipeline:

    S1 -> S2 -> [H1] -> S3 -> S4 -> [H2] -> S5 -> [H3] -> S6 -> S7 -> S8 -> S9
         -> [H4] -> S10 -> [H5] -> S11

Gates are implemented as langgraph `interrupt_before` on the node that would
start the *next* stage (S3, S5, S6, S10, S11 respectively) -- the graph
naturally pauses with exactly the artifacts a human needs for that gate
already in state, and resumes only when the Review API tells the Orchestrator
a human has approved.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class RunState(TypedDict, total=False):
    run_id: str
    requirement_id: str
    raw_input: dict[str, Any]

    s1_output: dict[str, Any]
    s2_output: dict[str, Any]
    s3_output: dict[str, Any]
    s4_output: dict[str, Any]
    s5_output: dict[str, Any]
    s6_output: dict[str, Any]
    s7_output: dict[str, Any]
    s8_output: dict[str, Any]
    s9_output: dict[str, Any]
    s10_output: dict[str, Any]
    s11_output: dict[str, Any]

    # Metadata from the deterministic Automation Model Compiler (after S5).
    compiled_specs: dict[str, Any]

    # artifact_id (Postgres) for each stage's saved output, used to link
    # human_reviews rows to the exact versioned artifact being reviewed.
    artifact_ids: dict[str, str]

    escalated: bool
    escalation_reason: Optional[str]

    # Latest request-changes comment; included in skill inputs on revision re-runs.
    review_feedback: Optional[str]
