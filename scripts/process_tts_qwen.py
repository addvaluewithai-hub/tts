#!/usr/bin/env python3
"""Generate TTS audio through the private Qwen3-TTS 0.6B Modal service.

Flow:
  transcripts/**/*.{txt,md} -> audio/**/*.wav + audio/**/*.json -> done/**/*.{txt,md}

This is the production speech-synthesis provider for Video Factory. It deliberately
keeps Modal/GPU/model hosting out of GitHub Actions: the runner only calls the
private HTTP API deployed from addvaluewithai-hub/free-image-editing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import re
import sys
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

SUPPORTED_EXTENSIONS = {".txt", ".md"}
QWEN_MAX_TEXT_CHARS = 2400
CONTROL_CUE_RE = re.compile(r"(?m)^\s*\[[A-Z][A-Z0-9 ,.'’/&+\-]*\]\s*")
TAG_RE = re.compile(r"</?[^>]+>")
SANITIZER_VERSION = 1


@dataclass(frozen=True)
class TranscriptJob:
    source_path: Path
    relative_path: Path
    transcript: str
    metadata: dict[str, Any]


class ConfigError(ValueError):
    pass


class QwenAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Expected YAML mapping in {path}")
    return data


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
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


def merged_setting(
    global_config: dict[str, Any], metadata: dict[str, Any], key: str, default: Any = None
) -> Any:
    return metadata.get(key, global_config.get(key, default))


def sanitize_transcript(text: str) -> str:
    """Remove renderer control markup that Qwen 0.6B would otherwise speak aloud."""
    cleaned = CONTROL_CUE_RE.sub("", text)
    cleaned = TAG_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_transcript(text: str, max_chars: int) -> list[str]:
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

        sentence_parts = re.split(r"(?<=[.!?])\s+", paragraph)
        for sentence in sentence_parts:
            sentence = sentence.strip()
            if not sentence:
                continue
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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def manifest_matches(manifest_path: Path, source_hash: str, config_hash: str) -> bool:
    if not manifest_path.exists():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (
        data.get("source_sha256") == source_hash
        and data.get("effective_config_sha256") == config_hash
    )


def qwen_headers() -> dict[str, str]:
    token_id = os.environ.get("MODAL_PROXY_TOKEN_ID")
    token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET")
    if not token_id or not token_secret:
        raise ConfigError(
            "Qwen Modal proxy credentials are missing. Set MODAL_PROXY_TOKEN_ID and "
            "MODAL_PROXY_TOKEN_SECRET."
        )
    return {
        "Authorization": f"Bearer {token_id}.{token_secret}",
        "Content-Type": "application/json",
    }


def qwen_base_url(config: dict[str, Any]) -> str:
    value = os.environ.get("QWEN_TTS_API_URL") or str(config.get("api_url", "")).strip()
    if not value:
        raise ConfigError("Set QWEN_TTS_API_URL to the deployed Modal API URL")
    return value.rstrip("/")


def validate_wav(data: bytes) -> dict[str, int]:
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            meta = {
                "sample_rate_hz": int(wf.getframerate()),
                "channels": int(wf.getnchannels()),
                "sample_width_bytes": int(wf.getsampwidth()),
                "frames": int(wf.getnframes()),
            }
    except (wave.Error, EOFError) as exc:
        raise QwenAPIError("Qwen returned invalid WAV audio") from exc
    if meta["frames"] <= 0:
        raise QwenAPIError("Qwen returned an empty WAV")
    return meta


def call_qwen_preset(
    *,
    base_url: str,
    text: str,
    speaker: str,
    language: str,
    timeout_seconds: float,
) -> bytes:
    response = requests.post(
        f"{base_url}/tts",
        headers=qwen_headers(),
        json={"text": text, "speaker": speaker, "language": language},
        timeout=timeout_seconds,
    )
    if not response.ok:
        detail = response.text[:1000]
        raise QwenAPIError(
            f"Qwen Modal HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
        )
    validate_wav(response.content)
    return response.content


def synthesize_with_retry(
    *,
    base_url: str,
    text: str,
    speaker: str,
    language: str,
    timeout_seconds: float,
    max_attempts: int,
    initial_delay: float,
    max_delay: float,
) -> bytes:
    for attempt in range(1, max_attempts + 1):
        try:
            return call_qwen_preset(
                base_url=base_url,
                text=text,
                speaker=speaker,
                language=language,
                timeout_seconds=timeout_seconds,
            )
        except (requests.RequestException, QwenAPIError) as exc:
            status = getattr(exc, "status_code", None)
            retryable = status in {408, 409, 425, 429} or (
                isinstance(status, int) and 500 <= status <= 599
            ) or isinstance(exc, requests.RequestException)
            if not retryable or attempt >= max_attempts:
                raise
            delay = min(max_delay, initial_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, 0.75)
            print(
                f"    Qwen request failed ({status or type(exc).__name__}); retrying "
                f"attempt {attempt + 1}/{max_attempts} in {delay:.1f}s"
            )
            time.sleep(delay)
    raise RuntimeError("Unreachable retry state")


def concat_wavs(parts: list[bytes], gap_ms: int = 200) -> bytes:
    if not parts:
        raise QwenAPIError("No WAV parts to concatenate")

    decoded: list[tuple[dict[str, int], bytes]] = []
    for data in parts:
        with wave.open(io.BytesIO(data), "rb") as wf:
            meta = {
                "sample_rate_hz": int(wf.getframerate()),
                "channels": int(wf.getnchannels()),
                "sample_width_bytes": int(wf.getsampwidth()),
            }
            pcm = wf.readframes(wf.getnframes())
            decoded.append((meta, pcm))

    first = decoded[0][0]
    for meta, _ in decoded[1:]:
        if meta != first:
            raise QwenAPIError("Qwen chunks returned incompatible WAV formats")

    bytes_per_frame = first["channels"] * first["sample_width_bytes"]
    gap_frames = int(first["sample_rate_hz"] * max(0, gap_ms) / 1000)
    silence = b"\x00" * gap_frames * bytes_per_frame
    pcm = silence.join(item[1] for item in decoded)

    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(first["channels"])
        wf.setsampwidth(first["sample_width_bytes"])
        wf.setframerate(first["sample_rate_hz"])
        wf.writeframes(pcm)
    return out.getvalue()


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def archive_source(job: TranscriptJob, done_dir: Path) -> Path:
    destination = done_dir / job.relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    job.source_path.replace(destination)
    return destination


def process_job(
    job: TranscriptJob,
    global_config: dict[str, Any],
    audio_dir: Path,
    done_dir: Path,
) -> None:
    qwen_cfg = global_config.get("qwen", {}) or {}
    if not isinstance(qwen_cfg, dict):
        raise ConfigError("tts_config.yaml 'qwen' must be a mapping")

    provider = str(global_config.get("provider", "qwen_modal"))
    if provider != "qwen_modal":
        raise ConfigError(f"process_tts_qwen.py requires provider=qwen_modal, got {provider!r}")

    model = str(qwen_cfg.get("model", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"))
    speaker = str(merged_setting(qwen_cfg, job.metadata, "speaker", "Aiden"))
    language = str(merged_setting(qwen_cfg, job.metadata, "language", "English"))
    max_chars = int(qwen_cfg.get("max_chars_per_request", 2200))
    if max_chars <= 0 or max_chars > QWEN_MAX_TEXT_CHARS:
        raise ConfigError(f"qwen.max_chars_per_request must be 1..{QWEN_MAX_TEXT_CHARS}")

    timeout_seconds = float(qwen_cfg.get("timeout_seconds", 900))
    chunk_gap_ms = int(qwen_cfg.get("chunk_gap_ms", 180))
    request_delay = float(qwen_cfg.get("request_delay_seconds", 0.25))
    retry = qwen_cfg.get("retry", {}) or {}
    max_attempts = int(retry.get("max_attempts", 4))
    initial_delay = float(retry.get("initial_delay_seconds", 3))
    max_delay = float(retry.get("max_delay_seconds", 30))

    speakable = sanitize_transcript(job.transcript)
    if not speakable:
        raise ConfigError(f"Transcript contains no speakable text after sanitization: {job.source_path}")

    effective_config = {
        "provider": provider,
        "model": model,
        "speaker": speaker,
        "language": language,
        "max_chars_per_request": max_chars,
        "chunk_gap_ms": chunk_gap_ms,
        "sanitizer_version": SANITIZER_VERSION,
    }
    source_hash = sha256_text(job.transcript)
    config_hash = sha256_text(json.dumps(effective_config, sort_keys=True, ensure_ascii=False))

    relative_no_suffix = job.relative_path.with_suffix("")
    wav_path = audio_dir / relative_no_suffix.with_suffix(".wav")
    manifest_path = audio_dir / relative_no_suffix.with_suffix(".json")

    if wav_path.exists() and manifest_matches(manifest_path, source_hash, config_hash):
        archived = archive_source(job, done_dir)
        print(f"  Reusing matching Qwen audio; archived transcript -> {archived}")
        return

    chunks = split_transcript(speakable, max_chars=max_chars)
    base_url = qwen_base_url(qwen_cfg)
    print(f"  Generating {len(chunks)} chunk(s) with Qwen 0.6B speaker={speaker} language={language}")

    wav_parts: list[bytes] = []
    for index, chunk in enumerate(chunks, start=1):
        print(f"    Chunk {index}/{len(chunks)} ({len(chunk)} chars)")
        wav_parts.append(
            synthesize_with_retry(
                base_url=base_url,
                text=chunk,
                speaker=speaker,
                language=language,
                timeout_seconds=timeout_seconds,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
            )
        )
        if index != len(chunks) and request_delay > 0:
            time.sleep(request_delay)

    joined = concat_wavs(wav_parts, gap_ms=chunk_gap_ms)
    audio_meta = validate_wav(joined)
    write_bytes_atomic(wav_path, joined)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": str(job.relative_path),
        "source_sha256": source_hash,
        "effective_config_sha256": config_hash,
        "provider": provider,
        "model": model,
        "speaker": speaker,
        "language": language,
        "chunks": len(chunks),
        **audio_meta,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    archived = archive_source(job, done_dir)
    print(f"  Wrote {wav_path} with Qwen and archived transcript -> {archived}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Qwen3-TTS audio for transcript files")
    parser.add_argument("--config", type=Path, default=Path("tts_config.yaml"))
    parser.add_argument("--inbox", type=Path, default=Path("transcripts"))
    parser.add_argument("--audio", type=Path, default=Path("audio"))
    parser.add_argument("--done", type=Path, default=Path("done"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_yaml(args.config)
        jobs = discover_jobs(args.inbox)
        if not jobs:
            print("No transcript files found. Nothing to do.")
            return 0

        print(f"Found {len(jobs)} transcript(s) for Qwen TTS.")
        if args.dry_run:
            qwen_cfg = config.get("qwen", {}) or {}
            for job in jobs:
                text = sanitize_transcript(job.transcript)
                speaker = merged_setting(qwen_cfg, job.metadata, "speaker", "Aiden")
                language = merged_setting(qwen_cfg, job.metadata, "language", "English")
                print(f"  {job.relative_path}: {len(text)} speakable chars, {speaker=}, {language=}")
            return 0

        # Validate credentials/url once before mutating queue state.
        qwen_base_url(config.get("qwen", {}) or {})
        qwen_headers()
        for job in jobs:
            print(f"Processing {job.relative_path}")
            process_job(job, config, args.audio, args.done)
        return 0
    except (ConfigError, QwenAPIError, requests.RequestException) as exc:
        print(f"QWEN TTS ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
