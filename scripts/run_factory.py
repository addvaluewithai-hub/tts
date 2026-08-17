#!/usr/bin/env python3
"""Run the complete audio stage (TTS → assemble → align → soundtrack) for Video Factory."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "tts": ROOT / "scripts" / "process_tts.py",
    "assemble": ROOT / "scripts" / "assemble_lessons.py",
    "align": ROOT / "scripts" / "transcribe_final.py",
    "soundtrack": ROOT / "scripts" / "run_soundtrack.py",
}
ORDER = ("tts", "assemble", "align", "soundtrack")


def run_stage(name: str, config: Path) -> int:
    script = STAGES[name]
    command = [sys.executable, str(script)]
    if name != "soundtrack":
        command += ["--config", str(config)]

    print(f"\n=== {name.upper()} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        print(
            f"Audio factory stopped: stage '{name}' failed with exit code {completed.returncode}.",
            file=sys.stderr,
        )
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Video Factory audio stage")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("tts_config.yaml"),
        help="Audio-stage config path relative to the repository root",
    )
    parser.add_argument(
        "--stage",
        choices=("all", *ORDER),
        default="all",
        help="Run the full audio stage or one recovery/debug stage",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stages = ORDER if args.stage == "all" else (args.stage,)

    for stage in stages:
        result = run_stage(stage, args.config)
        if result:
            return result

    print("\nAudio factory complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
