"""Manual CLI trigger: `python -m app.cli start-run --raw-text "..."` etc.
Same runner functions the HTTP API uses -- neither is the source of truth,
Postgres + the LangGraph checkpoint are.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from app import runner

cli = typer.Typer(help="QAZen Orchestrator manual trigger (Phase 0/1)")


@cli.command("start-run")
def start_run_cmd(
    input_file: Optional[Path] = typer.Option(None, help="Path to a JSON file with the raw input payload"),
    raw_text: Optional[str] = typer.Option(None, help="Inline raw requirement text, shorthand for {'raw': text}"),
    requirement_id: Optional[str] = typer.Option(None),
) -> None:
    if input_file:
        payload = json.loads(input_file.read_text(encoding="utf-8"))
    elif raw_text:
        payload = {"raw": raw_text}
    else:
        raise typer.BadParameter("Provide either --input-file or --raw-text")

    result = runner.start_run(payload, requirement_id=requirement_id)
    typer.echo(json.dumps(result, indent=2, default=str))


@cli.command("resume-run")
def resume_run_cmd(
    run_id: str,
    gate: str = typer.Option(..., help="H1, H2, or H3"),
    reviewer: str = typer.Option(...),
    comment: Optional[str] = typer.Option(None),
) -> None:
    result = runner.approve_gate_and_resume(run_id, gate, reviewer, comment)
    typer.echo(json.dumps(result, indent=2, default=str))


@cli.command("reject-run")
def reject_run_cmd(
    run_id: str,
    gate: str = typer.Option(...),
    reviewer: str = typer.Option(...),
    comment: Optional[str] = typer.Option(None),
) -> None:
    runner.reject_gate(run_id, gate, reviewer, comment, decision="rejected")
    typer.echo(f"Gate {gate} for run {run_id} rejected.")


@cli.command("request-changes")
def request_changes_cmd(
    run_id: str,
    gate: str = typer.Option(...),
    reviewer: str = typer.Option(...),
    comment: Optional[str] = typer.Option(None),
) -> None:
    result = runner.request_changes_and_revise(run_id, gate, reviewer, comment)
    typer.echo(json.dumps(result, indent=2, default=str))


@cli.command("status")
def status_cmd(run_id: str) -> None:
    snapshot = runner.get_run_snapshot(run_id)
    typer.echo(json.dumps(snapshot, indent=2, default=str))


if __name__ == "__main__":
    cli()
