#!/usr/bin/env python3
"""Policy guards for the optional soundtrack stage.

The factory repository is public and currently operates under a zero-cost media
policy. Before mixing program audio we enforce two things:

1. paid media generation (including Lyria) is blocked by factory_policy.yaml;
2. raw SFX committed to the public repo must explicitly permit redistribution.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_soundtrack as core  # noqa: E402


class SfxLicenseError(RuntimeError):
    pass


class PaidMediaPolicyError(RuntimeError):
    pass


def load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Missing YAML file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected YAML mapping in {path}")
    return data


def validate_zero_cost_policy(
    input_root: Path = Path("input"),
    policy_path: Path = ROOT / "factory_policy.yaml",
) -> None:
    active = core.read_active(input_root / "ACTIVE")
    if not active:
        return

    job_dir = input_root / active
    job = load_mapping(job_dir / "job.yaml")
    soundtrack = job.get("soundtrack") or {}
    if not isinstance(soundtrack, dict) or not bool(soundtrack.get("enabled", False)):
        return

    music = soundtrack.get("music") or {}
    if not isinstance(music, dict) or not bool(music.get("enabled", False)):
        return

    policy = load_mapping(policy_path)
    cost = policy.get("cost") or {}
    paid_media_allowed = bool(cost.get("paid_media_generation", False))
    source = str(music.get("source", "file")).strip().lower()

    if source == "lyria" and not paid_media_allowed:
        raise PaidMediaPolicyError(
            "Lyria is blocked by factory_policy.yaml: paid_media_generation=false. "
            "This factory is configured for $0 incremental media spend. Use a local "
            "owned/CC0 music file or disable background music."
        )


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
        validate_zero_cost_policy()
        validate_public_repo_sfx()
    except Exception as exc:
        print(f"SOUNDTRACK POLICY ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
