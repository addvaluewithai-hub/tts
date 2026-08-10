# Video Factory — Agent Contract

This repository is an operational **video production factory**. TTS is one internal stage.

An agent should be able to enter a fresh conversation, read this file, inspect `input/ACTIVE`, and continue the current production without relying on chat memory.

Also read [`docs/PRODUCTION_PLAYBOOK.md`](docs/PRODUCTION_PLAYBOOK.md) before authoring or approving video.

## Golden rule

**Humans/agents provide new job source only under `input/<job-id>/`.**

Do not invent a second source-of-truth folder. Do not ask the user to manually populate `transcripts/`, `audio/`, `done/`, or `final/`.

`input/ACTIVE` selects the one production allowed to advance. Multiple input job folders may coexist, but process one at a time for now.

## When the user says “the next video/lesson is ready, make it”

1. Read `input/ACTIVE` and the active job folder.
2. Read `job.yaml`, `direction.md`, transcript parts, and any optional assets/references/data.
3. Validate the input package before changing production state.
4. Run/trigger the audio stage and resolve real failures from logs. Do not mutate content to solve infrastructure/rate-limit errors.
5. Wait for a successful master audio + `final/<job>.transcript.json` from the same state.
6. Author/update deterministic video source under `productions/<job>/video/` using the job direction and exact word timing.
7. Run authoritative HyperFrames QA.
8. Download the QA artifact and **actually open every required full-resolution image**. Automated checks/contact sheets are insufficient.
9. Patch visual/source issues, rerun QA, and repeat manual review until clean.
10. Create/update approval bound to the current video source SHA and transcript SHA-256.
11. Run final render.
12. Verify final MP4 media properties and duration.
13. Open representative frames extracted from the final MP4.
14. Notify the user that the video is ready only after the final artifact manifest exists and the manual final-frame gate passes.

## Input contract

Minimum active job:

```text
input/<job-id>/
  job.yaml
  direction.md
  transcript/
    01-part.txt
    02-part.txt
    ...
```

Optional:

```text
  pronunciation-map.json
  assets/
  references/
  data/
```

`direction.md` may contain course-specific, brand-specific, language-specific, or one-off creative instructions. Keep those out of repository-wide instructions.

### `job.yaml`

Current minimal schema:

```yaml
schema: 1
id: my-video
title: My Video
kind: video

audio:
  enabled: true

video:
  enabled: true
  engine: hyperframes
  width: 1920
  height: 1080
  fps: 30
  qa_fps: 6
  manual_visual_review: true
```

The `id` must exactly match the job folder name and `input/ACTIVE`.

## Internal audio queue

`scripts/ingest_input.py` materializes only changed active transcript parts into the proven internal `transcripts/<job-id>/` queue.

The legacy queue is intentionally preserved as an implementation detail while the larger video factory stabilizes.

Do not manually copy inputs there.

## Transcript/TTS rules

1. Use short numbered source files in playback order.
2. Short files are retry/retake boundaries, not video scene boundaries.
3. Do not introduce per-part max-character tuning as normal production behavior.
4. Global `max_chars_per_request` is an emergency/internal safety net only.
5. For one narrator, use `voice:`. `speakers:` is for genuine multi-speaker work.
6. Treat `[PERFORMANCE]`, `<lang>`, `<phoneme>`, and IPA tied to visible English as protected production markup unless intentionally revising pronunciation.
7. `Speaker 1:` role labels should not be spoken. Prefer omitting them in new single-speaker inputs.
8. Runtime synthesis should faithfully render the authored transcript. Source editing flexibility is a separate authoring decision.

### Rate-limit behavior

Gemini 429 is an infrastructure/quota event, not a content-quality signal.

- preserve successful parts;
- stop advancing the batch after a quota error;
- wait 60 seconds;
- retry remaining work in the same workflow run;
- cap retries;
- inspect real logs if quota persists.

Do not respond to 429 by changing transcript text, SSML-like markup, IPA, or per-part character limits.

## Audio run contract

Preferred GitHub production path is the **Video Factory — Audio** workflow.

Local equivalent:

```bash
python scripts/ingest_input.py
python scripts/run_factory.py
```

Internal stage order:

```text
1. TTS
2. Assemble
3. Align
```

A completed audio job produces:

```text
final/<job-id>.wav
final/<job-id>.mp3
final/<job-id>.json
final/<job-id>.transcript.json
final/<job-id>.transcript.vtt
```

The authoritative video handoff is `final/<job-id>.transcript.json` (schema v2, per-part alignment).

Use `parts[]` for deterministic audio boundaries and `words[]` for word-driven visual cues. Do not assume one audio part equals one visual scene.

## Video authoring contract

Agent-authored deterministic source lives at:

```text
productions/<job-id>/video/
```

A production may have custom files/layout, but its build must generate:

```text
index.html
build-meta.json
```

`build-meta.json` must include:

- duration;
- transcript SHA-256;
- semantic scene boundaries;
- `finalHolds[]` timestamps;
- `riskBeats[]` timestamps.

The current HyperFrames reference production is `productions/introduce-yourself/video/`.

## HyperFrames non-negotiables

- Exactly one root `.html` composition. Editable source templates use `.tpl` or another non-HTML extension.
- Timed scenes have stable IDs and `class="clip ..."`.
- Audio elements have stable IDs.
- Authoritative animation is deterministic and timeline-driven.
- Lint/check/inspect failures are real failures.
- Any `... | tee ...` validation command uses `set -o pipefail`.
- A QA render success does not equal visual approval.

### Lottie

Register the real lottie-web AnimationItem once in `window.__hfLottie`. Do not register both a wrapper and the original auto-discovered instance. Scene-local animation seeking must not be overwritten by a second global seek.

## Visual QA contract

Manual review is mandatory when `manual_visual_review: true`.

Open every:

- full-resolution scene final;
- risk beat;
- full-duration scene progression strip.

Do not claim review based only on file existence, lint, inspect, a contact sheet, or an automated image test.

Review composition, hierarchy, clipping, bidi/RTL, edge safety, readability, containment, balance, and intentional motion.

### Screenshot generation rules

- Clamp risk beats inside the visible scene after reveal time; boundary frames can be blank.
- Progression strips sample each complete scene duration.
- Use `ffmpeg -nostdin` in shell loops.
- Verify expected screenshot counts.

## Approval contract

Approval must bind review to:

```text
source_sha=<exact video source SHA>
transcript_sha256=<exact final audio transcript hash>
visual_review=all_full_resolution_scene_holds_opened
```

If source or transcript changes, old approval is invalid.

## Final render contract

Before final render:

- approval source/hash must match current state;
- HyperFrames lint/check must pass.

After render:

- MP4 is non-empty;
- requested resolution/fps are correct (default 1920×1080 / 30fps);
- duration is within 0.15 seconds of the audio master;
- representative frames are extracted from the final MP4 and manually opened;
- final artifact + manifest are published.

Do not use fragile tab-escape shell parsing for review timestamps.

## Definition of done

A job is **not done** until:

- audio master and timing handoff are successful and consistent;
- video QA automation passes;
- all required QA frames/strips were manually opened and accepted;
- hash-bound approval is current;
- final render and media verification pass;
- representative final MP4 frames were manually opened;
- final artifact manifest exists.

If any gate is missing, report the exact blocker/status rather than saying the video is ready.

## Historical repositories

The separate `addvaluewithai-hub/videos` repository contains earlier production history. The canonical approved Lesson 01 V4 source is being migrated here as a reference. Do not build new production architecture in the old repo unless explicitly requested.
