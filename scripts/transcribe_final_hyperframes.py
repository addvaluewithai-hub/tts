#!/usr/bin/env python3
"""Build schema-v2 word timings with HyperFrames' local transcription stack.

Qwen is the narration source of truth. This stage listens back to each generated
WAV part and derives word-level timings from the actual audio via
`hyperframes transcribe`, then offsets those timings into the final master.

No Gemini/API transcription is required for production synchronization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from transcription_core import (
    SCHEMA_VERSION,
    TranscriptionError,
    audio_duration_ms,
    part_timeline,
    reference_parts,
    reference_word_count,
    render_vtt,
    sha256_file,
)


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    if not isinstance(data, dict):
        raise TranscriptionError(f"Expected YAML mapping in {path}")
    return data


def settings_from(config: dict[str, Any]) -> dict[str, Any]:
    block = config.get("transcription", {}) or {}
    return {
        "enabled": bool(block.get("enabled", True)),
        "provider": str(block.get("provider", "hyperframes_whisper")),
        "engine": str(block.get("engine", "whisper")),
        "model": str(block.get("model", "small.en")),
        "language": str(block.get("language", "en")),
        "timeout_seconds": int(block.get("timeout_seconds", 1200)),
        "min_reference_coverage": float(block.get("min_reference_coverage", 0.72)),
        "write_vtt": bool(block.get("write_vtt", True)),
    }


def config_fingerprint(settings: dict[str, Any]) -> str:
    stable = {
        "schema_version": SCHEMA_VERSION,
        "alignment_mode": "per_part_hyperframes",
        **settings,
    }
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def discover(final_dir: Path) -> list[Path]:
    if not final_dir.exists():
        return []
    return sorted(path for path in final_dir.rglob("*.mp3") if path.is_file())


def transcript_path(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.stem}.transcript.json")


def cache_path(part_audio: Path) -> Path:
    return part_audio.with_suffix(".hyperframes-timing.json")


def load_cache(path: Path, *, audio_hash: str, config_hash: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        data.get("schema_version") == SCHEMA_VERSION
        and data.get("audio_sha256") == audio_hash
        and data.get("transcription_config_sha256") == config_hash
        and isinstance(data.get("words"), list)
        and data.get("words")
    ):
        return data
    return None


def parse_hyperframes_words(payload: Any, *, duration_ms: int, language: str) -> list[dict[str, Any]]:
    """Normalize HyperFrames transcript.json into Video Factory word objects."""
    if isinstance(payload, dict):
        raw_words = payload.get("words") or payload.get("transcript") or payload.get("items")
    else:
        raw_words = payload
    if not isinstance(raw_words, list) or not raw_words:
        raise TranscriptionError("HyperFrames produced no word timings")

    words: list[dict[str, Any]] = []
    for raw in raw_words:
        if not isinstance(raw, dict):
            continue
        token = str(raw.get("text", "")).strip()
        if not token:
            continue
        start = raw.get("start")
        end = raw.get("end")
        if start is None or end is None:
            continue
        start_ms = max(0, round(float(start) * 1000))
        end_ms = min(duration_ms, round(float(end) * 1000))
        if end_ms <= start_ms:
            end_ms = min(duration_ms, start_ms + 40)
        if start_ms >= duration_ms or end_ms <= start_ms:
            continue
        words.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": token,
                "language": language or "und",
            }
        )

    words.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    if not words:
        raise TranscriptionError("HyperFrames transcript contained no usable timed words")
    return words


def run_hyperframes_part(
    part_audio: Path,
    *,
    work_dir: Path,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    if not shutil.which("npx"):
        raise TranscriptionError("npx is required for HyperFrames word alignment")

    work_dir.mkdir(parents=True, exist_ok=True)
    output = work_dir / "transcript.json"
    if output.exists():
        output.unlink()

    command = [
        "npx",
        "--yes",
        "hyperframes@latest",
        "transcribe",
        str(part_audio.resolve()),
        "--dir",
        str(work_dir.resolve()),
        "--json",
        "--engine",
        settings["engine"],
        "--model",
        settings["model"],
    ]
    if settings["language"]:
        command += ["--language", settings["language"]]

    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=settings["timeout_seconds"],
        check=False,
    )
    if completed.returncode:
        tail = (completed.stderr or completed.stdout or "hyperframes transcribe failed")[-2500:]
        raise TranscriptionError(f"HyperFrames transcription failed: {tail}")
    if not output.exists():
        raise TranscriptionError(
            "hyperframes transcribe succeeded but transcript.json was not written"
        )

    payload = json.loads(output.read_text(encoding="utf-8"))
    duration_ms = round(_wav_duration_seconds(part_audio) * 1000)
    return parse_hyperframes_words(
        payload,
        duration_ms=duration_ms,
        language=settings["language"] or "und",
    )


def _wav_duration_seconds(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def coverage_ok(words: list[dict[str, Any]], reference: str, minimum: float) -> tuple[bool, float]:
    expected = reference_word_count(reference)
    if expected <= 0:
        return True, 1.0
    ratio = len(words) / expected
    return ratio >= minimum, ratio


def write_cache(
    path: Path,
    *,
    audio_hash: str,
    config_hash: str,
    settings: dict[str, Any],
    duration_ms: int,
    words: list[dict[str, Any]],
) -> dict[str, Any]:
    data = {
        "schema_version": SCHEMA_VERSION,
        "provider": "hyperframes",
        "engine": settings["engine"],
        "model": settings["model"],
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "duration_ms": duration_ms,
        "language": settings["language"] or "und",
        "text": " ".join(word["text"] for word in words),
        "words": words,
    }
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)
    return data


def consolidate(
    parts: list[dict[str, Any]], caches: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    enriched_parts: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []

    for index, (part, cache) in enumerate(zip(parts, caches, strict=True)):
        segment_words = cache["words"]
        text = cache.get("text") or " ".join(word["text"] for word in segment_words)
        segments.append(
            {
                "start_ms": part["start_ms"],
                "end_ms": part["end_ms"],
                "speaker": "teacher",
                "language": cache.get("language", "und"),
                "text": text,
            }
        )
        for word in segment_words:
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
            provider="hyperframes",
            engine=cache.get("engine"),
            model=cache.get("model"),
            word_count=len(segment_words),
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
    settings: dict[str, Any],
    parts: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    words: list[dict[str, Any]],
) -> None:
    output = {
        "schema_version": SCHEMA_VERSION,
        "alignment_mode": "per_part_hyperframes",
        "alignment_provider": "hyperframes",
        "alignment_engine": settings["engine"],
        "alignment_model": settings["model"],
        "lesson": lesson.as_posix(),
        "source_audio": audio_path.as_posix(),
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
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

    if settings["write_vtt"]:
        vtt = audio_path.with_name(f"{audio_path.stem}.transcript.vtt")
        temp_vtt = vtt.with_suffix(vtt.suffix + ".tmp")
        temp_vtt.write_text(render_vtt(segments), encoding="utf-8")
        temp_vtt.replace(vtt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Timestamp final audio using HyperFrames local ASR")
    parser.add_argument("--config", type=Path, default=Path("tts_config.yaml"))
    parser.add_argument("--final", type=Path, default=Path("final"))
    parser.add_argument("--audio", type=Path, default=Path("audio"))
    parser.add_argument("--done", type=Path, default=Path("done"))
    parser.add_argument("--cache", type=Path, default=Path(".factory-cache/hyperframes-transcribe"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    settings = settings_from(config)
    if not settings["enabled"]:
        print("Final audio transcription is disabled.")
        return 0
    if settings["provider"] not in {"hyperframes", "hyperframes_whisper"}:
        print(
            f"ERROR: unsupported production transcription provider {settings['provider']!r}; "
            "expected hyperframes_whisper",
            file=sys.stderr,
        )
        return 2

    final_audio = discover(args.final)
    if not final_audio:
        print("No final MP3 files found. Nothing to transcribe.")
        return 0

    gap_ms = int((config.get("assembly", {}) or {}).get("gap_ms", 300))
    config_hash = config_fingerprint(settings)
    failures: list[tuple[Path, str]] = []

    print(f"Found {len(final_audio)} final lesson(s).")
    print(
        f"Alignment: HyperFrames {settings['engine']} / {settings['model']} "
        f"language={settings['language'] or 'auto'}"
    )

    for final_mp3 in final_audio:
        lesson = final_mp3.relative_to(args.final).with_suffix("")
        final_hash = sha256_file(final_mp3)
        try:
            duration_ms = audio_duration_ms(
                final_mp3.with_suffix(".wav"), final_mp3.with_suffix(".json")
            )
            parts = part_timeline(args.audio, lesson, gap_ms)
            if not parts:
                raise TranscriptionError(f"No source WAV parts found for {lesson}")
            references = reference_parts(args.done, lesson)
            caches: list[dict[str, Any]] = []

            print(f"- {lesson}: aligning {len(parts)} Qwen WAV part(s)")
            for part in parts:
                part_audio = args.audio / lesson / part["file"]
                part_hash = sha256_file(part_audio)
                cache_file = cache_path(part_audio)
                cache = load_cache(cache_file, audio_hash=part_hash, config_hash=config_hash)
                if cache:
                    print(f"    {part['file']}: cached ({len(cache['words'])} words)")
                    caches.append(cache)
                    continue

                work_dir = args.cache / lesson / Path(part["file"]).stem
                words = run_hyperframes_part(
                    part_audio,
                    work_dir=work_dir,
                    settings=settings,
                )
                reference = references.get(Path(part["file"]).stem, "")
                okay, ratio = coverage_ok(
                    words,
                    reference,
                    settings["min_reference_coverage"],
                )
                if not okay:
                    raise TranscriptionError(
                        f"{part['file']}: word coverage {ratio:.0%} is below "
                        f"{settings['min_reference_coverage']:.0%} of source transcript"
                    )
                cache = write_cache(
                    cache_file,
                    audio_hash=part_hash,
                    config_hash=config_hash,
                    settings=settings,
                    duration_ms=int(part["duration_ms"]),
                    words=words,
                )
                caches.append(cache)
                print(f"    {part['file']}: {len(words)} timed words, coverage={ratio:.0%}")

            enriched_parts, segments, words = consolidate(parts, caches)
            if not words:
                raise TranscriptionError("No global word timings produced")
            if words[-1]["end_ms"] > duration_ms:
                raise TranscriptionError("Global word timing exceeds final audio duration")

            write_final_outputs(
                final_mp3,
                lesson=lesson,
                audio_hash=final_hash,
                config_hash=config_hash,
                duration_ms=duration_ms,
                settings=settings,
                parts=enriched_parts,
                segments=segments,
                words=words,
            )
            print(
                f"  complete: {len(segments)} segments, {len(words)} timed words -> "
                f"{transcript_path(final_mp3)}"
            )
        except Exception as exc:
            failures.append((lesson, f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailed HyperFrames alignment:", file=sys.stderr)
        for lesson, reason in failures:
            print(f"- {lesson}: {reason}", file=sys.stderr)
        return 1

    print("All final-audio HyperFrames word alignments are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
