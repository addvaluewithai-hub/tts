#!/usr/bin/env python3
"""Build exact word timings with one Gemini 3.5 Transcribe request per final audio.

The rendered Qwen master audio is authoritative for timing. Gemini returns
official word-level offsets for the whole file in a single request. We then
slice those recognized words back into the known Qwen part boundaries and map
them onto the source transcript for canonical spelling and visual anchors.

This deliberately avoids one API request per audio part: a three-minute video
fits comfortably inside Gemini Transcribe's file-processing limits, and one
master request is much friendlier to low request quotas.
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
        "attempts": int(block.get("gemini_attempts", 4)),
        "initial_delay_seconds": float(block.get("initial_delay_seconds", 5)),
        "max_delay_seconds": float(block.get("max_delay_seconds", 90)),
        "write_vtt": bool(block.get("write_vtt", True)),
    }


def config_fingerprint(settings: dict[str, Any]) -> str:
    stable = {
        "schema_version": SCHEMA_VERSION,
        "alignment_mode": "whole_audio_gemini_transcribe",
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


def raw_cache_path(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.stem}.gemini-transcribe-raw.json")


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
    """Interpolate source-script tokens across one recognized replacement span."""
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
    """Map Gemini-recognized words to our source text without changing timing truth."""
    refs = reference_tokens(reference)
    if not refs:
        return raw_words, 1.0
    if not raw_words:
        raise TranscriptionError("No recognized words available for a referenced audio part")

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
            # Extra recognized token: keep the audio truth internally but do not
            # expose a visual anchor that does not exist in the approved script.
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
    previous_end = 0
    for word in canonical:
        word["start_ms"] = max(previous_end, min(duration_ms, int(word["start_ms"])))
        word["end_ms"] = max(word["start_ms"] + 1, min(duration_ms, int(word["end_ms"])))
        previous_end = word["end_ms"]

    coverage = exact_reference_words / max(1, len(refs))
    return canonical, coverage


def retry_delay_from_error(exc: Exception) -> float | None:
    """Extract provider retry guidance such as 'Please retry in 47.9s'."""
    match = re.search(r"retry in\s+([0-9.]+)s", str(exc), flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def transcribe_master(
    client: genai.Client,
    audio_path: Path,
    *,
    settings: dict[str, Any],
    duration_ms: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Upload and transcribe the full master in exactly one successful API call."""
    uploaded = client.files.upload(file=str(audio_path))
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
                            "mime_type": uploaded.mime_type or "audio/mpeg",
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
                exponential = settings["initial_delay_seconds"] * 2 ** (attempt - 1)
                provider_hint = retry_delay_from_error(exc) or 0
                delay = min(settings["max_delay_seconds"], max(exponential, provider_hint + 1))
                delay += random.uniform(0, 1)
                print(f"      Gemini retrying master request in {delay:.1f}s")
                time.sleep(delay)
        raise TranscriptionError("Gemini master transcription failed: " + " | ".join(failures))
    finally:
        try:
            if getattr(uploaded, "name", None):
                client.files.delete(name=uploaded.name)
        except Exception as exc:
            print(f"Warning: could not delete uploaded Gemini file: {exc}", file=sys.stderr)


def load_raw_cache(path: Path, *, audio_hash: str, config_hash: str) -> dict[str, Any] | None:
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
        and isinstance(data.get("raw_words"), list)
        and data.get("raw_words")
    ):
        return data
    return None


def write_raw_cache(
    path: Path,
    *,
    audio_hash: str,
    config_hash: str,
    settings: dict[str, Any],
    duration_ms: int,
    recognized_text: str,
    raw_words: list[dict[str, Any]],
) -> dict[str, Any]:
    data = {
        "schema_version": SCHEMA_VERSION,
        "provider": "gemini",
        "model": settings["model"],
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "duration_ms": duration_ms,
        "recognized_text": recognized_text,
        "raw_words": raw_words,
    }
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)
    return data


def words_for_part(raw_words: list[dict[str, Any]], part: dict[str, Any]) -> list[dict[str, Any]]:
    """Slice global timestamps by a known Qwen part boundary and make them relative."""
    part_start = int(part["start_ms"])
    part_end = int(part["end_ms"])
    duration = int(part["duration_ms"])
    selected: list[dict[str, Any]] = []
    for word in raw_words:
        midpoint = (int(word["start_ms"]) + int(word["end_ms"])) / 2
        if midpoint < part_start or midpoint > part_end:
            continue
        start = max(0, int(word["start_ms"]) - part_start)
        end = min(duration, int(word["end_ms"]) - part_start)
        if end <= start:
            end = min(duration, start + 20)
        if end > start:
            selected.append({**word, "start_ms": start, "end_ms": end})
    return selected


def build_part_alignment(
    *,
    parts: list[dict[str, Any]],
    raw_words: list[dict[str, Any]],
    references: dict[str, str],
    settings: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    enriched_parts: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []

    for index, part in enumerate(parts):
        reference = references.get(Path(part["file"]).stem, "")
        relative_raw = words_for_part(raw_words, part)
        if not relative_raw:
            raise TranscriptionError(f"{part['file']}: Gemini returned no words inside this part boundary")

        canonical, coverage = canonicalize_to_reference(
            relative_raw,
            reference,
            duration_ms=int(part["duration_ms"]),
        )
        if reference and coverage < settings["min_reference_coverage"]:
            raise TranscriptionError(
                f"{part['file']}: exact reference coverage {coverage:.0%} is below "
                f"{settings['min_reference_coverage']:.0%}"
            )

        segment_text = reference or " ".join(word["text"] for word in canonical)
        segments.append(
            {
                "start_ms": int(part["start_ms"]),
                "end_ms": int(part["end_ms"]),
                "speaker": "teacher",
                "language": "en",
                "text": segment_text,
            }
        )
        for word in canonical:
            words.append(
                {
                    "start_ms": int(part["start_ms"]) + int(word["start_ms"]),
                    "end_ms": int(part["start_ms"]) + int(word["end_ms"]),
                    "text": word["text"],
                    "language": "en",
                    "segment_index": index,
                }
            )
        enriched = dict(part)
        enriched.update(
            provider="gemini",
            model=settings["model"],
            word_count=len(canonical),
            raw_word_count=len(relative_raw),
            exact_reference_coverage=coverage,
        )
        enriched_parts.append(enriched)
        print(
            f"    {part['file']}: {len(relative_raw)} Gemini words -> "
            f"{len(canonical)} script words, exact coverage={coverage:.0%}"
        )

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
    raw_word_count: int,
) -> None:
    output = {
        "schema_version": SCHEMA_VERSION,
        "alignment_mode": "whole_audio_gemini_transcribe",
        "alignment_provider": "gemini",
        "alignment_model": settings["model"],
        "lesson": lesson.as_posix(),
        "source_audio": audio_path.as_posix(),
        "audio_sha256": audio_hash,
        "transcription_config_sha256": config_hash,
        "duration_ms": duration_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_word_count": raw_word_count,
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
    print(f"Alignment: one {settings['model']} master request with official word timestamps")

    for final_mp3 in final_audio:
        lesson = final_mp3.relative_to(args.final).with_suffix("")
        try:
            final_hash = sha256_file(final_mp3)
            duration_ms = audio_duration_ms(final_mp3.with_suffix(".wav"), final_mp3.with_suffix(".json"))
            parts = part_timeline(args.audio, lesson, gap_ms)
            if not parts:
                raise TranscriptionError(f"No source WAV parts found for {lesson}")
            references = reference_parts(args.done, lesson)

            cache_file = raw_cache_path(final_mp3)
            raw_cache = load_raw_cache(cache_file, audio_hash=final_hash, config_hash=config_hash)
            if raw_cache:
                recognized_text = str(raw_cache.get("recognized_text", ""))
                raw_words = list(raw_cache["raw_words"])
                print(f"- {lesson}: reusing cached master transcription ({len(raw_words)} raw words)")
            else:
                print(f"- {lesson}: transcribing full {duration_ms / 1000:.1f}s master in one API request")
                recognized_text, raw_words = transcribe_master(
                    client,
                    final_mp3,
                    settings=settings,
                    duration_ms=duration_ms,
                )
                write_raw_cache(
                    cache_file,
                    audio_hash=final_hash,
                    config_hash=config_hash,
                    settings=settings,
                    duration_ms=duration_ms,
                    recognized_text=recognized_text,
                    raw_words=raw_words,
                )
                print(f"  master: {len(raw_words)} Gemini word timestamps")

            enriched_parts, segments, words = build_part_alignment(
                parts=parts,
                raw_words=raw_words,
                references=references,
                settings=settings,
            )
            if not words:
                raise TranscriptionError("No canonical word timings produced")
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
                raw_word_count=len(raw_words),
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

    print("All final-audio Gemini word alignments are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
