#!/usr/bin/env python3
"""License guard for the soundtrack stage.

The factory repository is public. Before mixing any job-local raw SFX file, require
an explicit manifest assertion that its license permits redistribution of the raw
asset. This prevents stock-library files that are licensed for end products but
not standalone redistribution from being committed and reused as source assets.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_soundtrack as core  # noqa: E402


class SfxLicenseError(RuntimeError):
    pass


def load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SfxLicenseError(f"Missing YAML file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SfxLicenseError(f"Expected YAML mapping in {path}")
    return data


def validate_public_repo_sfx(input_root: Path = Path("input")) -> None:
    active = core.read_active(input_root / "ACTIVE")
    if not active:
        return

    job_dir = input_root / active
    job = load_mapping(job_dir / "job.yaml")
    soundtrack = job.get("soundtrack") or {}
    if not isinstance(soundtrack, dict) or not bool(soundtrack.get("enabled", False)):
        return

    sfx = soundtrack.get("sfx") or {}
    if not isinstance(sfx, dict) or not bool(sfx.get("enabled", False)):
        return

    events = sfx.get("events") or []
    if not isinstance(events, list):
        raise SfxLicenseError("soundtrack.sfx.events must be a list")
    if not events:
        return

    manifest = load_mapping(job_dir / "sfx" / "manifest.yaml")
    files = manifest.get("files") or {}
    if not isinstance(files, dict):
        raise SfxLicenseError("sfx/manifest.yaml 'files' must be a mapping")

    used_files = []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise SfxLicenseError(f"SFX event #{index} must be a mapping")
        filename = str(event.get("file", "")).strip()
        if not filename:
            raise SfxLicenseError(f"SFX event #{index} is missing file")
        used_files.append(filename)

    for filename in sorted(set(used_files)):
        meta = files.get(filename)
        if not isinstance(meta, dict):
            raise SfxLicenseError(f"SFX file {filename!r} is missing from sfx/manifest.yaml")
        if meta.get("redistribution") is not True:
            raise SfxLicenseError(
                f"SFX file {filename!r} is not approved for raw redistribution. "
                "Because this repository is public, set redistribution: true only "
                "when the exact asset license permits storing/distributing the raw file "
                "(for example CC0). Otherwise keep that stock asset out of the repo."
            )


def main() -> int:
    try:
        validate_public_repo_sfx()
    except Exception as exc:
        print(f"SFX LICENSE ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
