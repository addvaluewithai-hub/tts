#!/usr/bin/env python3
"""Build complete lesson-wide word timings from short TTS audio parts."""

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
    SCHEMA_VERSION,
    TranscriptionError,
    audio_duration_ms,
    build_part_prompt,
    config_fingerprint,
    existing_matches,
    load_part_cache,
    part_cache_path,
    part_timeline,
    reference_parts,
    reference_word_count,
    render_vtt,
    sha256_file,
    transcribe_part_with_router,
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


def write_part_cache(
    path: Path,
    *,
    audio_hash: str,
    config_hash: str,
    model: str,
    duration_ms: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    data = {
        "schema_version": SCHEMA_VERSION,
        "source_audio": path.with_name(path.name.replace(".timing.json", ".wav")).as_posix(),
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "model": model,
        "duration_ms": duration_ms,
        "text": payload["text"],
        "language": payload["language"],
        "words": payload["words"],
    }
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)
    return data


def consolidate(
    parts: list[dict[str, Any]], caches: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []
    enriched_parts: list[dict[str, Any]] = []

    for index, (part, cache) in enumerate(zip(parts, caches, strict=True)):
        segments.append(
            {
                "start_ms": part["start_ms"],
                "end_ms": part["end_ms"],
                "speaker": "teacher",
                "language": cache.get("language", "und"),
                "text": cache["text"],
            }
        )
        for word in cache["words"]:
            words.append(
                {
                    "start_ms": part["start_ms"] + int(word["start_ms"]),
                    "end_ms": part["start_ms"] + int(word["end_ms"]),
                    "text": word["text"],
                    "language": word.get("language", "und"),
                    "segment_index": index,
                }
            )
        enriched = dict(part)
        enriched.update(
            model=cache.get("model"),
            word_count=len(cache["words"]),
            audio_sha256=cache.get("audio_sha256"),
        )
        enriched_parts.append(enriched)

    words.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    return enriched_parts, segments, words


def write_final_outputs(
    audio_path: Path,
    *,
    lesson: Path,
    audio_hash: str,
    config_hash: str,
    duration_ms: int,
    models: list[str],
    parts: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    words: list[dict[str, Any]],
    write_vtt: bool,
) -> None:
    output = {
        "schema_version": SCHEMA_VERSION,
        "alignment_mode": "per_part",
        "lesson": lesson.as_posix(),
        "source_audio": audio_path.as_posix(),
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "model_router": models,
        "duration_ms": duration_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parts": parts,
        "segments": segments,
        "words": words,
    }
    json_path = transcript_path(audio_path)
    temp = json_path.with_suffix(json_path.suffix + ".tmp")
    temp.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(json_path)

    if write_vtt:
        vtt = audio_path.with_name(f"{audio_path.stem}.transcript.vtt")
        temp_vtt = vtt.with_suffix(vtt.suffix + ".tmp")
        temp_vtt.write_text(render_vtt(segments), encoding="utf-8")
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

    final_audio = discover(args.final)
    if not final_audio:
        print("No final MP3 files found. Nothing to transcribe.")
        return 0
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GEMINI_API_KEY (or GOOGLE_API_KEY) is required.", file=sys.stderr)
        return 2

    gap_ms = int((config.get("assembly", {}) or {}).get("gap_ms", 300))
    config_hash = config_fingerprint(settings)
    client = genai.Client()
    failures: list[tuple[Path, str]] = []

    print(f"Found {len(final_audio)} final lesson(s).")
    print("Audio router: " + " -> ".join(settings["models"]))

    for lesson_index, final_mp3 in enumerate(final_audio):
        lesson = final_mp3.relative_to(args.final).with_suffix("")
        final_hash = sha256_file(final_mp3)
        output = transcript_path(final_mp3)
        if existing_matches(output, final_hash, config_hash):
            print(f"- {lesson}: unchanged; reusing complete word alignment")
            continue

        try:
            duration_ms = audio_duration_ms(
                final_mp3.with_suffix(".wav"), final_mp3.with_suffix(".json")
            )
            parts = part_timeline(args.audio, lesson, gap_ms)
            if not parts:
                raise TranscriptionError(f"No source WAV parts found for {lesson}")
            references = reference_parts(args.done, lesson)
            caches: list[dict[str, Any]] = []

            print(f"- {lesson}: aligning {len(parts)} short audio parts")
            for part_index, part in enumerate(parts):
                part_audio = args.audio / lesson / part["file"]
                part_hash = sha256_file(part_audio)
                cache_path = part_cache_path(part_audio)
                cache = load_part_cache(cache_path, part_hash, config_hash)
                if cache:
                    print(f"    {part['file']}: cached ({len(cache['words'])} words)")
                    caches.append(cache)
                    continue

                reference = references.get(Path(part["file"]).stem, "")
                prompt = build_part_prompt(
                    part["file"], int(part["duration_ms"]), reference
                )
                route_index = lesson_index + part_index
                model, payload = transcribe_part_with_router(
                    client,
                    audio_path=part_audio,
                    prompt=prompt,
                    models=settings["models"],
                    item_index=route_index,
                    attempts_per_model=settings["attempts_per_model"],
                    initial_delay=settings["initial_delay_seconds"],
                    max_delay=settings["max_delay_seconds"],
                    duration_ms=int(part["duration_ms"]),
                    expected_words=reference_word_count(reference),
                )
                cache = write_part_cache(
                    cache_path,
                    audio_hash=part_hash,
                    config_hash=config_hash,
                    model=model,
                    duration_ms=int(part["duration_ms"]),
                    payload=payload,
                )
                caches.append(cache)
                print(
                    f"    {part['file']}: {model}, {len(payload['words'])} timed words"
                )

            enriched_parts, segments, words = consolidate(parts, caches)
            if not words:
                raise TranscriptionError("No global word timings produced")
            if words[-1]["end_ms"] > duration_ms:
                raise TranscriptionError("Global word timing exceeds final lesson duration")

            write_final_outputs(
                final_mp3,
                lesson=lesson,
                audio_hash=final_hash,
                config_hash=config_hash,
                duration_ms=duration_ms,
                models=settings["models"],
                parts=enriched_parts,
                segments=segments,
                words=words,
                write_vtt=settings["write_vtt"],
            )
            print(
                f"  complete: {len(segments)} segments, {len(words)} timed words "
                f"-> {output}"
            )
        except Exception as exc:
            failures.append((lesson, f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailed final-audio transcription:", file=sys.stderr)
        for lesson, reason in failures:
            print(f"- {lesson}: {reason}", file=sys.stderr)
        return 1

    print("All final lesson timing transcripts are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
