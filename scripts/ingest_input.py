#!/usr/bin/env python3
"""Materialize the active human/agent input package into the internal TTS queue.

Humans and agents write only under input/<job-id>/. The legacy transcripts/
directory remains an internal queue so the proven TTS/assembly/alignment code can
stay stable while the repository evolves into a full video factory.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_EXTENSIONS = {".txt", ".md"}


class InputError(ValueError):
    pass


def read_active(path: Path) -> str | None:
    if not path.exists():
        raise InputError(f"Missing active-job pointer: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return line
    return None


def load_job(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise InputError(f"Missing job.yaml: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise InputError("job.yaml must contain a YAML mapping")
    return data


def same_bytes(a: Path, b: Path) -> bool:
    return a.exists() and b.exists() and a.read_bytes() == b.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest input/ACTIVE into transcripts/")
    parser.add_argument("--input-root", type=Path, default=Path("input"))
    parser.add_argument("--queue-root", type=Path, default=Path("transcripts"))
    parser.add_argument("--done-root", type=Path, default=Path("done"))
    args = parser.parse_args()

    try:
        active = read_active(args.input_root / "ACTIVE")
        if not active:
            print("No active input job. Nothing to ingest.")
            return 0
        if active.startswith("_") or "/" in active or "\\" in active or active in {".", ".."}:
            raise InputError(f"Unsafe or reserved active job id: {active!r}")

        job_dir = args.input_root / active
        if not job_dir.is_dir():
            raise InputError(f"Active job folder does not exist: {job_dir}")

        job = load_job(job_dir / "job.yaml")
        declared_id = str(job.get("id", "")).strip()
        if not declared_id:
            raise InputError("job.yaml requires a non-empty 'id'")
        if declared_id != active:
            raise InputError(
                f"job.yaml id {declared_id!r} must match input/ACTIVE {active!r}"
            )

        audio_config = job.get("audio", {}) or {}
        if not isinstance(audio_config, dict):
            raise InputError("job.yaml 'audio' must be a mapping")
        audio_enabled = bool(audio_config.get("enabled", True))
        if not audio_enabled:
            print(f"Active job {active}: audio.enabled=false; no TTS input to ingest.")
            return 0

        source_dir = job_dir / "transcript"
        if not source_dir.is_dir():
            raise InputError(f"Audio is enabled but transcript folder is missing: {source_dir}")

        parts = sorted(
            p
            for p in source_dir.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and not p.name.startswith(".")
        )
        if not parts:
            raise InputError(f"No .txt/.md transcript parts found in {source_dir}")

        for part in parts:
            stem = part.stem
            prefix = stem.split("-", 1)[0]
            if len(prefix) != 2 or not prefix.isdigit():
                raise InputError(
                    f"Transcript part must start with a zero-padded number (01-, 02-, ...): {part.name}"
                )

        done_dir = args.done_root / active
        known_done = {
            p.name
            for p in done_dir.iterdir()
            if done_dir.is_dir() and p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        } if done_dir.exists() else set()
        input_names = {p.name for p in parts}
        stale_done = sorted(known_done - input_names)
        if stale_done:
            raise InputError(
                "Input removed/renamed transcript parts that already have production state: "
                + ", ".join(stale_done)
                + ". Use a new job id or explicitly reset stale audio/state before changing the part list."
            )

        queue_dir = args.queue_root / active
        queue_dir.mkdir(parents=True, exist_ok=True)
        queued = 0
        reused = 0

        for source in parts:
            queued_path = queue_dir / source.name
            done_path = done_dir / source.name

            if same_bytes(source, done_path):
                if queued_path.exists():
                    queued_path.unlink()
                reused += 1
                print(f"  Reusing completed source: {source.name}")
                continue

            if same_bytes(source, queued_path):
                print(f"  Already queued: {source.name}")
                continue

            shutil.copy2(source, queued_path)
            queued += 1
            print(f"  Queued: {source.name}")

        try:
            if queue_dir.exists() and not any(queue_dir.iterdir()):
                queue_dir.rmdir()
        except OSError:
            pass

        print(
            f"Active job {active}: {len(parts)} part(s), {queued} newly queued, "
            f"{reused} already complete."
        )
        return 0
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
