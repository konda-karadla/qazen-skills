"""Smoke: count unique S5 models for a completed mapping run."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "review-api"))

from app import db  # noqa: E402

RUN = "fc8083f6-d524-4c48-aff6-f893075c8151"
models = db.automation_models_from_s5(RUN)
print([(m["version"], m["test_case_id"]) for m in models])
print("count", len(models))
