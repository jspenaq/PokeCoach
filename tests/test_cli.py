from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

UV_CACHE_DIR = "/tmp/uv-cache"


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = UV_CACHE_DIR
    return subprocess.run(
        ["uv", "run", "python", "run_report.py", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_success_writes_json_to_stdout() -> None:
    log_path = "logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt"

    completed = _run_cli([log_path, "--deterministic-only"])

    assert completed.returncode == 0
    parsed = json.loads(completed.stdout)
    assert "summary" in parsed
    assert "turning_points" in parsed
    assert "mistakes" in parsed
    assert completed.stderr == ""


def test_cli_returns_non_zero_for_missing_log() -> None:
    completed = _run_cli(["logs_prueba/does_not_exist.txt"])

    assert completed.returncode != 0
    assert "Log file not found" in completed.stderr


def test_cli_writes_output_file(tmp_path: Path) -> None:
    log_path = "logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt"
    output_path = tmp_path / "report.md"

    completed = _run_cli([log_path, "--format", "md", "--output", str(output_path)])

    assert completed.returncode == 0
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Post-Game Report")
