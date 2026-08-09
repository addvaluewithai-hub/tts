#!/usr/bin/env python3
"""Run the complete TTS factory pipeline from one stable entry point."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "tts": ROOT / "scripts" / "process_tts.py",
    "assemble": ROOT / "scripts" / "assemble_lessons.py",
    "align": ROOT / "scripts" / "transcribe_final.py",
}
ORDER = ("tts", "assemble", "align")
ARCHIVE_SUFFIX = re.compile(r"^(?P<stem>.+)-(?P<stamp>\d{8}T\d{6}Z)(?P<suffix>\.[^.]+)$")


def run_stage(name: str, config: Path) -> int:
    script = STAGES[name]
    command = [sys.executable, str(script), "--config", str(config)]
    print(f"\n=== {name.upper()} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        print(
            f"Factory stopped: stage '{name}' failed with exit code {completed.returncode}.",
            file=sys.stderr,
        )
    return completed.returncode


def canonicalize_done(done_dir: Path) -> int:
    """Keep the latest successful transcript at its canonical path in done/.

    process_tts preserves an existing done file by adding a UTC timestamp to a retake.
    For downstream alignment, the newest successful retake must become canonical while
    Git history remains the archive of older versions.
    """
    if not done_dir.exists():
        return 0

    groups: dict[Path, list[tuple[str, Path]]] = {}
    for path in done_dir.rglob("*"):
        if not path.is_file():
            continue
        match = ARCHIVE_SUFFIX.match(path.name)
        if not match:
            continue
        canonical = path.with_name(f"{match.group('stem')}{match.group('suffix')}")
        groups.setdefault(canonical, []).append((match.group("stamp"), path))

    normalized = 0
    for canonical, candidates in groups.items():
        candidates.sort(key=lambda item: item[0])
        _, newest = candidates[-1]
        canonical.unlink(missing_ok=True)
        newest.replace(canonical)
        for _, stale in candidates[:-1]:
            stale.unlink(missing_ok=True)
        normalized += 1
        print(f"Canonicalized latest transcript -> {canonical.relative_to(done_dir.parent)}")
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the TTS factory")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("tts_config.yaml"),
        help="Factory config path relative to the repository root",
    )
    parser.add_argument(
        "--stage",
        choices=("all", *ORDER),
        default="all",
        help="Run the full pipeline or one recovery/debug stage",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stages = ORDER if args.stage == "all" else (args.stage,)

    for stage in stages:
        result = run_stage(stage, args.config)
        if result:
            return result
        if stage == "tts":
            canonicalize_done(ROOT / "done")

    print("\nFactory complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
