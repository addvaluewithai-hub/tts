#!/usr/bin/env python3
"""Small CLI for the private Qwen3-TTS 0.6B Modal service.

The service itself is deployed from addvaluewithai-hub/free-image-editing.
That repository name is legacy: for Video Factory it is a TTS provider only.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests


def auth_headers() -> dict[str, str]:
    token_id = os.environ.get("MODAL_PROXY_TOKEN_ID")
    token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET")
    if not token_id or not token_secret:
        raise SystemExit(
            "Set MODAL_PROXY_TOKEN_ID and MODAL_PROXY_TOKEN_SECRET. "
            "Create a Modal proxy token with: modal workspace proxy-tokens create"
        )
    return {"Authorization": f"Bearer {token_id}.{token_secret}"}


def base_url(value: str | None) -> str:
    url = value or os.environ.get("QWEN_TTS_API_URL")
    if not url:
        raise SystemExit("Pass --url or set QWEN_TTS_API_URL")
    return url.rstrip("/")


def generate_preset(
    *,
    url: str,
    text: str,
    speaker: str,
    language: str,
    timeout: float,
) -> bytes:
    response = requests.post(
        f"{url}/tts",
        headers={**auth_headers(), "Content-Type": "application/json"},
        json={"text": text, "speaker": speaker, "language": language},
        timeout=timeout,
    )
    if not response.ok:
        raise SystemExit(f"Qwen HTTP {response.status_code}: {response.text[:1000]}")
    return response.content


def generate_clone(
    *,
    url: str,
    reference: Path,
    text: str,
    reference_text: str | None,
    language: str,
    x_vector_only: bool,
    timeout: float,
) -> bytes:
    if not x_vector_only and not reference_text:
        raise SystemExit(
            "--reference-text is required for high-fidelity cloning. "
            "Use --x-vector-only only when the transcript is unavailable."
        )
    with reference.open("rb") as handle:
        response = requests.post(
            f"{url}/clone",
            headers=auth_headers(),
            files={"reference": (reference.name, handle)},
            data={
                "text": text,
                "reference_text": reference_text or "",
                "language": language,
                "x_vector_only": "true" if x_vector_only else "false",
            },
            timeout=timeout,
        )
    if not response.ok:
        raise SystemExit(f"Qwen HTTP {response.status_code}: {response.text[:1000]}")
    return response.content


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the private Qwen3-TTS 0.6B Modal API")
    parser.add_argument("--url", help="Defaults to QWEN_TTS_API_URL")
    parser.add_argument("--timeout", type=float, default=900)
    sub = parser.add_subparsers(dest="command", required=True)

    preset = sub.add_parser("tts", help="Use a built-in CustomVoice speaker")
    preset.add_argument("text")
    preset.add_argument("--speaker", default="Aiden")
    preset.add_argument("--language", default="English")
    preset.add_argument("--out", default="qwen.wav")

    clone = sub.add_parser("clone", help="Clone a voice with the 0.6B Base model")
    clone.add_argument("reference", type=Path)
    clone.add_argument("text")
    clone.add_argument("--reference-text")
    clone.add_argument("--language", default="English")
    clone.add_argument("--x-vector-only", action="store_true")
    clone.add_argument("--out", default="qwen-clone.wav")

    args = parser.parse_args()
    url = base_url(args.url)

    if args.command == "tts":
        audio = generate_preset(
            url=url,
            text=args.text,
            speaker=args.speaker,
            language=args.language,
            timeout=args.timeout,
        )
        out = Path(args.out)
    else:
        audio = generate_clone(
            url=url,
            reference=args.reference,
            text=args.text,
            reference_text=args.reference_text,
            language=args.language,
            x_vector_only=args.x_vector_only,
            timeout=args.timeout,
        )
        out = Path(args.out)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
