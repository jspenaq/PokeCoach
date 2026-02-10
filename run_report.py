"""Command-line entrypoint for generating post-game reports."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pokecoach.report import generate_post_game_report
from pokecoach.schemas import PostGameReport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_report.py",
        description="Generate a PokeCoach post-game report from a battle log.",
    )
    parser.add_argument("log_path", help="Path to the battle log file.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "md"),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "--output",
        help="Optional output file path. If omitted, writes to stdout.",
    )
    parser.add_argument(
        "--deterministic-only",
        action="store_true",
        help="Bypass LLM guidance and keep deterministic fallback behavior only.",
    )
    return parser


@contextmanager
def _temporarily_disable_llm(enabled: bool):
    if not enabled:
        yield
        return

    api_key = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        yield
    finally:
        if api_key is not None:
            os.environ["OPENROUTER_API_KEY"] = api_key


def _read_log_text(log_path: str) -> str:
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")
    return path.read_text(encoding="utf-8")


def _render_markdown(report: PostGameReport) -> str:
    lines: list[str] = []
    lines.extend(["# Post-Game Report", ""])
    lines.extend(["## Summary", ""])
    lines.extend(f"- {item}" for item in report.summary)
    lines.extend(["", "## Turning Points", ""])
    for idx, tp in enumerate(report.turning_points, start=1):
        lines.append(f"### {idx}. {tp.title}")
        lines.append(f"- Impact: {tp.impact}")
        lines.append(f"- Confidence: {tp.confidence:.2f}")
        lines.append(f"- Depends on hidden info: {tp.depends_on_hidden_info}")
        lines.append(f"- Evidence ({tp.evidence.start_line}-{tp.evidence.end_line}):")
        lines.extend(f"  - {raw}" for raw in tp.evidence.raw_lines)
        lines.append("")
    lines.extend(["## Mistakes", ""])
    for idx, ms in enumerate(report.mistakes, start=1):
        lines.append(f"### {idx}. {ms.description}")
        lines.append(f"- Why it matters: {ms.why_it_matters}")
        lines.append(f"- Better line: {ms.better_line}")
        lines.append(f"- Confidence: {ms.confidence:.2f}")
        lines.append(f"- Depends on hidden info: {ms.depends_on_hidden_info}")
        lines.append(f"- Evidence ({ms.evidence.start_line}-{ms.evidence.end_line}):")
        lines.extend(f"  - {raw}" for raw in ms.evidence.raw_lines)
        lines.append("")
    lines.extend(["## Unknowns", ""])
    lines.extend(f"- {item}" for item in report.unknowns)
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in report.next_actions)
    return "\n".join(lines).rstrip() + "\n"


def _serialize_report(report: PostGameReport, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    if output_format == "md":
        return _render_markdown(report)
    raise ValueError(f"Unsupported format: {output_format}")


def _write_output(content: str, output_path: str | None) -> None:
    if output_path is None:
        print(content, end="")
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        log_text = _read_log_text(args.log_path)
        with _temporarily_disable_llm(args.deterministic_only):
            report = generate_post_game_report(log_text)
        rendered = _serialize_report(report, args.output_format)
        _write_output(rendered, args.output)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: failed to read or write files: {exc}", file=os.sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: failed to generate report: {exc}", file=os.sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
