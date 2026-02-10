from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

UV_CACHE_DIR = "/tmp/uv-cache"
REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = "logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt"


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = UV_CACHE_DIR
    # Keep import resolution stable across CI and local runs.
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        ["uv", "run", sys.executable, "run_report.py", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=REPO_ROOT,
    )


def test_cli_format_json_writes_valid_json_to_stdout() -> None:
    completed = _run_cli([LOG_PATH, "--format", "json", "--deterministic-only"])

    assert completed.returncode == 0, completed.stderr
    parsed = json.loads(completed.stdout)
    assert "summary" in parsed
    assert "turning_points" in parsed
    assert "mistakes" in parsed
    assert completed.stderr == ""


def test_cli_format_md_writes_markdown_to_stdout() -> None:
    completed = _run_cli([LOG_PATH, "--format", "md", "--deterministic-only"])

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("# Post-Game Report")
    assert "## Summary" in completed.stdout
    assert completed.stderr == ""


def test_cli_returns_non_zero_for_missing_log() -> None:
    completed = _run_cli(["logs_prueba/does_not_exist.txt"])

    assert completed.returncode != 0
    assert "Log file not found" in completed.stderr


def test_cli_writes_output_file_and_creates_parent_dirs(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "reports" / "report.md"

    completed = _run_cli([LOG_PATH, "--format", "md", "--output", str(output_path), "--deterministic-only"])

    assert completed.returncode == 0, completed.stderr
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Post-Game Report")
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_cli_deterministic_only_emits_valid_json() -> None:
    completed = _run_cli([LOG_PATH, "--deterministic-only"])

    assert completed.returncode == 0, completed.stderr
    parsed = json.loads(completed.stdout)
    assert isinstance(parsed["summary"], list)
    assert isinstance(parsed["turning_points"], list)


def test_cli_invalid_format_returns_argparse_error() -> None:
    completed = _run_cli([LOG_PATH, "--format", "txt", "--deterministic-only"])

    assert completed.returncode != 0
    assert "invalid choice" in completed.stderr
