#!/usr/bin/env python3
"""Report the active Video Factory job and the next production gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def read_active(path: Path) -> str | None:
    if not path.exists():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return line
    return None


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def determine_next(status: dict[str, Any]) -> str:
    if not status["active_job"]:
        return "set_active_job"
    if not status["input"]["valid_minimum"]:
        return "complete_input_package"
    if not status["audio"]["complete"]:
        return "run_or_fix_audio_factory"
    if not status["video"]["source_exists"]:
        return "author_video_source_from_direction_and_timing"
    if not status["video"]["qa_passed"]:
        return "run_or_fix_visual_qa"
    if not status["video"]["approved"]:
        return "manually_review_qa_artifact_and_approve"
    if not status["video"]["final_complete"]:
        return "run_or_fix_final_render"
    return "production_ready"


def build_status(root: Path) -> dict[str, Any]:
    active = read_active(root / "input" / "ACTIVE")
    result: dict[str, Any] = {
        "active_job": active,
        "input": {},
        "audio": {},
        "video": {},
    }

    if not active:
        result["input"] = {"valid_minimum": False}
        result["audio"] = {"complete": False}
        result["video"] = {
            "source_exists": False,
            "qa_passed": False,
            "approved": False,
            "final_complete": False,
        }
        result["next_action"] = determine_next(result)
        return result

    job_dir = root / "input" / active
    job_yaml = job_dir / "job.yaml"
    direction = job_dir / "direction.md"
    transcript_dir = job_dir / "transcript"
    job_data: dict[str, Any] = {}
    if job_yaml.exists():
        try:
            parsed = yaml.safe_load(job_yaml.read_text(encoding="utf-8")) or {}
            if isinstance(parsed, dict):
                job_data = parsed
        except yaml.YAMLError:
            pass

    audio_enabled = bool((job_data.get("audio") or {}).get("enabled", True)) if isinstance(job_data.get("audio") or {}, dict) else True
    transcript_parts = sorted(
        p.name
        for p in transcript_dir.glob("*")
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}
    ) if transcript_dir.exists() else []
    minimum = (
        job_dir.is_dir()
        and job_yaml.is_file()
        and direction.is_file()
        and str(job_data.get("id", "")).strip() == active
        and (not audio_enabled or bool(transcript_parts))
    )

    result["input"] = {
        "folder": str(job_dir.relative_to(root)) if job_dir.exists() else str(job_dir),
        "valid_minimum": minimum,
        "audio_enabled": audio_enabled,
        "transcript_parts": transcript_parts,
    }

    final_wav = root / "final" / f"{active}.wav"
    final_mp3 = root / "final" / f"{active}.mp3"
    timing = root / "final" / f"{active}.transcript.json"
    audio_manifest = root / "final" / f"{active}.json"
    result["audio"] = {
        "wav": final_wav.exists() and final_wav.stat().st_size > 0,
        "mp3": final_mp3.exists() and final_mp3.stat().st_size > 0,
        "timing_json": timing.exists() and timing.stat().st_size > 0,
        "manifest": audio_manifest.exists() and audio_manifest.stat().st_size > 0,
    }
    result["audio"]["complete"] = bool(
        result["audio"]["wav"]
        and result["audio"]["mp3"]
        and result["audio"]["timing_json"]
        and result["audio"]["manifest"]
    )

    project = root / "productions" / active / "video"
    qa_manifest_path = root / ".factory-status" / "video" / active / "qa-latest.json"
    final_manifest_path = root / ".factory-status" / "video" / active / "final-latest.json"
    final_status_path = root / ".factory-status" / "video" / active / "final-status.json"
    approval = root / "approvals" / active / "APPROVED"

    qa = read_json(qa_manifest_path)
    final_manifest = read_json(final_manifest_path)
    final_state = read_json(final_status_path)
    qa_passed = bool(
        qa
        and qa.get("lint_outcome") == "success"
        and qa.get("check_outcome") == "success"
        and qa.get("inspect_outcome") == "success"
        and qa.get("draft_outcome") == "success"
    )
    final_complete = bool(final_manifest and final_state and final_state.get("status") == "complete")

    result["video"] = {
        "source_exists": project.is_dir() and (project / "scripts" / "build-from-audio.mjs").is_file(),
        "qa_manifest": str(qa_manifest_path.relative_to(root)),
        "qa_passed": qa_passed,
        "qa_run_id": qa.get("run_id") if qa else None,
        "approved": approval.is_file(),
        "final_status": final_state.get("status") if final_state else None,
        "final_manifest": str(final_manifest_path.relative_to(root)),
        "final_complete": final_complete,
        "final_run_id": final_manifest.get("run_id") if final_manifest else None,
        "artifact_url": final_manifest.get("artifact_url") if final_manifest else None,
    }

    result["next_action"] = determine_next(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Show active Video Factory production status")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    status = build_status(args.root.resolve())
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0

    print(f"Active job: {status['active_job'] or '(none)'}")
    print(f"Input ready: {status['input'].get('valid_minimum', False)}")
    print(f"Audio complete: {status['audio'].get('complete', False)}")
    print(f"Video source: {status['video'].get('source_exists', False)}")
    print(f"Visual QA passed: {status['video'].get('qa_passed', False)}")
    print(f"Approved: {status['video'].get('approved', False)}")
    print(f"Final complete: {status['video'].get('final_complete', False)}")
    print(f"Next action: {status['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
