"""scripts_from_compiled should keep unique files across Compile versions."""
from __future__ import annotations

from app import db


def test_scripts_from_compiled_dedupes_by_file_across_versions(monkeypatch):
    rows = [
        {
            "artifact_id": "a2",
            "run_id": "r1",
            "version": 2,
            "created_at": None,
            "content": {
                "file_name": "TC-invalid_login_001.spec.ts",
                "test_case_id": "TC-invalid_login_001",
                "script_id": "SCR-TC-invalid_login_001",
                "source": "invalid",
            },
        },
        {
            "artifact_id": "a1",
            "run_id": "r1",
            "version": 1,
            "created_at": None,
            "content": {
                "file_name": "TC-valid_login_001.spec.ts",
                "test_case_id": "TC-valid_login_001",
                "script_id": "SCR-TC-valid_login_001",
                "source": "valid",
            },
        },
        {
            "artifact_id": "a0",
            "run_id": "r1",
            "version": 1,
            "created_at": None,
            "content": {
                "file_name": "TC-valid_login_001.spec.ts",
                "test_case_id": "TC-valid_login_001",
                "script_id": "SCR-old",
                "source": "old-valid",
            },
        },
    ]

    class FakeConn:
        def execute(self, *_args, **_kwargs):
            class R:
                def fetchall(self_inner):
                    return rows

            return R()

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr(db, "get_conn", lambda: FakeConn())
    scripts = db.scripts_from_compiled("r1")
    names = [s["file_name"] for s in scripts]
    assert names == [
        "TC-invalid_login_001.spec.ts",
        "TC-valid_login_001.spec.ts",
    ]
    assert scripts[1]["source"] == "valid"


def test_automation_models_from_s5_dedupes_by_test_case(monkeypatch):
    rows = [
        {
            "artifact_id": "m2",
            "run_id": "r1",
            "version": 2,
            "created_at": None,
            "content": {
                "script_id": "SCR-TC-invalid_login_001",
                "test_case_id": "TC-invalid_login_001",
                "layer": "UI",
                "automation_model": {"actions": []},
            },
        },
        {
            "artifact_id": "m1",
            "run_id": "r1",
            "version": 1,
            "created_at": None,
            "content": {
                "script_id": "SCR-TC-valid_login_001",
                "test_case_id": "TC-valid_login_001",
                "layer": "UI",
                "automation_model": {"actions": [{"type": "click"}]},
            },
        },
    ]

    class FakeConn:
        def execute(self, *_args, **_kwargs):
            class R:
                def fetchall(self_inner):
                    return rows

            return R()

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr(db, "get_conn", lambda: FakeConn())
    models = db.automation_models_from_s5("r1")
    assert [m["test_case_id"] for m in models] == [
        "TC-invalid_login_001",
        "TC-valid_login_001",
    ]
    assert models[1]["version"] == 1
    assert models[1]["model"]["script_id"] == "SCR-TC-valid_login_001"
