"""Loads schemas/<skill>.schema.json and validates a candidate output against it.

AI generates. Schema validates. Nothing here decides whether content is
*correct* -- only whether it is *structurally* valid enough for the
Orchestrator to persist and present at a human gate.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.config import settings

# S1 -> s1.schema.json, S2 -> s2.schema.json, etc.
_SKILL_TO_SCHEMA_FILE = {f"S{i}": f"s{i}.schema.json" for i in range(1, 12)}


class SchemaNotFoundError(Exception):
    pass


class SchemaValidationError(Exception):
    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors


def schema_path_for(skill_id: str) -> Path:
    filename = _SKILL_TO_SCHEMA_FILE.get(skill_id)
    if filename is None:
        raise SchemaNotFoundError(f"No schema mapping configured for skill '{skill_id}'")
    path = settings.schemas_dir / filename
    if not path.exists():
        raise SchemaNotFoundError(f"Schema file not found for '{skill_id}': {path}")
    return path


def load_schema(skill_id: str) -> dict:
    path = schema_path_for(skill_id)
    return json.loads(path.read_text(encoding="utf-8"))


def validate(skill_id: str, candidate: dict) -> None:
    """Raises SchemaValidationError if candidate does not conform.

    Collects *all* validation errors (not just the first) so a retry prompt
    can address everything in one pass.
    """
    schema = load_schema(skill_id)
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(candidate), key=lambda e: list(e.path))
    if errors:
        messages = [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]
        raise SchemaValidationError(
            f"{len(messages)} schema validation error(s) for {skill_id}", messages
        )
