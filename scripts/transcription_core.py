"""Helpers for reliable per-part word alignment with Gemini audio understanding."""

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

SCHEMA_VERSION = 2
REFERENCE_EXTENSIONS = {".txt", ".md"}

PART_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "language": {"type": "string"},
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_ms": {"type": "integer", "minimum": 0},
                    "end_ms": {"type": "integer", "minimum": 0},
                    "text": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["start_ms", "end_ms", "text", "language"],
            },
        },
    },
    "required": ["text", "language", "words"],
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
        "alignment_mode": "per_part",
        "models": settings["models"],
        "attempts_per_model": settings["attempts_per_model"],
        "prompt_version": 2,
    }
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def route_order(models: list[str], item_index: int) -> list[str]:
    if not models:
        raise TranscriptionError("No transcription models configured")
    offset = item_index % len(models)
    return models[offset:] + models[:offset]


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as wf:
        return round(wf.getnframes() / wf.getframerate() * 1000)


def audio_duration_ms(final_wav: Path, manifest: Path) -> int:
    if final_wav.exists():
        return wav_duration_ms(final_wav)
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
        duration = wav_duration_ms(part)
        result.append(
            {
                "file": part.name,
                "start_ms": cursor,
                "end_ms": cursor + duration,
                "duration_ms": duration,
            }
        )
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
    text = re.sub(r"(?m)^Speaker\s+\d+\s*:\s*", "", text, flags=re.IGNORECASE)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()


def reference_parts(done_dir: Path, lesson: Path) -> dict[str, str]:
    lesson_dir = done_dir / lesson
    if not lesson_dir.exists():
        return {}
    result: dict[str, str] = {}
    for path in sorted(p for p in lesson_dir.iterdir() if p.is_file()):
        if path.suffix.lower() not in REFERENCE_EXTENSIONS:
            continue
        cleaned = clean_reference_text(path.read_text(encoding="utf-8"))
        if cleaned:
            result[path.stem] = cleaned
    return result


def build_part_prompt(part_name: str, duration_ms: int, reference: str) -> str:
    reference = reference or "(No source transcript reference is available.)"
    return f"""Align the spoken words in audio part "{part_name}" to timestamps.

Audio duration: {duration_ms} ms.

SOURCE TRANSCRIPT REFERENCE
{reference}

Requirements:
1. The audio is authoritative. Transcribe exactly what is audibly spoken.
2. Preserve Arabic and English exactly as spoken. Do not translate or paraphrase.
3. Use the source reference only for spelling and expected word order.
4. Return `text` containing the complete spoken part.
5. Return one `words` entry for EVERY spoken lexical word from beginning to end.
6. A words entry must contain exactly one lexical word/token, never a multi-word phrase.
   Contractions such as "I'm" count as one word. Punctuation may attach to a word.
7. Each word needs start_ms/end_ms relative to THIS AUDIO PART, not the whole lesson.
8. Keep timestamps monotonic and within 0..{duration_ms}.
9. Label each word with a short language code such as "ar" or "en".
10. Do not output silent SSML, IPA, YAML, performance tags, or speaker/source labels.
11. Return only the requested structured data.
"""


def reference_word_count(reference: str) -> int:
    return len(re.findall(r"\S+", reference.strip())) if reference else 0


def normalize_part_payload(
    payload: dict[str, Any], duration_ms: int, expected_words: int = 0
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TranscriptionError("Model response is not an object")
    text = str(payload.get("text", "")).strip()
    language = str(payload.get("language", "")).strip() or "und"
    words_raw = payload.get("words")
    if not text or not isinstance(words_raw, list) or not words_raw:
        raise TranscriptionError("Model returned incomplete part transcript")

    words: list[dict[str, Any]] = []
    for raw in words_raw:
        if not isinstance(raw, dict):
            raise TranscriptionError("Word timing entry is not an object")
        start, end = int(raw["start_ms"]), int(raw["end_ms"])
        if start < 0 or end < start or end > duration_ms + 1500:
            raise TranscriptionError(f"Invalid word timing {start}..{end} for {duration_ms}ms")
        token = str(raw.get("text", "")).strip()
        if not token:
            raise TranscriptionError("Empty timed word")
        if len(token.split()) > 1:
            raise TranscriptionError(f"Grouped multi-word timing entry: {token!r}")
        words.append(
            {
                "start_ms": min(start, duration_ms),
                "end_ms": min(end, duration_ms),
                "text": token,
                "language": str(raw.get("language", "")).strip() or "und",
            }
        )

    words.sort(key=lambda item: (item["start_ms"], item["end_ms"]))
    if expected_words and len(words) < max(1, round(expected_words * 0.7)):
        raise TranscriptionError(
            f"Only {len(words)} timed words for ~{expected_words} reference words"
        )
    return {"text": text, "language": language, "words": words}


def transcribe_part_with_router(
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
    expected_words: int,
) -> tuple[str, dict[str, Any]]:
    uploaded = client.files.upload(
        file=str(audio_path),
        config={"mime_type": "audio/wav", "display_name": audio_path.name},
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
                                "mime_type": uploaded.mime_type or "audio/wav",
                            },
                        ],
                        response_format=PART_SCHEMA,
                    )
                    raw = getattr(response, "output_text", None)
                    if not raw:
                        raise TranscriptionError(f"{model} returned no transcript")
                    payload = normalize_part_payload(
                        json.loads(raw), duration_ms, expected_words
                    )
                    return model, payload
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
                        print(f"      {model}: retrying in {delay:.1f}s")
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


def part_cache_path(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.stem}.timing.json")


def load_part_cache(
    path: Path, audio_hash: str, config_hash: str
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        data.get("schema_version") != SCHEMA_VERSION
        or data.get("audio_sha256") != audio_hash
        or data.get("transcription_config_sha256") != config_hash
        or not data.get("words")
    ):
        return None
    return data


def existing_matches(path: Path, audio_hash: str, config_hash: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        data.get("schema_version") == SCHEMA_VERSION
        and data.get("audio_sha256") == audio_hash
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
