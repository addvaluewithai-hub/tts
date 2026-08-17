#!/usr/bin/env python3
"""Generate optional background music and mix licensed SFX with the dry voice master.

Dry narration remains authoritative for alignment:
  final/<job>.wav
  final/<job>.transcript.json

Optional program-audio outputs:
  final/<job>.music.mp3
  final/<job>.music.json
  final/<job>.mix.wav
  final/<job>.mix.mp3
  final/<job>.soundtrack.json

Configuration is read from input/<job>/job.yaml under `soundtrack`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml

try:
    from google import genai
except ImportError:  # pragma: no cover - surfaced clearly at runtime
    genai = None


class SoundtrackError(RuntimeError):
    pass


def read_active(path: Path) -> str | None:
    if not path.exists():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return line
    return None


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SoundtrackError(f"Missing YAML file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SoundtrackError(f"Expected YAML mapping in {path}")
    return data


def load_json_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SoundtrackError(f"Missing JSON file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SoundtrackError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SoundtrackError(f"Expected JSON mapping in {path}")
    return data


def stable_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_token(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    return "".join(ch for ch in text if unicodedata.category(ch)[0] not in {"P", "S"}).strip()


def anchor_tokens(text: str) -> list[str]:
    return [tok for tok in (normalize_token(x) for x in str(text).split()) if tok]


def resolve_anchor_ms(
    transcript: dict[str, Any],
    anchor_text: str,
    occurrence: int = 1,
) -> int:
    if occurrence < 1:
        raise SoundtrackError("SFX occurrence must be >= 1")
    target = anchor_tokens(anchor_text)
    if not target:
        raise SoundtrackError("SFX anchor_text must contain at least one searchable token")

    words = transcript.get("words") or []
    searchable: list[tuple[str, int]] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        token = normalize_token(word.get("text", ""))
        if token:
            searchable.append((token, int(word.get("start_ms", 0))))

    matches: list[int] = []
    width = len(target)
    for i in range(0, len(searchable) - width + 1):
        if [token for token, _ in searchable[i : i + width]] == target:
            matches.append(searchable[i][1])

    if len(matches) < occurrence:
        raise SoundtrackError(
            f"SFX anchor {anchor_text!r} occurrence {occurrence} not found "
            f"(found {len(matches)})"
        )
    return matches[occurrence - 1]


def resolve_event_ms(event: dict[str, Any], transcript: dict[str, Any]) -> int:
    offset_ms = int(event.get("offset_ms", 0))

    if "at_ms" in event:
        base = int(event["at_ms"])
    elif "at_seconds" in event:
        base = round(float(event["at_seconds"]) * 1000)
    elif "anchor_text" in event:
        base = resolve_anchor_ms(
            transcript,
            str(event["anchor_text"]),
            int(event.get("occurrence", 1)),
        )
    elif "part" in event:
        parts = transcript.get("parts") or []
        part_value = event["part"]
        if isinstance(part_value, int):
            index = part_value - 1
            if index < 0 or index >= len(parts):
                raise SoundtrackError(f"SFX part index out of range: {part_value}")
            base = int(parts[index]["start_ms"])
        else:
            wanted = str(part_value)
            match = next((p for p in parts if str(p.get("file")) == wanted), None)
            if not match:
                raise SoundtrackError(f"SFX part file not found in transcript: {wanted}")
            base = int(match["start_ms"])
    else:
        raise SoundtrackError(
            "Each SFX event needs one timing source: at_ms, at_seconds, anchor_text, or part"
        )

    return max(0, base + offset_ms)


def ensure_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SoundtrackError("ffmpeg is required for soundtrack mixing")
    return ffmpeg


def music_prompt(config: dict[str, Any]) -> str:
    prompt = str(config.get("prompt", "")).strip()
    if not prompt:
        raise SoundtrackError("soundtrack.music.prompt is required for Lyria")
    if bool(config.get("instrumental", True)):
        prompt += (
            "\nInstrumental only. No vocals, no singing, no spoken words, "
            "no voice samples. Keep the arrangement subtle enough to sit under narration."
        )
    return prompt


def generate_lyria_music(
    config: dict[str, Any],
    output_path: Path,
    metadata_path: Path,
) -> dict[str, Any]:
    if genai is None:
        raise SoundtrackError("google-genai is not installed")
    if not os.getenv("GEMINI_API_KEY"):
        raise SoundtrackError("GEMINI_API_KEY is required for Lyria generation")

    model = str(config.get("model", "lyria-3-clip-preview")).strip()
    if model not in {"lyria-3-clip-preview", "lyria-3-pro-preview"}:
        raise SoundtrackError(f"Unsupported Lyria model: {model}")

    prompt = music_prompt(config)
    request = {"provider": "lyria", "model": model, "prompt": prompt}
    request_sha = stable_json_hash(request)

    if output_path.exists() and metadata_path.exists():
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if existing.get("request_sha256") == request_sha:
            print(f"- Reusing cached Lyria music: {output_path}")
            return existing

    print(f"- Generating background music with {model}")
    client = genai.Client()
    interaction = client.interactions.create(model=model, input=prompt)
    generated_audio = interaction.output_audio
    if not generated_audio or not getattr(generated_audio, "data", None):
        raise SoundtrackError("Lyria response contained no audio")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(generated_audio.data))

    metadata = {
        "provider": "lyria",
        "model": model,
        "request_sha256": request_sha,
        "audio_sha256": file_sha256(output_path),
        "instrumental": bool(config.get("instrumental", True)),
        "synthid_expected": True,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return metadata


def resolve_music_asset(
    job_dir: Path,
    final_dir: Path,
    job_id: str,
    config: dict[str, Any],
) -> tuple[Path | None, dict[str, Any] | None]:
    if not bool(config.get("enabled", False)):
        return None, None

    source = str(config.get("source", "lyria")).strip().lower()
    if source == "lyria":
        output_path = final_dir / f"{job_id}.music.mp3"
        metadata_path = final_dir / f"{job_id}.music.json"
        metadata = generate_lyria_music(config, output_path, metadata_path)
        return output_path, metadata

    if source == "file":
        raw_file = str(config.get("file", "")).strip()
        if not raw_file:
            raise SoundtrackError("soundtrack.music.file is required when source=file")
        relative = Path(raw_file)
        if relative.is_absolute() or ".." in relative.parts:
            raise SoundtrackError("soundtrack.music.file must stay inside the job folder")
        path = job_dir / relative
        if not path.is_file():
            raise SoundtrackError(f"Music file not found: {path}")
        return path, {
            "provider": "file",
            "file": relative.as_posix(),
            "audio_sha256": file_sha256(path),
        }

    raise SoundtrackError(f"Unsupported soundtrack.music.source: {source}")


def load_sfx_manifest(job_dir: Path) -> dict[str, Any]:
    path = job_dir / "sfx" / "manifest.yaml"
    if not path.exists():
        raise SoundtrackError(
            "SFX are enabled but input/<job>/sfx/manifest.yaml is missing. "
            "Track source URL and license for every production SFX file."
        )
    data = load_yaml_mapping(path)
    files = data.get("files") or {}
    if not isinstance(files, dict):
        raise SoundtrackError("sfx/manifest.yaml 'files' must be a mapping")
    return files


def resolve_sfx_events(
    job_dir: Path,
    config: dict[str, Any],
    transcript: dict[str, Any],
    duration_ms: int,
) -> list[dict[str, Any]]:
    if not bool(config.get("enabled", False)):
        return []

    raw_events = config.get("events") or []
    if not isinstance(raw_events, list):
        raise SoundtrackError("soundtrack.sfx.events must be a list")

    manifest_files = load_sfx_manifest(job_dir)
    default_gain_db = float(config.get("gain_db", -8.0))
    resolved: list[dict[str, Any]] = []

    for index, event in enumerate(raw_events, start=1):
        if not isinstance(event, dict):
            raise SoundtrackError(f"SFX event #{index} must be a mapping")
        filename = str(event.get("file", "")).strip()
        if not filename:
            raise SoundtrackError(f"SFX event #{index} is missing file")
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise SoundtrackError(f"Unsafe SFX file path: {filename}")
        path = job_dir / "sfx" / relative
        if not path.is_file():
            raise SoundtrackError(f"SFX file not found: {path}")

        license_meta = manifest_files.get(filename)
        if not isinstance(license_meta, dict):
            raise SoundtrackError(
                f"SFX file {filename!r} is missing from sfx/manifest.yaml"
            )
        source_url = str(license_meta.get("source_url", "")).strip()
        license_name = str(license_meta.get("license", "")).strip()
        if not source_url or not license_name:
            raise SoundtrackError(
                f"SFX manifest entry {filename!r} requires source_url and license"
            )

        at_ms = resolve_event_ms(event, transcript)
        if at_ms >= duration_ms:
            raise SoundtrackError(
                f"SFX event {filename!r} starts at {at_ms}ms, beyond audio duration {duration_ms}ms"
            )
        resolved.append(
            {
                "file": filename,
                "path": path,
                "at_ms": at_ms,
                "gain_db": float(event.get("gain_db", default_gain_db)),
                "audio_sha256": file_sha256(path),
                "source_url": source_url,
                "license": license_name,
                "attribution": str(license_meta.get("attribution", "")).strip() or None,
            }
        )
    return resolved


def mix_audio(
    voice_path: Path,
    music_path: Path | None,
    music_config: dict[str, Any],
    sfx_events: list[dict[str, Any]],
    output_wav: Path,
    output_mp3: Path,
    duration_ms: int,
) -> None:
    ffmpeg = ensure_ffmpeg()
    duration = duration_ms / 1000.0
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(voice_path)]

    music_index: int | None = None
    next_input = 1
    if music_path is not None:
        music_index = next_input
        next_input += 1
        command += ["-stream_loop", "-1", "-i", str(music_path)]

    sfx_indexes: list[int] = []
    for event in sfx_events:
        sfx_indexes.append(next_input)
        next_input += 1
        command += ["-i", str(event["path"])]

    filters: list[str] = []
    mix_inputs: list[str] = []

    if music_index is not None:
        filters.append(
            "[0:a]aresample=48000,aformat=channel_layouts=stereo,"
            "asplit=2[voice_mix][voice_key]"
        )
        gain_db = float(music_config.get("gain_db", -28.0))
        fade_in = max(0.0, float(music_config.get("fade_in_seconds", 0.6)))
        fade_out = max(0.0, float(music_config.get("fade_out_seconds", 1.2)))
        fade_out = min(fade_out, duration)
        fade_out_start = max(0.0, duration - fade_out)

        music_filter = (
            f"[{music_index}:a]aresample=48000,aformat=channel_layouts=stereo,"
            f"volume={gain_db}dB,atrim=0:{duration:.3f},asetpts=PTS-STARTPTS"
        )
        if fade_in > 0:
            music_filter += f",afade=t=in:st=0:d={fade_in:.3f}"
        if fade_out > 0:
            music_filter += f",afade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f}"
        music_filter += "[music_raw]"
        filters.append(music_filter)

        threshold = float(music_config.get("duck_threshold", 0.025))
        ratio = float(music_config.get("duck_ratio", 8.0))
        attack = float(music_config.get("duck_attack_ms", 20.0))
        release = float(music_config.get("duck_release_ms", 300.0))
        filters.append(
            f"[music_raw][voice_key]sidechaincompress="
            f"threshold={threshold}:ratio={ratio}:attack={attack}:release={release}"
            "[music_ducked]"
        )
        mix_inputs.extend(["[voice_mix]", "[music_ducked]"])
    else:
        filters.append("[0:a]aresample=48000,aformat=channel_layouts=stereo[voice_mix]")
        mix_inputs.append("[voice_mix]")

    for idx, (input_index, event) in enumerate(zip(sfx_indexes, sfx_events), start=1):
        delay = int(event["at_ms"])
        gain_db = float(event["gain_db"])
        label = f"sfx{idx}"
        filters.append(
            f"[{input_index}:a]aresample=48000,aformat=channel_layouts=stereo,"
            f"volume={gain_db}dB,adelay={delay}|{delay}[{label}]"
        )
        mix_inputs.append(f"[{label}]")

    filters.append(
        "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.95[out]"
    )

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    temp_wav = output_wav.with_name(output_wav.name + ".tmp.wav")
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[out]",
        "-t",
        f"{duration:.3f}",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(temp_wav),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        temp_wav.unlink(missing_ok=True)
        raise SoundtrackError("ffmpeg soundtrack mix failed") from exc
    temp_wav.replace(output_wav)

    temp_mp3 = output_mp3.with_name(output_mp3.name + ".tmp.mp3")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(output_wav),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-map_metadata",
                "-1",
                str(temp_mp3),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        temp_mp3.unlink(missing_ok=True)
        raise SoundtrackError("ffmpeg soundtrack MP3 encode failed") from exc
    temp_mp3.replace(output_mp3)


def soundtrack_fingerprint(
    voice_path: Path,
    transcript_path: Path,
    soundtrack_config: dict[str, Any],
    music_meta: dict[str, Any] | None,
    sfx_events: list[dict[str, Any]],
) -> str:
    payload = {
        "voice_sha256": file_sha256(voice_path),
        "transcript_sha256": file_sha256(transcript_path),
        "config": soundtrack_config,
        "music": music_meta,
        "sfx": [
            {
                k: v
                for k, v in event.items()
                if k not in {"path"}
            }
            for event in sfx_events
        ],
    }
    return stable_json_hash(payload)


def existing_mix_matches(path: Path, fingerprint: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return data.get("soundtrack_sha256") == fingerprint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare optional music + SFX program audio")
    parser.add_argument("--input-root", type=Path, default=Path("input"))
    parser.add_argument("--final-root", type=Path, default=Path("final"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        active = read_active(args.input_root / "ACTIVE")
        if not active:
            print("No active input job. Soundtrack stage has nothing to do.")
            return 0

        job_dir = args.input_root / active
        job = load_yaml_mapping(job_dir / "job.yaml")
        soundtrack = job.get("soundtrack") or {}
        if not isinstance(soundtrack, dict):
            raise SoundtrackError("job.yaml 'soundtrack' must be a mapping")
        if not bool(soundtrack.get("enabled", False)):
            print(f"Active job {active}: soundtrack.enabled=false; keeping dry voice master.")
            return 0

        voice_path = args.final_root / f"{active}.wav"
        transcript_path = args.final_root / f"{active}.transcript.json"
        if not voice_path.is_file() or not transcript_path.is_file():
            raise SoundtrackError(
                f"Soundtrack stage requires {voice_path} and {transcript_path}"
            )
        transcript = load_json_mapping(transcript_path)
        duration_ms = int(transcript.get("duration_ms", 0))
        if duration_ms <= 0:
            raise SoundtrackError("Transcript duration_ms must be > 0")

        music_config = soundtrack.get("music") or {}
        sfx_config = soundtrack.get("sfx") or {}
        if not isinstance(music_config, dict) or not isinstance(sfx_config, dict):
            raise SoundtrackError("soundtrack.music and soundtrack.sfx must be mappings")

        music_path, music_meta = resolve_music_asset(
            job_dir, args.final_root, active, music_config
        )
        sfx_events = resolve_sfx_events(job_dir, sfx_config, transcript, duration_ms)

        if music_path is None and not sfx_events:
            print(f"Active job {active}: soundtrack enabled but no music/SFX are enabled.")
            return 0

        output_wav = args.final_root / f"{active}.mix.wav"
        output_mp3 = args.final_root / f"{active}.mix.mp3"
        manifest_path = args.final_root / f"{active}.soundtrack.json"
        fingerprint = soundtrack_fingerprint(
            voice_path, transcript_path, soundtrack, music_meta, sfx_events
        )
        if (
            output_wav.exists()
            and output_mp3.exists()
            and existing_mix_matches(manifest_path, fingerprint)
        ):
            print(f"- {active}: soundtrack unchanged; reusing existing mix")
            return 0

        mix_audio(
            voice_path,
            music_path,
            music_config,
            sfx_events,
            output_wav,
            output_mp3,
            duration_ms,
        )

        manifest = {
            "schema_version": 1,
            "job": active,
            "soundtrack_sha256": fingerprint,
            "duration_ms": duration_ms,
            "dry_voice": {
                "file": voice_path.as_posix(),
                "sha256": file_sha256(voice_path),
            },
            "music": music_meta,
            "sfx": [
                {k: v for k, v in event.items() if k != "path"}
                for event in sfx_events
            ],
            "mix": {
                "wav": output_wav.as_posix(),
                "wav_sha256": file_sha256(output_wav),
                "mp3": output_mp3.as_posix(),
                "mp3_sha256": file_sha256(output_mp3),
                "sample_rate_hz": 48000,
                "channels": 2,
            },
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"- {active}: program audio ready -> {output_wav} + {output_mp3} "
            f"({len(sfx_events)} SFX)"
        )
        return 0
    except Exception as exc:
        print(f"SOUNDTRACK ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
