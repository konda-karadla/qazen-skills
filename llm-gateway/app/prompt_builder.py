"""Assembles a single completion prompt from:

    AGENT_INSTRUCTIONS.md (binding rulebook, read fresh every call)
    + skills/<skill_id>/skill.md (the specific skill, read fresh every call)
    + the caller-supplied input/context for this invocation
    + (on retry only) the previous output and the schema validation error

No state is cached between calls -- every invocation re-reads both markdown
files from disk, per the framework's stateless-skill design.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


class SkillNotFoundError(Exception):
    pass


def _read_text(path: Path) -> str:
    if not path.exists():
        raise SkillNotFoundError(f"Expected file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_agent_instructions() -> str:
    return _read_text(settings.agent_instructions_path)


def load_skill_md(skill_id: str) -> str:
    """skill_id like 'S1', 'S3', 'S5' -- maps to skills/<skill_id>/skill.md."""
    path = settings.skills_dir / skill_id / "skill.md"
    return _read_text(path)


def build_prompt(
    skill_id: str,
    input_payload: dict,
    output_schema: dict | None = None,
    prior_output: dict | None = None,
    prior_error: str | None = None,
) -> str:
    instructions = load_agent_instructions()
    skill_md = load_skill_md(skill_id)

    sections = [
        "# BINDING RULEBOOK (AGENT_INSTRUCTIONS.md) -- inherits without dilution\n",
        instructions,
        "\n\n# SKILL DEFINITION -- " + skill_id + "\n",
        skill_md,
        "\n\n# INPUT FOR THIS INVOCATION\n",
        "```json\n" + json.dumps(input_payload, indent=2) + "\n```",
    ]

    if output_schema is not None:
        sections.append(
            "\n\n# REQUIRED OUTPUT SCHEMA\n"
            "Respond with a single JSON object that validates against this JSON Schema. "
            "No prose outside the JSON object.\n"
            "```json\n" + json.dumps(output_schema, indent=2) + "\n```"
        )

    if prior_output is not None and prior_error:
        sections.append(
            "\n\n# PREVIOUS ATTEMPT FAILED SCHEMA VALIDATION -- FIX AND RETRY\n"
            "Your previous output:\n```json\n"
            + json.dumps(prior_output, indent=2)
            + "\n```\n"
            "Validation error:\n" + prior_error + "\n"
            "Return a corrected JSON object only. Do not change the substance of your "
            "answer beyond what's needed to satisfy the schema -- do not use this as an "
            "opportunity to weaken an assertion or invent a value to fill a gap; if the "
            "error is because required information is genuinely missing, escalate instead "
            "per Section 7 of the rulebook."
        )

    return "\n".join(sections)
