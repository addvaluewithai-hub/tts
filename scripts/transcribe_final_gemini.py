#!/usr/bin/env python3
"""Build exact word timings with Gemini 3.5 Transcribe.

The rendered Qwen audio is authoritative for timing. The source transcript is
used only as a canonical-text layer after Gemini returns official word-level
start/end offsets, so formatting differences such as "$200" vs "two hundred
dollars" do not break visual anchors.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from google import genai
from google.genai import errors

from transcription_core import (
    SCHEMA_VERSION,
    TranscriptionError,
    audio_duration_ms,
    part_timeline,
    reference_parts,
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
        "model": str(block.get("gemini_model", "gemini-3.5-transcribe")),
        "language_codes": list(block.get("language_codes", ["en-US"])),
        "min_reference_coverage": float(block.get("min_reference_coverage", 0.72)),
        "attempts": int(block.get("gemini_attempts", 3)),
        "initial_delay_seconds": float(block.get("initial_delay_seconds", 3)),
        "max_delay_seconds": float(block.get("max_delay_seconds", 20)),
        "write_vtt": bool(block.get("write_vtt", True)),
    }


def config_fingerprint(settings: dict[str, Any]) -> str:
    stable = {
        "schema_version": SCHEMA_VERSION,
        "alignment_mode": "per_part_gemini_transcribe",
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
    return part_audio.with_suffix(".gemini-transcribe-timing.json")


def parse_offset_ms(value: Any) -> int:
    if value is None:
        raise TranscriptionError("Gemini word annotation is missing a time offset")
    if isinstance(value, (int, float)):
        return round(float(value) * 1000)
    text = str(value).strip().lower()
    if text.endswith("ms"):
        return round(float(text[:-2]))
    if text.endswith("s"):
        return round(float(text[:-1]) * 1000)
    return round(float(text) * 1000)


def extract_word_annotations(interaction: Any, *, duration_ms: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for step in getattr(interaction, "steps", []) or []:
        for content in getattr(step, "content", []) or []:
            for annotation in getattr(content, "annotations", []) or []:
                if getattr(annotation, "type", None) != "word_info":
                    continue
                token = str(getattr(annotation, "text", "") or "").strip()
                if not token:
                    continue
                start_ms = max(0, parse_offset_ms(getattr(annotation, "start_offset", None)))
                end_ms = min(duration_ms, parse_offset_ms(getattr(annotation, "end_offset", None)))
                if end_ms <= start_ms:
                    end_ms = min(duration_ms, start_ms + 30)
                if start_ms >= duration_ms or end_ms <= start_ms:
                    continue
                result.append(
                    {
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "text": token,
                        "language": "en",
                    }
                )
    result.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    if not result:
        raise TranscriptionError("Gemini returned no word_info timestamp annotations")
    return result


def normalize_token(value: str) -> str:
    return "".join(re.findall(r"[\w]+", value.lower(), flags=re.UNICODE))


def reference_tokens(reference: str) -> list[str]:
    return [token for token in re.findall(r"\S+", reference.strip()) if normalize_token(token)]


def _distributed_words(tokens: list[str], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    if not tokens:
        return []
    span = max(len(tokens) * 30, end_ms - start_ms)
    end_ms = max(end_ms, start_ms + span)
    weights = [max(1, len(normalize_token(token))) for token in tokens]
    total = sum(weights)
    cursor = start_ms
    words: list[dict[str, Any]] = []
    consumed = 0
    for index, (token, weight) in enumerate(zip(tokens, weights, strict=True)):
        consumed += weight
        token_end = end_ms if index == len(tokens) - 1 else start_ms + round(span * consumed / total)
        token_end = max(cursor + 20, token_end)
        words.append(
            {
                "start_ms": cursor,
                "end_ms": token_end,
                "text": token,
                "language": "en",
            }
        )
        cursor = token_end
    return words


def canonicalize_to_reference(
    raw_words: list[dict[str, Any]],
    reference: str,
    *,
    duration_ms: int,
) -> tuple[list[dict[str, Any]], float]:
    refs = reference_tokens(reference)
    if not refs:
        return raw_words, 1.0

    ref_norm = [normalize_token(token) for token in refs]
    raw_norm = [normalize_token(word["text"]) for word in raw_words]
    matcher = difflib.SequenceMatcher(a=ref_norm, b=raw_norm, autojunk=False)
    canonical: list[dict[str, Any]] = []
    exact_reference_words = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        ref_slice = refs[i1:i2]
        raw_slice = raw_words[j1:j2]
        if tag == "equal":
            exact_reference_words += len(ref_slice)
            for ref_token, raw_word in zip(ref_slice, raw_slice, strict=True):
                canonical.append({**raw_word, "text": ref_token})
            continue

        if tag == "insert":
            # Gemini heard an extra token. It has no source-script word, so do not
            # expose it as a visual anchor.
            continue

        if raw_slice:
            start_ms = raw_slice[0]["start_ms"]
            end_ms = raw_slice[-1]["end_ms"]
        else:
            prev_end = canonical[-1]["end_ms"] if canonical else 0
            next_start = raw_words[j1]["start_ms"] if j1 < len(raw_words) else duration_ms
            start_ms, end_ms = prev_end, max(prev_end + 30 * len(ref_slice), next_start)

        canonical.extend(_distributed_words(ref_slice, start_ms, min(duration_ms, end_ms)))

    canonical.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    # Clamp any interpolation edge cases while keeping monotonic timing.
    previous_end = 0
    for word in canonical:
        word["start_ms"] = max(previous_end, min(duration_ms, int(word["start_ms"])))
        word["end_ms"] = max(word["start_ms"] + 1, min(duration_ms, int(word["end_ms"])))
        previous_end = word["end_ms"]

    coverage = exact_reference_words / max(1, len(refs))
    return canonical, coverage


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


def transcribe_part(
    client: genai.Client,
    part_audio: Path,
    *,
    settings: dict[str, Any],
    duration_ms: int,
) -> tuple[str, list[dict[str, Any]]]:
    uploaded = client.files.upload(
        file=str(part_audio),
        config={"mime_type": "audio/wav", "display_name": part_audio.name},
    )
    failures: list[str] = []
    try:
        for attempt in range(1, settings["attempts"] + 1):
            try:
                interaction = client.interactions.create(
                    model=settings["model"],
                    input=[
                        {
                            "type": "audio",
                            "uri": uploaded.uri,
                            "mime_type": uploaded.mime_type or "audio/wav",
                        }
                    ],
                    generation_config={
                        "transcription_config": {
                            "language_codes": settings["language_codes"],
                            "mode": {
                                "type": "verbatim",
                                "timestamp_granularities": ["word"],
                            },
                        }
                    },
                )
                words = extract_word_annotations(interaction, duration_ms=duration_ms)
                text = str(getattr(interaction, "output_text", "") or "").strip()
                return text, words
            except errors.APIError as exc:
                status = getattr(exc, "code", None)
                failures.append(f"attempt {attempt}: API {status}: {exc}")
                retryable = status == 429 or (isinstance(status, int) and 500 <= status <= 599)
                if not retryable or attempt >= settings["attempts"]:
                    break
                delay = min(
                    settings["max_delay_seconds"],
                    settings["initial_delay_seconds"] * 2 ** (attempt - 1),
                ) + random.uniform(0, 1)
                print(f"      Gemini retrying in {delay:.1f}s")
                time.sleep(delay)
        raise TranscriptionError("Gemini transcription failed: " + " | ".join(failures))
    finally:
        try:
            if getattr(uploaded, "name", None):
                client.files.delete(name=uploaded.name)
        except Exception as exc:
            print(f"Warning: could not delete uploaded Gemini file: {exc}", file=sys.stderr)


def write_cache(
    path: Path,
    *,
    audio_hash: str,
    config_hash: str,
    settings: dict[str, Any],
    duration_ms: int,
    recognized_text: str,
    raw_words: list[dict[str, Any]],
    canonical_words: list[dict[str, Any]],
    reference: str,
    coverage: float,
) -> dict[str, Any]:
    data = {
        "schema_version": SCHEMA_VERSION,
        "provider": "gemini",
        "model": settings["model"],
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "duration_ms": duration_ms,
        "language": "en",
        "recognized_text": recognized_text,
        "reference_text": reference,
        "exact_reference_coverage": coverage,
        "raw_words": raw_words,
        "words": canonical_words,
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
        reference_text = cache.get("reference_text") or " ".join(word["text"] for word in segment_words)
        segments.append(
            {
                "start_ms": part["start_ms"],
                "end_ms": part["end_ms"],
                "speaker": "teacher",
                "language": "en",
                "text": reference_text,
            }
        )
        for word in segment_words:
            words.append(
                {
                    "start_ms": part["start_ms"] + int(word["start_ms"]),
                    "end_ms": part["start_ms"] + int(word["end_ms"]),
                    "text": word["text"],
                    "language": "en",
                    "segment_index": index,
                }
            )
        enriched = dict(part)
        enriched.update(
            provider="gemini",
            model=cache.get("model"),
            word_count=len(segment_words),
            raw_word_count=len(cache.get("raw_words", [])),
            exact_reference_coverage=cache.get("exact_reference_coverage"),
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
        "alignment_mode": "per_part_gemini_transcribe",
        "alignment_provider": "gemini",
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
    parser = argparse.ArgumentParser(description="Timestamp final audio with Gemini 3.5 Transcribe")
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
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GEMINI_API_KEY (or GOOGLE_API_KEY) is required.", file=sys.stderr)
        return 2

    final_audio = discover(args.final)
    if not final_audio:
        print("No final MP3 files found. Nothing to align.")
        return 0

    gap_ms = int((config.get("assembly", {}) or {}).get("gap_ms", 300))
    config_hash = config_fingerprint(settings)
    client = genai.Client()
    failures: list[tuple[Path, str]] = []

    print(f"Found {len(final_audio)} final lesson(s).")
    print(f"Alignment: {settings['model']} with official word timestamps")

    for final_mp3 in final_audio:
        lesson = final_mp3.relative_to(args.final).with_suffix("")
        try:
            final_hash = sha256_file(final_mp3)
            duration_ms = audio_duration_ms(final_mp3.with_suffix(".wav"), final_mp3.with_suffix(".json"))
            parts = part_timeline(args.audio, lesson, gap_ms)
            if not parts:
                raise TranscriptionError(f"No source WAV parts found for {lesson}")
            references = reference_parts(args.done, lesson)
            caches: list[dict[str, Any]] = []

            print(f"- {lesson}: aligning {len(parts)} approved Qwen part(s)")
            for part in parts:
                part_audio = args.audio / lesson / part["file"]
                part_hash = sha256_file(part_audio)
                cache_file = cache_path(part_audio)
                cache = load_cache(cache_file, audio_hash=part_hash, config_hash=config_hash)
                if cache:
                    print(f"    {part['file']}: cached ({len(cache['words'])} canonical words)")
                    caches.append(cache)
                    continue

                reference = references.get(Path(part["file"]).stem, "")
                recognized_text, raw_words = transcribe_part(
                    client,
                    part_audio,
                    settings=settings,
                    duration_ms=int(part["duration_ms"]),
                )
                canonical_words, coverage = canonicalize_to_reference(
                    raw_words,
                    reference,
                    duration_ms=int(part["duration_ms"]),
                )
                if reference and coverage < settings["min_reference_coverage"]:
                    raise TranscriptionError(
                        f"{part['file']}: exact reference coverage {coverage:.0%} is below "
                        f"{settings['min_reference_coverage']:.0%}"
                    )
                cache = write_cache(
                    cache_file,
                    audio_hash=part_hash,
                    config_hash=config_hash,
                    settings=settings,
                    duration_ms=int(part["duration_ms"]),
                    recognized_text=recognized_text,
                    raw_words=raw_words,
                    canonical_words=canonical_words,
                    reference=reference,
                    coverage=coverage,
                )
                caches.append(cache)
                print(
                    f"    {part['file']}: {len(raw_words)} Gemini words -> "
                    f"{len(canonical_words)} script words, exact coverage={coverage:.0%}"
                )

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
                f"  complete: {len(segments)} segments, {len(words)} canonical timed words -> "
                f"{transcript_path(final_mp3)}"
            )
        except Exception as exc:
            failures.append((lesson, f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailed Gemini alignment:", file=sys.stderr)
        for lesson, reason in failures:
            print(f"- {lesson}: {reason}", file=sys.stderr)
        return 1

    print("All Gemini word alignments are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
