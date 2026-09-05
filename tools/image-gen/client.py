#!/usr/bin/env python3
"""CLI for the private Image Generation API used by Video Factory.

Preferred live base URL:
https://agent.wpaikits.site/v1/workflow/jobs-images

Authentication is bearer-token only via IMAGE_API_TOKEN. Generated files are
hosted temporarily by the service, so callers should download them immediately
when they need durable local/project storage.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

DEFAULT_BASE_URL = "https://agent.wpaikits.site/v1/workflow/jobs-images"
TERMINAL_SUCCESS = {"complete", "completed", "succeeded", "success"}
TERMINAL_FAILURE = {"failed", "error", "cancelled", "canceled"}


def api_token() -> str:
    token = os.environ.get("IMAGE_API_TOKEN")
    if not token:
        raise SystemExit("Set IMAGE_API_TOKEN before using the image API")
    return token


def base_url(value: str | None = None) -> str:
    return (value or os.environ.get("IMAGE_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def auth_headers(*, json_body: bool = False) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_token()}"}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def encode_reference(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SystemExit(f"Reference image not found: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "name": path.name,
        "mime": mime,
        "data_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def resolve_url(value: str, *, base: str) -> str:
    """Resolve API URLs without duplicating the compatibility prefix.

    The VPS returns root-relative URLs such as
    `/v1/workflow/jobs-images/jobs/<id>`. Those must resolve from the site origin,
    not from the configured API prefix.
    """
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        parsed = urlsplit(base)
        return f"{parsed.scheme}://{parsed.netloc}{value}"
    return urljoin(base.rstrip("/") + "/", value)


def request_json(method: str, url: str, *, payload: dict[str, Any] | None = None, timeout: float = 120) -> dict[str, Any]:
    response = requests.request(
        method,
        url,
        headers=auth_headers(json_body=payload is not None),
        json=payload,
        timeout=timeout,
    )
    if not response.ok:
        raise SystemExit(f"Image API HTTP {response.status_code}: {response.text[:1500]}")
    try:
        data = response.json()
    except ValueError as exc:
        raise SystemExit("Image API returned non-JSON status data") from exc
    if not isinstance(data, dict):
        raise SystemExit("Image API returned an unexpected JSON payload")
    return data


def status_name(data: dict[str, Any]) -> str:
    return str(data.get("status", "")).strip().lower()


def poll_status(status_url: str, *, base: str, interval: float, timeout_seconds: float) -> dict[str, Any]:
    url = resolve_url(status_url, base=base)
    deadline = time.monotonic() + timeout_seconds
    while True:
        data = request_json("GET", url, timeout=min(120, timeout_seconds))
        state = status_name(data)
        if state in TERMINAL_SUCCESS:
            return data
        if state in TERMINAL_FAILURE:
            raise SystemExit(f"Image job failed: {json.dumps(data, ensure_ascii=False)[:2000]}")
        if time.monotonic() >= deadline:
            raise SystemExit(f"Timed out waiting for image job at {url}")
        time.sleep(interval)


def download_file(download_url: str, out: Path, *, base: str, timeout: float = 120) -> None:
    url = resolve_url(download_url, base=base)
    response = requests.get(url, headers=auth_headers(), timeout=timeout)
    if not response.ok:
        raise SystemExit(f"Image download HTTP {response.status_code}: {response.text[:1000]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.content)


def image_download_url(data: dict[str, Any]) -> str:
    image = data.get("image")
    if isinstance(image, dict) and image.get("download_url"):
        return str(image["download_url"])
    if data.get("download_url"):
        return str(data["download_url"])
    raise SystemExit(f"Completed image job has no download URL: {json.dumps(data, ensure_ascii=False)[:1500]}")


def generate_one(args: argparse.Namespace) -> None:
    base = base_url(args.base_url)
    payload = {
        "prompt": args.prompt,
        "aspect_ratio": args.aspect_ratio,
        "output_format": args.output_format,
        "references": [encode_reference(Path(value)) for value in args.ref],
    }
    created = request_json("POST", f"{base}/jobs", payload=payload, timeout=args.request_timeout)
    status_url = created.get("status_url")
    if not status_url:
        raise SystemExit(f"Image API response has no status_url: {json.dumps(created, ensure_ascii=False)[:1500]}")
    finished = poll_status(
        str(status_url),
        base=base,
        interval=args.poll_interval,
        timeout_seconds=args.timeout,
    )
    out = Path(args.out)
    download_file(image_download_url(finished), out, base=base, timeout=args.request_timeout)
    print(f"Saved {out}")


def load_batch_requests(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    requests_data = raw.get("requests") if isinstance(raw, dict) else raw
    if not isinstance(requests_data, list) or not (1 <= len(requests_data) <= 20):
        raise SystemExit("Batch JSON must contain 1..20 requests")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(requests_data, start=1):
        if not isinstance(item, dict) or not str(item.get("prompt", "")).strip():
            raise SystemExit(f"Batch request #{index} requires a prompt")
        refs: list[dict[str, str]] = []
        for ref in item.get("references", []) or []:
            if isinstance(ref, str):
                refs.append(encode_reference(Path(ref)))
            elif isinstance(ref, dict) and ref.get("data_base64"):
                refs.append(ref)
            else:
                raise SystemExit(f"Batch request #{index} has an invalid reference")
        normalized.append(
            {
                "prompt": str(item["prompt"]),
                "aspect_ratio": str(item.get("aspect_ratio", "16:9")),
                "output_format": str(item.get("output_format", "png")),
                "references": refs,
            }
        )
    return normalized


def collect_child_downloads(data: dict[str, Any]) -> list[str]:
    candidates = data.get("jobs") or data.get("results") or data.get("requests") or []
    if not isinstance(candidates, list):
        return []
    urls: list[str] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        image = item.get("image")
        if isinstance(image, dict) and image.get("download_url"):
            urls.append(str(image["download_url"]))
        elif item.get("download_url"):
            urls.append(str(item["download_url"]))
    return urls


def generate_batch(args: argparse.Namespace) -> None:
    base = base_url(args.base_url)
    requests_data = load_batch_requests(Path(args.requests))
    created = request_json(
        "POST",
        f"{base}/batches",
        payload={"requests": requests_data},
        timeout=args.request_timeout,
    )
    status_url = created.get("status_url")
    if not status_url:
        raise SystemExit(f"Batch response has no status_url: {json.dumps(created, ensure_ascii=False)[:1500]}")
    finished = poll_status(
        str(status_url),
        base=base,
        interval=args.poll_interval,
        timeout_seconds=args.timeout,
    )
    urls = collect_child_downloads(finished)
    if not urls:
        raise SystemExit(
            "Batch completed but child download URLs were not found in the response. "
            "Inspect the returned batch payload and update the client if the service contract changed."
        )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = args.output_format.lstrip(".")
    for index, url in enumerate(urls, start=1):
        out = out_dir / f"{index:02d}.{suffix}"
        download_file(url, out, base=base, timeout=args.request_timeout)
        print(f"Saved {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Private Video Factory image generation API client")
    parser.add_argument("--base-url", help=f"Defaults to IMAGE_API_BASE_URL or {DEFAULT_BASE_URL}")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--request-timeout", type=float, default=120)
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("generate", help="Generate one image")
    one.add_argument("--prompt", required=True)
    one.add_argument("--aspect-ratio", default="16:9")
    one.add_argument("--output-format", default="png")
    one.add_argument("--ref", action="append", default=[], help="Optional reference image path; repeatable")
    one.add_argument("--out", required=True)
    one.set_defaults(func=generate_one)

    batch = sub.add_parser("batch", help="Generate 1..20 images from a JSON request file")
    batch.add_argument("--requests", required=True, help="JSON file containing a requests array")
    batch.add_argument("--out-dir", required=True)
    batch.add_argument("--output-format", default="png", help="Filename suffix for downloaded batch results")
    batch.set_defaults(func=generate_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()