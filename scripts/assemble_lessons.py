#!/usr/bin/env python3
"""Assemble per-lesson TTS clips into final WAV and MP3 files.

Convention:
  audio/<lesson-name>/01-*.wav
  audio/<lesson-name>/02-*.wav
  ...
becomes:
  final/<lesson-name>.wav
  final/<lesson-name>.mp3
  final/<lesson-name>.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class WavFormat:
    channels: int
    sample_width: int
    frame_rate: int
    compression_type: str


class AssemblyError(RuntimeError):
    pass


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise AssemblyError(f"Expected YAML mapping in {path}")
    return data


def discover_lessons(audio_dir: Path) -> dict[Path, list[Path]]:
    lessons: dict[Path, list[Path]] = {}
    if not audio_dir.exists():
        return lessons

    for wav_path in sorted(audio_dir.rglob("*.wav")):
        if not wav_path.is_file():
            continue
        lesson = wav_path.parent.relative_to(audio_dir)
        if lesson == Path("."):
            print(f"Skipping root-level WAV (put lesson clips in a subfolder): {wav_path}")
            continue
        lessons.setdefault(lesson, []).append(wav_path)
    return lessons


def wav_format(path: Path) -> WavFormat:
    with wave.open(str(path), "rb") as wf:
        return WavFormat(
            channels=wf.getnchannels(),
            sample_width=wf.getsampwidth(),
            frame_rate=wf.getframerate(),
            compression_type=wf.getcomptype(),
        )


def assembly_fingerprint(parts: list[Path], gap_ms: int, mp3_bitrate: str) -> str:
    digest = hashlib.sha256()
    digest.update(f"gap_ms={gap_ms}\nmp3_bitrate={mp3_bitrate}\n".encode())
    for part in parts:
        digest.update(part.name.encode("utf-8"))
        digest.update(b"\0")
        with part.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def manifest_matches(path: Path, fingerprint: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("assembly_sha256") == fingerprint


def assemble_wav(parts: list[Path], output_path: Path, gap_ms: int) -> tuple[WavFormat, int]:
    if not parts:
        raise AssemblyError("Cannot assemble an empty lesson")

    expected = wav_format(parts[0])
    if expected.compression_type != "NONE":
        raise AssemblyError(f"Only uncompressed PCM WAV is supported: {parts[0]}")

    gap_frames = round(expected.frame_rate * (gap_ms / 1000))
    gap_bytes = b"\x00" * gap_frames * expected.channels * expected.sample_width
    total_frames = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    with wave.open(str(temp_path), "wb") as out:
        out.setnchannels(expected.channels)
        out.setsampwidth(expected.sample_width)
        out.setframerate(expected.frame_rate)

        for index, part in enumerate(parts):
            current = wav_format(part)
            if current != expected:
                raise AssemblyError(
                    f"WAV format mismatch in lesson: {part} is {current}, expected {expected}"
                )
            with wave.open(str(part), "rb") as src:
                frames = src.readframes(src.getnframes())
                total_frames += src.getnframes()
                out.writeframes(frames)

            if index != len(parts) - 1 and gap_frames:
                out.writeframes(gap_bytes)
                total_frames += gap_frames

    temp_path.replace(output_path)
    return expected, total_frames


def encode_mp3(wav_path: Path, mp3_path: Path, bitrate: str) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AssemblyError(
            "ffmpeg is required for MP3 output. Install ffmpeg or run in GitHub Actions."
        )

    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = mp3_path.with_name(mp3_path.name + ".tmp.mp3")
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-map_metadata",
        "-1",
        str(temp_path),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        temp_path.unlink(missing_ok=True)
        raise AssemblyError(f"ffmpeg failed for {wav_path}") from exc
    temp_path.replace(mp3_path)


def process_lesson(
    lesson: Path,
    parts: list[Path],
    final_dir: Path,
    gap_ms: int,
    mp3_bitrate: str,
) -> bool:
    output_base = final_dir / lesson
    wav_path = output_base.with_suffix(".wav")
    mp3_path = output_base.with_suffix(".mp3")
    manifest_path = output_base.with_suffix(".json")

    fingerprint = assembly_fingerprint(parts, gap_ms, mp3_bitrate)
    if wav_path.exists() and mp3_path.exists() and manifest_matches(manifest_path, fingerprint):
        print(f"- {lesson}: unchanged; reusing existing final files")
        return False

    audio_format, total_frames = assemble_wav(parts, wav_path, gap_ms)
    encode_mp3(wav_path, mp3_path, mp3_bitrate)

    duration_seconds = total_frames / audio_format.frame_rate
    manifest = {
        "lesson": lesson.as_posix(),
        "assembly_sha256": fingerprint,
        "parts": [part.name for part in parts],
        "part_count": len(parts),
        "gap_ms": gap_ms,
        "duration_seconds": round(duration_seconds, 3),
        "wav": {
            "sample_rate_hz": audio_format.frame_rate,
            "channels": audio_format.channels,
            "sample_width_bytes": audio_format.sample_width,
        },
        "mp3_bitrate": mp3_bitrate,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"- {lesson}: {len(parts)} clips -> {wav_path} + {mp3_path} "
        f"({duration_seconds:.1f}s)"
    )
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble lesson clip folders into final WAV and MP3 files"
    )
    parser.add_argument("--config", type=Path, default=Path("tts_config.yaml"))
    parser.add_argument("--audio", type=Path, default=Path("audio"))
    parser.add_argument("--final", type=Path, default=Path("final"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    assembly = config.get("assembly", {}) or {}
    gap_ms = int(assembly.get("gap_ms", 300))
    mp3_bitrate = str(assembly.get("mp3_bitrate", "192k"))

    lessons = discover_lessons(args.audio)
    if not lessons:
        print("No lesson clip folders found. Nothing to assemble.")
        return 0

    print(f"Found {len(lessons)} lesson(s) to assemble.")
    failures: list[tuple[Path, str]] = []
    for lesson, parts in lessons.items():
        try:
            process_lesson(lesson, parts, args.final, gap_ms, mp3_bitrate)
        except Exception as exc:
            failures.append((lesson, f"{type(exc).__name__}: {exc}"))
            print(f"- {lesson}: FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailed lesson assembly:", file=sys.stderr)
        for lesson, reason in failures:
            print(f"- {lesson}: {reason}", file=sys.stderr)
        return 1

    print("All lessons assembled successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
