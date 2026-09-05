# Video Factory — Agent Contract

This repository is an operational **video production factory**. TTS is one internal stage.

An agent should be able to enter a fresh conversation, read this file, inspect `input/ACTIVE`, and continue the current production without relying on chat memory.

Also read [`docs/PRODUCTION_PLAYBOOK.md`](docs/PRODUCTION_PLAYBOOK.md) before authoring or approving video, [`docs/visual-production.md`](docs/visual-production.md) before planning visuals, and [`docs/SOUNDTRACK.md`](docs/SOUNDTRACK.md) whenever music or SFX are enabled.

## Golden rule

**Humans/agents provide new job source only under `input/<job-id>/`.**

Do not invent a second source-of-truth folder. Do not ask the user to manually populate `transcripts/`, `audio/`, `done/`, or `final/`.

`input/ACTIVE` selects the one production allowed to advance. Multiple input job folders may coexist, but process one at a time for now.

## Production providers

### Narration

Production narration is **Qwen3-TTS 0.6B on Modal**.

- Provider implementation: `scripts/process_tts_qwen.py`
- Default voice: `Aiden`
- Default language: `English`
- Modal service source repository: `addvaluewithai-hub/free-image-editing`
- That repository name is legacy; for Video Factory it is a **TTS provider only**.
- Manual client/docs: `tools/qwen-tts/`

The private Modal endpoint requires `QWEN_TTS_API_URL`, `MODAL_PROXY_TOKEN_ID`, and `MODAL_PROXY_TOKEN_SECRET`.

Gemini is not the narration renderer. The current alignment stage may still use Gemini audio-input models to produce word timing.

### Images

Production image generation uses the private Image Generation API:

`https://agent.wpaikits.site/v1/workflow/jobs-images`

Authentication is through `IMAGE_API_TOKEN` only. Manual client/docs: `tools/image-gen/`.

Do **not** use `addvaluewithai-hub/free-image-editing` for image generation in Video Factory. The private Image Generation API is the approved image provider.

## When the user says “the next video/lesson is ready, make it”

1. Read `input/ACTIVE` and the active job folder.
2. Read `job.yaml`, `direction.md`, transcript parts, and any optional assets/references/data/music/SFX.
3. Validate the input package before changing production state.
4. Run/trigger the audio stage and resolve real failures from logs. Do not mutate content to solve infrastructure/rate-limit errors.
5. Wait for a successful dry master audio + `final/<job>.transcript.json` from the same state.
6. If soundtrack is enabled, verify the intended music/SFX mix and its soundtrack manifest before video QA.
7. Build an image-first storyboard from the direction and exact timing. Generate/curate required visual assets through the approved Image Generation API and download any assets needed beyond the service's temporary hosting window.
8. Author/update deterministic video source under `productions/<job>/video/` using generated images, overlays, text breaks, and exact word timing.
9. Run authoritative HyperFrames QA using the intended program audio.
10. Download the QA artifact and **actually open every required full-resolution image**. Automated checks/contact sheets are insufficient.
11. Patch visual/source issues, rerun QA, and repeat manual review until clean.
12. Create/update approval bound to the current video source SHA and transcript SHA-256.
13. Run final render.
14. Verify final MP4 media properties and duration.
15. Open representative frames extracted from the final MP4.
16. Notify the user that the video is ready only after the final artifact manifest exists and the manual final-frame gate passes.

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
  music/
  sfx/
    manifest.yaml
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

soundtrack:
  enabled: false

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

`scripts/ingest_input.py` materializes only changed active transcript parts into the internal `transcripts/<job-id>/` queue. The legacy queue is an implementation detail. Do not manually copy inputs there.

## Transcript/TTS rules

1. Use short numbered source files in playback order.
2. Short files are retry/retake boundaries, not video scene boundaries.
3. Qwen's service hard limit is 2400 characters per request; the factory targets 2200 for headroom.
4. Default narrator is `Aiden` / `English` unless a job intentionally overrides it.
5. Qwen3-TTS 0.6B CustomVoice does not provide reliable free-form style instruction. Write performance into the copy through wording, punctuation, sentence length, pauses, and chunk boundaries.
6. Renderer-only bracket cues and XML-like tags are stripped before Qwen synthesis so they are not spoken. Do not rely on SSML or IPA input at the Qwen API layer.
7. `Speaker 1:` role labels should not be spoken. Prefer omitting them in new single-speaker inputs.
8. Runtime synthesis should faithfully render the authored speakable transcript. Source editing flexibility is a separate authoring decision.
9. Voice cloning through Qwen 0.6B Base is allowed only with an owned/authorized reference. High-fidelity clone requests should include the exact reference transcript.

### Rate-limit / provider-failure behavior

Provider 429/5xx/transport failures are infrastructure events, not content-quality signals.

- preserve successful parts;
- retry individual requests with bounded exponential backoff;
- keep a bounded whole-factory recovery loop;
- inspect real logs if failures persist;
- do not change transcript wording merely to solve infrastructure failure.

## Audio run contract

Preferred GitHub production path is the **Video Factory — Audio** workflow.

Local equivalent:

```bash
python scripts/ingest_input.py
python scripts/run_factory.py
```

Internal stage order:

```text
1. TTS (Qwen Modal)
2. Assemble
3. Align
4. Soundtrack (optional; no-op unless enabled)
```

A completed dry audio job produces:

```text
final/<job-id>.wav
final/<job-id>.mp3
final/<job-id>.json
final/<job-id>.transcript.json
final/<job-id>.transcript.vtt
```

A soundtrack-enabled job may additionally produce:

```text
final/<job-id>.music.mp3
final/<job-id>.music.json
final/<job-id>.mix.wav
final/<job-id>.mix.mp3
final/<job-id>.soundtrack.json
```

The authoritative timing handoff is always `final/<job-id>.transcript.json` (schema v2, per-part alignment). Dry narration is the timing master. Video QA/final render use `final/<job-id>.mix.wav` when present, otherwise the dry `final/<job-id>.wav`.

Use `parts[]` for deterministic audio boundaries and `words[]` for word-driven visual cues. Do not assume one audio part equals one visual scene.

## Soundtrack rules

1. Soundtrack and paid music generation are opt-in. Never enable paid generation merely because a job can support it.
2. Generated music must be cached/reused by request fingerprint; unrelated retries must not create duplicate paid requests.
3. Default educational/explainer beds to instrumental/no-vocals unless creative direction explicitly requires vocals.
4. Keep music subordinate to narration and use ducking.
5. Prefer word-timed SFX anchors over hard-coded seconds when the cue is tied to speech.
6. This repository is public. Commit raw SFX under `input/<job>/sfx/` only when the exact asset license permits raw redistribution; the manifest must assert `redistribution: true`.
7. Prefer CC0 audio packs for common UI/transition/impact sounds. CC BY is allowed only when redistribution is permitted and required attribution is preserved. Reject CC BY-NC for commercial work.
8. Do not hot-link, scrape, or mass-download SFX libraries during render. Curate sounds intentionally and preserve source/license evidence.
9. Every used SFX must have `source_url`, exact `license`, and `redistribution: true` in `sfx/manifest.yaml`; preserve attribution where required.
10. `final/<job>.soundtrack.json` is the traceability manifest for the program-audio mix.

## Visual production contract

The default strategy is **image-first storytelling**.

Editorial target, not a hard quota:

- ~70–80% generated-image-led shots;
- ~10–20% text-led rhythm breaks with animated background patterns;
- ~10% diagrams/labels/counters/arrows/charts/explanatory overlays.

Prefer generated images for environmental, emotional, and narrative context. Create motion in post through push-ins, pans, reframing, parallax, compositing, masks, and transitions.

Text-only scenes are appropriate for punchlines, surprising numbers, section pivots, questions, and concise conclusions.

Use diagrams when they materially improve comprehension. Do not default to building full narrative scenes in HTML/CSS/vector UI merely because the rendering engine can do it.

Do not ask the image model to render critical small text or dense exact diagrams. Generate the frame and add controlled typography/data overlays afterward.

Generated VPS image URLs expire after 24 hours. Download required assets into production storage promptly.

Every image/composite storyboard beat should record its generation prompt and target aspect ratio. Use references only when they materially improve continuity/fidelity and only when we own or are authorized to use them.

Full policy: [`docs/visual-production.md`](docs/visual-production.md).

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

HyperFrames remains the deterministic render/QA shell; it is not the default visual source generator. Generated images and other assets should be composed inside it.

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

Review composition, hierarchy, clipping, edge safety, readability, containment, balance, generated-image artifacts, continuity, and intentional motion.

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

If source or transcript changes, old approval is invalid. When soundtrack changes after QA, rerun QA so final render uses the same intended program-audio state that was reviewed.

## Final render contract

Before final render:

- approval source/hash must match current state;
- HyperFrames lint/check must pass.

After render:

- MP4 is non-empty;
- requested resolution/fps are correct;
- duration matches the audio master within production tolerance;
- representative frames are extracted from the final MP4 and manually opened;
- final artifact + manifest are published.

## Definition of done

A job is **not done** until:

- dry audio master and timing handoff are successful and consistent;
- optional soundtrack mix is current when enabled;
- generated image assets required by the production are downloaded and reviewed;
- video QA automation passes with the intended program audio;
- all required QA frames/strips were manually opened and accepted;
- hash-bound approval is current;
- final render and media verification pass;
- representative final MP4 frames were manually opened;
- final artifact manifest exists.

If any gate is missing, report the exact blocker/status rather than saying the video is ready.

## Historical repositories

The separate `addvaluewithai-hub/videos` repository contains earlier production history. Do not build new production architecture in the old repo unless explicitly requested.
