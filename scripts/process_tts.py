#!/usr/bin/env python3
"""Batch Gemini 3.1 Flash TTS processor.

Flow:
  transcripts/**/*.{txt,md} -> audio/**/*.wav + audio/**/*.json -> done/**/*.{txt,md}

A source transcript is archived only after a valid WAV and manifest are written.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import shutil
import sys
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from google import genai
from google.genai import errors

SUPPORTED_EXTENSIONS = {".txt", ".md"}
DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_CHANNELS = 1
DEFAULT_SAMPLE_WIDTH = 2


@dataclass(frozen=True)
class TranscriptJob:
    source_path: Path
    relative_path: Path
    transcript: str
    metadata: dict[str, Any]


class ConfigError(ValueError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Expected YAML mapping in {path}")
    return data


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Parse optional YAML front matter delimited by --- lines."""
    if not text.startswith("---\n"):
        return {}, text.strip()

    end = text.find("\n---\n", 4)
    if end == -1:
        raise ConfigError("Transcript starts with YAML front matter but has no closing --- line")

    raw_meta = text[4:end]
    body = text[end + 5 :].strip()
    metadata = yaml.safe_load(raw_meta) or {}
    if not isinstance(metadata, dict):
        raise ConfigError("Transcript front matter must be a YAML mapping")
    return metadata, body


def discover_jobs(inbox: Path) -> list[TranscriptJob]:
    jobs: list[TranscriptJob] = []
    if not inbox.exists():
        return jobs

    for path in sorted(p for p in inbox.rglob("*") if p.is_file()):
        if path.name.startswith(".") or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        metadata, transcript = parse_front_matter(raw)
        if not transcript.strip():
            raise ConfigError(f"Transcript is empty: {path}")
        jobs.append(
            TranscriptJob(
                source_path=path,
                relative_path=path.relative_to(inbox),
                transcript=transcript,
                metadata=metadata,
            )
        )
    return jobs


def merged_setting(global_config: dict[str, Any], metadata: dict[str, Any], key: str, default: Any = None) -> Any:
    value = metadata.get(key, global_config.get(key, default))
    return value


def normalize_speech_config(global_config: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, str]]:
    speakers = metadata.get("speakers")
    if speakers is not None:
        if not isinstance(speakers, list) or not (1 <= len(speakers) <= 2):
            raise ConfigError("'speakers' must be a list with one or two speaker mappings")
        normalized: list[dict[str, str]] = []
        for item in speakers:
            if not isinstance(item, dict) or not item.get("speaker") or not item.get("voice"):
                raise ConfigError("Each speaker requires both 'speaker' and 'voice'")
            normalized.append({"speaker": str(item["speaker"]), "voice": str(item["voice"])})
        return normalized

    voice = str(merged_setting(global_config, metadata, "voice", "Kore"))
    return [{"voice": voice}]


def build_prompt(global_config: dict[str, Any], metadata: dict[str, Any], transcript_chunk: str) -> str:
    audio_profile = str(merged_setting(global_config, metadata, "audio_profile", "Natural narrator"))
    scene = str(merged_setting(global_config, metadata, "scene", "Quiet recording studio"))
    director_notes = str(
        merged_setting(
            global_config,
            metadata,
            "director_notes",
            "Speak naturally and preserve the transcript exactly.",
        )
    )

    return (
        "Synthesize speech from the transcript below. Speak ONLY the text under TRANSCRIPT. "
        "Do not read any instructions, section labels, metadata, or commentary aloud.\n\n"
        f"# AUDIO PROFILE\n{audio_profile}\n\n"
        f"# SCENE\n{scene}\n\n"
        f"# DIRECTOR'S NOTES\n{director_notes}\n\n"
        f"# TRANSCRIPT\n{transcript_chunk.strip()}"
    )


def split_transcript(text: str, max_chars: int) -> list[str]:
    """Split near paragraph/sentence boundaries while preserving all text content."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
            current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        flush()
        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        sentence_parts: list[str] = []
        start = 0
        for idx, char in enumerate(paragraph):
            if char in ".!?" and idx + 1 < len(paragraph) and paragraph[idx + 1].isspace():
                sentence_parts.append(paragraph[start : idx + 1].strip())
                start = idx + 1
        tail = paragraph[start:].strip()
        if tail:
            sentence_parts.append(tail)

        for sentence in sentence_parts or [paragraph]:
            if len(sentence) > max_chars:
                flush()
                for pos in range(0, len(sentence), max_chars):
                    piece = sentence[pos : pos + max_chars].strip()
                    if piece:
                        chunks.append(piece)
                continue

            candidate = sentence if not current else f"{current} {sentence}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                flush()
                current = sentence

    flush()
    return chunks


def write_wav(path: Path, pcm: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with wave.open(str(temp_path), "wb") as wf:
        wf.setnchannels(DEFAULT_CHANNELS)
        wf.setsampwidth(DEFAULT_SAMPLE_WIDTH)
        wf.setframerate(DEFAULT_SAMPLE_RATE)
        wf.writeframes(pcm)
    temp_path.replace(path)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def manifest_matches(manifest_path: Path, source_hash: str, config_hash: str) -> bool:
    if not manifest_path.exists():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return data.get("source_sha256") == source_hash and data.get("effective_config_sha256") == config_hash


def retryable_status(exc: Exception) -> int | None:
    status = getattr(exc, "code", None)
    if isinstance(status, int):
        return status
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    return None


def synthesize_chunk(
    client: genai.Client,
    *,
    model: str,
    prompt: str,
    speech_config: list[dict[str, str]],
    max_attempts: int,
    initial_delay: float,
    max_delay: float,
) -> bytes:
    for attempt in range(1, max_attempts + 1):
        try:
            interaction = client.interactions.create(
                model=model,
                input=prompt,
                response_format={"type": "audio"},
                generation_config={"speech_config": speech_config},
            )
            output_audio = getattr(interaction, "output_audio", None)
            data = getattr(output_audio, "data", None) if output_audio is not None else None
            if not data:
                raise RuntimeError("Gemini returned no audio data")
            return base64.b64decode(data)
        except errors.APIError as exc:
            status = retryable_status(exc)
            should_retry = status == 429 or (status is not None and 500 <= status <= 599)
            if not should_retry or attempt >= max_attempts:
                raise
            delay = min(max_delay, initial_delay * (2 ** (attempt - 1))) + random.uniform(0, 1.0)
            print(f"    API error {status}; retrying attempt {attempt + 1}/{max_attempts} in {delay:.1f}s")
            time.sleep(delay)
        except RuntimeError:
            if attempt >= max_attempts:
                raise
            delay = min(max_delay, initial_delay * (2 ** (attempt - 1))) + random.uniform(0, 1.0)
            print(f"    No usable audio returned; retrying attempt {attempt + 1}/{max_attempts} in {delay:.1f}s")
            time.sleep(delay)

    raise RuntimeError("Unreachable retry state")


def archive_source(job: TranscriptJob, done_dir: Path) -> Path:
    destination = done_dir / job.relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = destination.with_name(f"{destination.stem}-{stamp}{destination.suffix}")
    shutil.move(str(job.source_path), str(destination))
    return destination


def process_job(
    client: genai.Client,
    job: TranscriptJob,
    global_config: dict[str, Any],
    audio_dir: Path,
    done_dir: Path,
) -> None:
    model = str(merged_setting(global_config, job.metadata, "model", "gemini-3.1-flash-tts-preview"))
    speech_config = normalize_speech_config(global_config, job.metadata)
    max_chars = int(merged_setting(global_config, job.metadata, "max_chars_per_request", 5000))
    request_delay = float(global_config.get("request_delay_seconds", 2))
    retry = global_config.get("retry", {}) or {}
    max_attempts = int(retry.get("max_attempts", 5))
    initial_delay = float(retry.get("initial_delay_seconds", 4))
    max_delay = float(retry.get("max_delay_seconds", 60))

    effective_config = {
        "model": model,
        "speech_config": speech_config,
        "audio_profile": merged_setting(global_config, job.metadata, "audio_profile"),
        "scene": merged_setting(global_config, job.metadata, "scene"),
        "director_notes": merged_setting(global_config, job.metadata, "director_notes"),
        "max_chars_per_request": max_chars,
    }
    source_hash = sha256_text(job.transcript)
    config_hash = sha256_text(json.dumps(effective_config, sort_keys=True, ensure_ascii=False))

    relative_no_suffix = job.relative_path.with_suffix("")
    wav_path = audio_dir / relative_no_suffix.with_suffix(".wav")
    manifest_path = audio_dir / relative_no_suffix.with_suffix(".json")

    if wav_path.exists() and manifest_matches(manifest_path, source_hash, config_hash):
        archived = archive_source(job, done_dir)
        print(f"  Reusing matching audio; archived transcript -> {archived}")
        return

    chunks = split_transcript(job.transcript, max_chars=max_chars)
    print(f"  Generating {len(chunks)} chunk(s) with {model} and {speech_config}")

    pcm_parts: list[bytes] = []
    for index, chunk in enumerate(chunks, start=1):
        print(f"    Chunk {index}/{len(chunks)} ({len(chunk)} chars)")
        prompt = build_prompt(global_config, job.metadata, chunk)
        pcm_parts.append(
            synthesize_chunk(
                client,
                model=model,
                prompt=prompt,
                speech_config=speech_config,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
            )
        )
        if index != len(chunks) and request_delay > 0:
            time.sleep(request_delay)

    silence = b"\x00\x00" * int(DEFAULT_SAMPLE_RATE * 0.20)
    joined_pcm = silence.join(pcm_parts)
    write_wav(wav_path, joined_pcm)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": str(job.relative_path),
        "source_sha256": source_hash,
        "effective_config_sha256": config_hash,
        "model": model,
        "speech_config": speech_config,
        "chunks": len(chunks),
        "sample_rate_hz": DEFAULT_SAMPLE_RATE,
        "channels": DEFAULT_CHANNELS,
        "sample_width_bytes": DEFAULT_SAMPLE_WIDTH,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    archived = archive_source(job, done_dir)
    print(f"  Wrote {wav_path} and archived transcript -> {archived}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Gemini TTS audio for transcript files")
    parser.add_argument("--config", type=Path, default=Path("tts_config.yaml"))
    parser.add_argument("--inbox", type=Path, default=Path("transcripts"))
    parser.add_argument("--audio", type=Path, default=Path("audio"))
    parser.add_argument("--done", type=Path, default=Path("done"))
    parser.add_argument("--dry-run", action="store_true", help="Validate and show jobs without calling Gemini")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml(args.config)
    jobs = discover_jobs(args.inbox)
    if not jobs:
        print("No transcript files found. Nothing to do.")
        return 0

    print(f"Found {len(jobs)} transcript(s).")
    if args.dry_run:
        for job in jobs:
            speech_config = normalize_speech_config(config, job.metadata)
            max_chars = int(merged_setting(config, job.metadata, "max_chars_per_request", 5000))
            print(f"- {job.relative_path}: {len(split_transcript(job.transcript, max_chars))} chunk(s), {speech_config}")
        return 0

    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: Set GEMINI_API_KEY (or GOOGLE_API_KEY) before running.", file=sys.stderr)
        return 2

    client = genai.Client()
    failures: list[tuple[Path, str]] = []

    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] {job.relative_path}")
        try:
            process_job(client, job, config, args.audio, args.done)
        except Exception as exc:
            failures.append((job.relative_path, f"{type(exc).__name__}: {exc}"))
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailed transcript(s):", file=sys.stderr)
        for path, reason in failures:
            print(f"- {path}: {reason}", file=sys.stderr)
        print("Successful transcripts were still generated/archived; failed files remain in transcripts/.", file=sys.stderr)
        return 1

    print("All transcripts processed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
