#!/usr/bin/env python3
"""Generate timestamped JSON/VTT transcripts for final lesson MP3 files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from google import genai

from transcription_core import (
    TranscriptionError,
    audio_duration_ms,
    build_prompt,
    config_fingerprint,
    existing_matches,
    part_timeline,
    reference_parts,
    render_vtt,
    sha256_file,
    transcribe_with_router,
)


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    if not isinstance(data, dict):
        raise TranscriptionError(f"Expected YAML mapping in {path}")
    return data


def settings_from(config: dict[str, Any]) -> dict[str, Any]:
    block = config.get("transcription", {}) or {}
    models = [
        str(model)
        for model in block.get(
            "models", ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
        )
    ]
    if not models:
        raise TranscriptionError("transcription.models cannot be empty")
    return {
        "enabled": bool(block.get("enabled", True)),
        "models": models,
        "attempts_per_model": int(block.get("attempts_per_model", 2)),
        "initial_delay_seconds": float(block.get("initial_delay_seconds", 3)),
        "max_delay_seconds": float(block.get("max_delay_seconds", 20)),
        "write_vtt": bool(block.get("write_vtt", True)),
    }


def discover(final_dir: Path) -> list[Path]:
    if not final_dir.exists():
        return []
    return sorted(path for path in final_dir.rglob("*.mp3") if path.is_file())


def transcript_path(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.stem}.transcript.json")


def write_outputs(
    audio_path: Path,
    *,
    lesson: Path,
    audio_hash: str,
    config_hash: str,
    model: str,
    duration_ms: int,
    parts: list[dict[str, Any]],
    payload: dict[str, Any],
    write_vtt: bool,
) -> None:
    output = {
        "schema_version": 1,
        "lesson": lesson.as_posix(),
        "source_audio": audio_path.as_posix(),
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "model": model,
        "duration_ms": duration_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parts": parts,
        "segments": payload["segments"],
        "words": payload["words"],
    }
    json_path = transcript_path(audio_path)
    temp = json_path.with_suffix(json_path.suffix + ".tmp")
    temp.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(json_path)

    if write_vtt:
        vtt = audio_path.with_name(f"{audio_path.stem}.transcript.vtt")
        temp_vtt = vtt.with_suffix(vtt.suffix + ".tmp")
        temp_vtt.write_text(render_vtt(payload["segments"]), encoding="utf-8")
        temp_vtt.replace(vtt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Timestamp final lesson audio")
    parser.add_argument("--config", type=Path, default=Path("tts_config.yaml"))
    parser.add_argument("--final", type=Path, default=Path("final"))
    parser.add_argument("--audio", type=Path, default=Path("audio"))
    parser.add_argument("--done", type=Path, default=Path("done"))
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    config = load_config(args.config)
    settings = settings_from(config)
    if not settings["enabled"]:
        print("Final audio transcription is disabled.")
        return 0

    audio_files = discover(args.final)
    if not audio_files:
        print("No final MP3 files found. Nothing to transcribe.")
        return 0
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GEMINI_API_KEY (or GOOGLE_API_KEY) is required.", file=sys.stderr)
        return 2

    gap_ms = int((config.get("assembly", {}) or {}).get("gap_ms", 300))
    config_hash = config_fingerprint(settings)
    client = genai.Client()
    failures: list[tuple[Path, str]] = []

    print(f"Found {len(audio_files)} final lesson(s).")
    print("Audio router: " + " -> ".join(settings["models"]))

    for index, audio_path in enumerate(audio_files):
        lesson = audio_path.relative_to(args.final).with_suffix("")
        audio_hash = sha256_file(audio_path)
        output_path = transcript_path(audio_path)
        if existing_matches(output_path, audio_hash, config_hash):
            print(f"- {lesson}: unchanged; reusing timestamp transcript")
            continue

        try:
            duration_ms = audio_duration_ms(
                audio_path.with_suffix(".wav"), audio_path.with_suffix(".json")
            )
            parts = part_timeline(args.audio, lesson, gap_ms)
            prompt = build_prompt(
                lesson, duration_ms, parts, reference_parts(args.done, lesson)
            )
            print(f"- {lesson}: transcribing {duration_ms / 1000:.1f}s")
            model, payload = transcribe_with_router(
                client,
                audio_path=audio_path,
                prompt=prompt,
                models=settings["models"],
                item_index=index,
                attempts_per_model=settings["attempts_per_model"],
                initial_delay=settings["initial_delay_seconds"],
                max_delay=settings["max_delay_seconds"],
                duration_ms=duration_ms,
            )
            write_outputs(
                audio_path,
                lesson=lesson,
                audio_hash=audio_hash,
                config_hash=config_hash,
                model=model,
                duration_ms=duration_ms,
                parts=parts,
                payload=payload,
                write_vtt=settings["write_vtt"],
            )
            print(
                f"  {model}: {len(payload['segments'])} segments, "
                f"{len(payload['words'])} timed words -> {output_path}"
            )
        except Exception as exc:
            failures.append((lesson, f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailed final-audio transcription:", file=sys.stderr)
        for lesson, reason in failures:
            print(f"- {lesson}: {reason}", file=sys.stderr)
        return 1

    print("All final lesson timing transcripts are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
