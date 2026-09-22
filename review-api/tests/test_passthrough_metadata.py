"""Unit tests for New Run passthrough metadata resolution on GET /runs."""
from __future__ import annotations

from app import db


def test_passthrough_prefers_runs_columns():
    run = {
        "base_url": "http://127.0.0.1:8765",
        "environment": "test",
        "branch": "main",
    }
    # Avoid DB: monkeypatch helpers via direct call with empty S1/S6 by patching.
    original_s1 = db.metadata_from_s1
    original_s6 = db._base_url_from_s6
    try:
        db.metadata_from_s1 = lambda _run_id: {"base_url": "http://from-s1.example"}  # type: ignore
        db._base_url_from_s6 = lambda _run_id: "http://from-s6.example"  # type: ignore
        meta = db.passthrough_metadata_for_run(run, "00000000-0000-0000-0000-000000000001")
    finally:
        db.metadata_from_s1 = original_s1  # type: ignore
        db._base_url_from_s6 = original_s6  # type: ignore
    assert meta["base_url"] == "http://127.0.0.1:8765"
    assert meta["environment"] == "test"
    assert meta["branch"] == "main"


def test_passthrough_falls_back_to_s6_app_build():
    run = {"base_url": None, "environment": None, "branch": None}
    original_s1 = db.metadata_from_s1
    original_s6 = db._base_url_from_s6
    try:
        db.metadata_from_s1 = lambda _run_id: {}  # type: ignore
        db._base_url_from_s6 = lambda _run_id: "http://127.0.0.1:8765"  # type: ignore
        meta = db.passthrough_metadata_for_run(run, "00000000-0000-0000-0000-000000000002")
    finally:
        db.metadata_from_s1 = original_s1  # type: ignore
        db._base_url_from_s6 = original_s6  # type: ignore
    assert meta["base_url"] == "http://127.0.0.1:8765"
