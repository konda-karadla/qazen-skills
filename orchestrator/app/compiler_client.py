"""Shell out to the deterministic Automation Model Compiler.

S5 emits automation_model JSON; this module never asks an LLM for Playwright
source. It writes .spec.ts under playwright/generated/<run_id>/.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPILER_CLI = REPO_ROOT / "automation-compiler" / "src" / "cli.ts"
DEFAULT_OUT_ROOT = REPO_ROOT / "playwright" / "generated"


class CompilerError(RuntimeError):
    pass


def flatten_s4_test_data(s4_output: dict[str, Any], test_case_id: str) -> dict[str, Any]:
    """Prefer the dataset matching test_case_id; else merge all data_values."""
    datasets = s4_output.get("datasets") or []
    for ds in datasets:
        if ds.get("test_case_id") == test_case_id:
            return dict(ds.get("data_values") or {})
    merged: dict[str, Any] = {}
    for ds in datasets:
        merged.update(ds.get("data_values") or {})
    return merged


def compile_s5_model(
    s5_output: dict[str, Any],
    *,
    s4_output: dict[str, Any] | None = None,
    run_id: str,
    out_root: Path | None = None,
) -> dict[str, Any]:
    """Compile one S5 automation_model into a Playwright .spec.ts file.

    Returns metadata: {spec_path, file_name, script_id, test_case_id, source}.
    """
    out_dir = (out_root or DEFAULT_OUT_ROOT) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    test_case_id = s5_output.get("test_case_id", "TC-UNKNOWN")
    test_data = flatten_s4_test_data(s4_output or {}, test_case_id)

    with tempfile.TemporaryDirectory(prefix="qazen-compile-") as tmp:
        tmp_path = Path(tmp)
        s5_path = tmp_path / "s5.json"
        data_path = tmp_path / "data.json"
        s5_path.write_text(json.dumps(s5_output), encoding="utf-8")
        data_path.write_text(json.dumps(test_data), encoding="utf-8")

        cmd = (
            f'npx --yes tsx "{COMPILER_CLI}" "{s5_path}" "{data_path}" '
            f'--out-dir "{out_dir}"'
        )
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT / "automation-compiler"),
            capture_output=True,
            text=True,
            shell=True,
            check=False,
        )
        if completed.returncode != 0:
            raise CompilerError(
                f"automation-compiler failed (exit {completed.returncode}): "
                f"{completed.stderr or completed.stdout}"
            )

    # CLI writes {test_case_id}.spec.ts
    file_name = f"{test_case_id}.spec.ts"
    spec_path = out_dir / file_name
    if not spec_path.is_file():
        # Fallback: any .spec.ts just written in out_dir
        specs = sorted(out_dir.glob("*.spec.ts"))
        if not specs:
            raise CompilerError(f"Compiler reported success but no .spec.ts under {out_dir}")
        spec_path = specs[-1]
        file_name = spec_path.name

    source = spec_path.read_text(encoding="utf-8")
    return {
        "spec_path": str(spec_path.resolve()),
        "file_name": file_name,
        "script_id": s5_output.get("script_id"),
        "test_case_id": test_case_id,
        "layer": s5_output.get("layer"),
        "source": source,
        "out_dir": str(out_dir.resolve()),
    }
