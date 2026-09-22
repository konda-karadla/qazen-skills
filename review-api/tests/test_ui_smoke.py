"""Smoke test: SPA build is present and Review API mounts /ui + proxies mutations."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parents[1] / "static"
RUN_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_static_assets_present():
    assert (STATIC / "index.html").is_file()
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "QAZen" in html
    assert 'id="root"' in html
    assets = STATIC / "assets"
    assert assets.is_dir()
    assert any(assets.glob("index-*.js"))
    assert any(assets.glob("index-*.css"))


def test_health_and_ui_index():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ui"] == "/ui/"

    root = client.get("/", follow_redirects=False)
    assert root.status_code in (307, 302)
    assert root.headers["location"].endswith("/ui/")

    ui = client.get("/ui/")
    assert ui.status_code == 200
    assert "QAZen" in ui.text
    assert 'id="root"' in ui.text

    # SPA fallback for client routes
    spa = client.get("/ui/runs/new")
    assert spa.status_code == 200
    assert "QAZen" in spa.text


def test_post_runs_requires_raw():
    client = TestClient(app)
    res = client.post("/runs", json={"input": {"environment": "test"}})
    assert res.status_code == 400


def test_post_runs_proxies_to_orchestrator():
    client = TestClient(app)
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {"run_id": RUN_ID, "next": ["s3"]}

    with patch("app.main.httpx.post", return_value=fake) as post:
        res = client.post(
            "/runs",
            json={"input": {"raw": "Users must log in with valid credentials."}},
        )
    assert res.status_code == 200
    assert res.json()["run_id"].startswith("aaaaaaaa")
    assert post.call_args.args[0].endswith("/runs")
    assert post.call_args.kwargs["json"]["input"]["raw"].startswith("Users must")


def test_request_changes_proxies_to_orchestrator_revise_endpoint():
    client = TestClient(app)
    pending = {
        "gate": "H1",
        "review_id": "11111111-1111-1111-1111-111111111111",
        "artifact_version": 1,
    }
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {"run_id": RUN_ID, "next": ["s3"], "gate": "H1"}

    with (
        patch("app.main.db.get_pending_review", return_value=pending),
        patch("app.main.httpx.post", return_value=fake) as post,
    ):
        res = client.post(
            f"/runs/{RUN_ID}/request-changes",
            json={"reviewer": "qa-lead", "comment": "fix ambiguity"},
        )
    assert res.status_code == 200
    assert post.call_args.args[0].endswith(f"/runs/{RUN_ID}/request-changes")
    assert post.call_args.kwargs["json"]["gate"] == "H1"


def test_dashboard_and_integrations_shape():
    client = TestClient(app)
    with (
        patch("app.main.db.count_runs_by_status", return_value={"completed": 1, "paused": 2}),
        patch("app.main.db.count_pending_reviews", return_value=3),
        patch(
            "app.main.db.execution_stats",
            return_value={
                "tests_executed": 10,
                "passed": 8,
                "failed": 2,
                "skipped": 0,
                "failed_classified": 1,
                "failed_unclassified": 1,
                "pass_rate": 8 / 9,
            },
        ),
    ):
        summary = client.get("/dashboard/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["pending_reviews"] == 3
    assert body["active_runs"] == 2
    assert body["pass_rate_basis"].startswith("Based on classified")
    assert body["pass_rate_display"] == "88.9%"

    integ = client.get("/integrations/status")
    assert integ.status_code == 200
    assert integ.json()["stop_run"]["available"] is False
    assert integ.json()["playwright"]["mcp"] is False
    assert integ.json()["knowledge_base"]["writable"] is False


def test_reviews_recent_endpoint():
    client = TestClient(app)
    with patch(
        "app.main.db.list_recent_reviews",
        return_value=[
            {
                "review_id": "r1",
                "run_id": "00000000-0000-0000-0000-000000000001",
                "gate": "H1",
                "decision": "approved",
                "reviewer": "qa-lead",
                "comment": "ok",
                "artifact_version": 1,
                "created_at": None,
                "decided_at": None,
                "run_status": "running",
                "current_stage": "S3",
            }
        ],
    ), patch("app.main.db.requirement_summary_for_run", return_value="Login story"):
        res = client.get("/reviews/recent")
    assert res.status_code == 200
    body = res.json()
    assert len(body["reviews"]) == 1
    assert body["reviews"][0]["decision"] == "approved"
    assert body["reviews"][0]["requirement_summary"] == "Login story"


def test_cross_run_catalog_endpoints():
    client = TestClient(app)
    with patch(
        "app.main.db.list_test_cases_cross_run",
        return_value=[
            {
                "test_case_id": "TC-001",
                "run_id": "00000000-0000-0000-0000-000000000001",
                "version": 1,
                "source_requirement_id": "REQ-1",
                "layer": "UI",
                "obligation": "login",
                "expected_result": "dashboard",
                "expected_result_basis": "ac1",
                "duplicate_of": None,
                "last_execution_status": "pass",
                "created_at": None,
            }
        ],
    ), patch(
        "app.main.db.list_scripts_cross_run",
        return_value=[
            {
                "script_id": None,
                "run_id": "00000000-0000-0000-0000-000000000001",
                "test_case_id": "TC-001",
                "file_name": "TC-001.spec.ts",
                "framework": "playwright",
                "version": 1,
                "source": "test('x')",
                "spec_path": None,
                "artifact_id": "a1",
                "created_at": None,
            }
        ],
    ), patch(
        "app.main.db.list_test_executions_cross_run",
        return_value=[
            {
                "execution_id": "00000000-0000-0000-0000-000000000099",
                "run_id": "00000000-0000-0000-0000-000000000001",
                "test_case_id": "TC-001",
                "correlation_id": "c1",
                "status": "pass",
                "classification": None,
                "retry_attempts": 0,
                "evidence_manifest": [],
                "created_at": None,
            }
        ],
    ):
        tc = client.get("/test-cases")
        sc = client.get("/scripts")
        ex = client.get("/executions")
    assert tc.status_code == 200 and tc.json()["test_cases"][0]["test_case_id"] == "TC-001"
    assert sc.status_code == 200 and sc.json()["scripts"][0]["file_name"] == "TC-001.spec.ts"
    assert ex.status_code == 200 and ex.json()["executions"][0]["status"] == "pass"
