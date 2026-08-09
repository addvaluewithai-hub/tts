"""Helpers for timestamping final lesson audio with Gemini."""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
import time
import wave
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors

SCHEMA_VERSION = 1
REFERENCE_EXTENSIONS = {".txt", ".md"}

TRANSCRIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_ms": {"type": "integer", "minimum": 0},
                    "end_ms": {"type": "integer", "minimum": 0},
                    "speaker": {"type": "string"},
                    "language": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["start_ms", "end_ms", "speaker", "language", "text"],
            },
        },
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_ms": {"type": "integer", "minimum": 0},
                    "end_ms": {"type": "integer", "minimum": 0},
                    "text": {"type": "string"},
                    "language": {"type": "string"},
                    "segment_index": {"type": "integer", "minimum": 0},
                },
                "required": ["start_ms", "end_ms", "text", "language", "segment_index"],
            },
        },
    },
    "required": ["segments", "words"],
}


class TranscriptionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def config_fingerprint(settings: dict[str, Any]) -> str:
    stable = {
        "schema_version": SCHEMA_VERSION,
        "models": settings["models"],
        "attempts_per_model": settings["attempts_per_model"],
        "prompt_version": 1,
    }
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def route_order(models: list[str], item_index: int) -> list[str]:
    if not models:
        raise TranscriptionError("No transcription models configured")
    offset = item_index % len(models)
    return models[offset:] + models[:offset]


def audio_duration_ms(final_wav: Path, manifest: Path) -> int:
    if final_wav.exists():
        with wave.open(str(final_wav), "rb") as wf:
            return round(wf.getnframes() / wf.getframerate() * 1000)
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return round(float(data["duration_seconds"]) * 1000)
    raise TranscriptionError(f"Cannot determine duration for {final_wav}")


def part_timeline(audio_dir: Path, lesson: Path, gap_ms: int) -> list[dict[str, Any]]:
    lesson_dir = audio_dir / lesson
    if not lesson_dir.exists():
        return []
    parts = sorted(path for path in lesson_dir.glob("*.wav") if path.is_file())
    cursor = 0
    result: list[dict[str, Any]] = []
    for index, part in enumerate(parts):
        with wave.open(str(part), "rb") as wf:
            duration = round(wf.getnframes() / wf.getframerate() * 1000)
        result.append({"file": part.name, "start_ms": cursor, "end_ms": cursor + duration})
        cursor += duration
        if index != len(parts) - 1:
            cursor += gap_ms
    return result


def strip_front_matter(text: str) -> str:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    return text if end == -1 else text[end + 5 :]


def clean_reference_text(text: str) -> str:
    text = strip_front_matter(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[[A-Z][A-Z0-9 ,_-]*\]\s*", "", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()


def reference_parts(done_dir: Path, lesson: Path) -> list[dict[str, str]]:
    lesson_dir = done_dir / lesson
    if not lesson_dir.exists():
        return []
    result = []
    for path in sorted(p for p in lesson_dir.iterdir() if p.is_file()):
        if path.suffix.lower() not in REFERENCE_EXTENSIONS:
            continue
        cleaned = clean_reference_text(path.read_text(encoding="utf-8"))
        if cleaned:
            result.append({"file": path.name, "text": cleaned})
    return result


def build_prompt(
    lesson: Path,
    duration_ms: int,
    parts: list[dict[str, Any]],
    references: list[dict[str, str]],
) -> str:
    boundaries = "\n".join(
        f"- {p['file']}: {p['start_ms']}ms to {p['end_ms']}ms" for p in parts
    ) or "- unavailable"
    reference = "\n\n".join(
        f"### {p['file']}\n{p['text']}" for p in references
    ) or "(No source transcript reference is available.)"
    return f"""Create a precise timing transcript for lesson \"{lesson.as_posix()}\".

Audio duration: {duration_ms} ms.

KNOWN ASSEMBLY BOUNDARIES
{boundaries}

SOURCE TRANSCRIPT REFERENCE
{reference}

Requirements:
1. Transcribe exactly what is audibly spoken. Preserve Arabic and English as spoken.
2. Do not translate, paraphrase, normalize, or invent speech.
3. Do not include silent SSML, IPA, YAML, performance tags, or source labels.
4. Return semantic segments with start_ms/end_ms relative to the final audio start.
5. Return best-effort word-level timing: one entry per spoken word with start_ms,
   end_ms, text, language, and its zero-based segment_index.
6. Keep timestamps monotonic and inside 0..{duration_ms}. Do not emit punctuation-only
   word entries; punctuation may stay attached to a neighboring spoken word.
7. Label mixed Arabic/English speech using short language codes such as \"ar\" and \"en\".
8. Assume one teacher unless the audio clearly contains multiple distinct speakers.
9. The source transcript is only a spelling/reference aid; the audio is authoritative.
10. Timing drives video synchronization. Return only the requested structured data.
"""


def normalize_payload(payload: dict[str, Any], duration_ms: int) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TranscriptionError("Model response is not an object")
    if not isinstance(payload.get("segments"), list) or not payload["segments"]:
        raise TranscriptionError("Model returned no transcript segments")
    if not isinstance(payload.get("words"), list) or not payload["words"]:
        raise TranscriptionError("Model returned no word timings")

    def item(raw: Any, word: bool) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise TranscriptionError("Timing entry is not an object")
        start, end = int(raw["start_ms"]), int(raw["end_ms"])
        if start < 0 or end < start or end > duration_ms + 3000:
            raise TranscriptionError(f"Invalid timing {start}..{end} for {duration_ms}ms")
        out = dict(raw)
        out.update(
            start_ms=min(start, duration_ms),
            end_ms=min(end, duration_ms),
            text=str(raw.get("text", "")).strip(),
            language=str(raw.get("language", "")).strip() or "und",
        )
        if not out["text"]:
            raise TranscriptionError("Empty transcript entry")
        if word:
            out["segment_index"] = int(raw["segment_index"])
        else:
            out["speaker"] = str(raw.get("speaker", "")).strip() or "Speaker 1"
        return out

    segments = sorted(
        (item(raw, False) for raw in payload["segments"]),
        key=lambda x: (x["start_ms"], x["end_ms"]),
    )
    words = sorted(
        (item(raw, True) for raw in payload["words"]),
        key=lambda x: (x["start_ms"], x["end_ms"]),
    )
    for index, word in enumerate(words):
        if not 0 <= word["segment_index"] < len(segments):
            raise TranscriptionError(f"Word {index} has invalid segment_index")
    return {"segments": segments, "words": words}


def transcribe_with_router(
    client: genai.Client,
    *,
    audio_path: Path,
    prompt: str,
    models: list[str],
    item_index: int,
    attempts_per_model: int,
    initial_delay: float,
    max_delay: float,
    duration_ms: int,
) -> tuple[str, dict[str, Any]]:
    uploaded = client.files.upload(
        file=str(audio_path),
        config={"mime_type": "audio/mpeg", "display_name": audio_path.name},
    )
    failures: list[str] = []
    try:
        for model in route_order(models, item_index):
            for attempt in range(1, attempts_per_model + 1):
                try:
                    response = client.interactions.create(
                        model=model,
                        input=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "audio",
                                "uri": uploaded.uri,
                                "mime_type": uploaded.mime_type or "audio/mpeg",
                            },
                        ],
                        response_format=TRANSCRIPT_SCHEMA,
                    )
                    raw = getattr(response, "output_text", None)
                    if not raw:
                        raise TranscriptionError(f"{model} returned no transcript")
                    return model, normalize_payload(json.loads(raw), duration_ms)
                except errors.APIError as exc:
                    status = getattr(exc, "code", None)
                    if status in {401, 403}:
                        raise
                    failures.append(f"{model} attempt {attempt}: API {status}: {exc}")
                    retryable = status == 429 or (
                        isinstance(status, int) and 500 <= status <= 599
                    )
                    if retryable and attempt < attempts_per_model:
                        delay = min(max_delay, initial_delay * 2 ** (attempt - 1))
                        delay += random.uniform(0, 1)
                        print(f"    {model}: retrying in {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    break
                except (
                    json.JSONDecodeError,
                    KeyError,
                    TypeError,
                    ValueError,
                    TranscriptionError,
                ) as exc:
                    failures.append(f"{model}: {type(exc).__name__}: {exc}")
                    break
        raise TranscriptionError("All router models failed: " + " | ".join(failures))
    finally:
        try:
            if getattr(uploaded, "name", None):
                client.files.delete(name=uploaded.name)
        except Exception as exc:
            print(f"Warning: could not delete uploaded Gemini file: {exc}", file=sys.stderr)


def existing_matches(path: Path, audio_hash: str, config_hash: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        data.get("audio_sha256") == audio_hash
        and data.get("transcription_config_sha256") == config_hash
        and bool(data.get("words"))
    )


def format_vtt_time(ms: int) -> str:
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def render_vtt(segments: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for index, segment in enumerate(segments, 1):
        lines += [
            str(index),
            f"{format_vtt_time(segment['start_ms'])} --> {format_vtt_time(segment['end_ms'])}",
            segment["text"],
            "",
        ]
    return "\n".join(lines)
