# Video Factory Production Playbook

This file records the production lessons that must survive across conversations and agents.

The factory is **audio-first, timing-driven, visually reviewed, and one active job at a time**.

## End-to-end lifecycle

```text
input/<job-id>/
  ↓
ingest active job
  ↓
short TTS parts
  ↓
assembled master WAV/MP3
  ↓
word alignment JSON/VTT
  ↓
author productions/<job-id>/video from direction + timing
  ↓
HyperFrames lint/check + QA render
  ↓
manual full-resolution visual review
  ↓
approval bound to source SHA + transcript hash
  ↓
final 1920×1080 / 30fps render
  ↓
ffprobe + representative final-frame review
  ↓
final artifact
```

A stage is not complete because files merely exist. Downstream work uses only outputs from a successful, internally consistent stage.

## Input philosophy

`input/<job-id>/` is intentionally flexible. The minimum is:

- `job.yaml`
- `direction.md`
- `transcript/` when audio is enabled

Optional assets, reference material, pronunciation maps, data, and project-specific instructions stay beside that job. Repository-wide rules stay here or in `AGENTS.md`.

Several input folders may exist. `input/ACTIVE` selects the single production currently allowed to move through the pipeline.

## Audio lessons we learned

### Short TTS parts, but do not couple them to video scenes

Long TTS requests are less reliable and harder to retake. Author several short, stable, numbered transcript files.

Those files are **transport/retry boundaries**. Video scene count is a separate editorial decision. A future lesson may have 8 TTS parts and 12 scenes, or 12 TTS parts and 7 scenes.

### `max_chars_per_request` is an internal safety net

Do not tune per-part max-character values during normal production. We already control production reliability by authoring short files. The global maximum protects the implementation from pathological input; it is not part of lesson design.

### Rate limits must not become request spam

Gemini TTS can return HTTP 429 quota/rate-limit errors. The safe pattern is:

1. preserve any parts that already succeeded;
2. stop advancing through more pending parts once quota is hit;
3. wait roughly one quota window (currently 60 seconds in the GitHub workflow);
4. retry the remaining work **inside the same workflow run**;
5. cap retries so a job cannot hang forever.

Do not respond to quota failures by rewriting transcript content, changing pronunciation markup, or adding arbitrary per-part limits.

### One speaker means `voice:`

For a single narrator/teacher, use `voice:`. Reserve `speakers:` for genuine multi-speaker synthesis. A one-item multi-speaker mapping adds unnecessary ambiguity.

`Speaker 1:`-style text is a role marker, not learner-facing spoken copy. Prefer omitting it in new single-speaker input. If legacy source contains it, treat it as silent control metadata, not content to emphasize.

### Protect pronunciation/performance markup

Do not casually edit:

- bracketed performance directions such as `[WARM]` or `[CLEARLY]`;
- `<lang>` / `<phoneme>` markup;
- IPA pronunciation attributes tied to visible English examples.

Other source wording may be edited when there is a real teaching/production reason, but pronunciation markup must remain internally consistent.

The TTS runtime should synthesize the authored source faithfully; source authoring flexibility and runtime model faithfulness are different concerns.

## Audio → video handoff

The authoritative video timing input is:

```text
final/<job-id>.transcript.json
```

Current audio alignment schema is v2. Use:

- `duration_ms` for the master duration;
- `parts[]` for deterministic audio-part boundaries;
- `words[]` for captions, highlights, graphics, and semantic cue timing.

Word timing is model-derived alignment, not phoneme/sample-accurate lip sync.

Do not start final video approval until the master audio and transcript JSON belong to the same successful audio factory state.

## HyperFrames contract

Every production video lives at:

```text
productions/<job-id>/video/
```

The agent may design each video differently, but the folder must provide a deterministic build that creates:

```text
index.html
build-meta.json
```

`build-meta.json` must contain at least:

- final duration;
- transcript SHA-256;
- semantic scenes with start/end/duration;
- `finalHolds[]` — one meaningful final-state review timestamp per scene;
- `riskBeats[]` — timestamps chosen around visually risky reveals/transitions.

### Avoid the HyperFrames failures we already hit

1. **Exactly one root HTML composition.** Keep editable HTML templates as `.tpl` (or another non-`.html` extension). Multiple root `.html` files can be discovered as separate compositions.
2. Timed scene containers use a stable `id` and `class="clip ..."`.
3. Audio elements have stable IDs. A bare `<audio>` can be rejected or render incorrectly.
4. Run lint/check against the production directory, not a command form that accidentally bypasses project-level checks.
5. Shell pipelines that use `tee` must enable `set -o pipefail`; otherwise `tee` can hide a real lint failure.
6. Do not let generated `index.html` become the editable source. Build it deterministically from `.tpl` + exact audio timing.
7. Keep animation deterministic: paused GSAP timeline, no wall-clock timers, random motion, or infinite repeats in the authoritative render path.

## Lottie rule

When using lottie-web with HyperFrames, register the **actual AnimationItem once** in `window.__hfLottie` and make its seeking scene-local if necessary.

Do not register a wrapper while leaving the original AnimationItem auto-discoverable. HyperFrames can seek both objects and the second seek can overwrite the intended state (for example, forcing a scene-local animation to its empty end frame).

Lottie must be visibly contained inside its intended region at multiple timestamps; successful loading alone is not visual QA.

## Visual QA is manual, not just automated

Lint, validate/check, inspect, render success, and contact sheets are useful gates. They are **not visual approval**.

For the authoritative QA artifact, the reviewer/agent must actually open:

- every full-resolution scene final hold;
- every risk-beat screenshot;
- every scene progression strip.

Judge at least:

- composition and hierarchy;
- clipping/overflow;
- Arabic/English bidi behavior;
- edge safety;
- text readability and contrast;
- asset/Lottie containment;
- visual balance;
- whether motion/reveals happen intentionally across the whole scene.

Do not claim visual review unless those images were genuinely opened.

### QA screenshot lessons

- A risk timestamp exactly at a scene boundary can capture a blank/pre-reveal frame. Clamp risk beats to a safe visible offset inside the target scene.
- Progression strips must sample the **full scene duration**, not merely the first N seconds.
- Use `ffmpeg -nostdin` inside shell loops; otherwise FFmpeg can consume the loop's stdin and silently prevent later scenes from being processed.
- Verify that the expected number of finals, risks, and strips were produced before approval.

## Approval gate

Approval is a file, not a feeling. It must bind the manual review to both:

- the exact video source SHA;
- the exact audio transcript SHA-256.

If either changes, the old approval is stale and a new authoritative QA/manual review is required.

## Final render gate

The final workflow must:

1. verify approval source/hash match;
2. lint/check again;
3. render the synchronized MP4;
4. verify the file is non-empty;
5. use `ffprobe` to verify codec/resolution/fps/duration;
6. require 1920×1080 and 30fps unless the job explicitly says otherwise;
7. keep duration within 0.15 seconds of the audio master;
8. extract representative final-render frames;
9. open those frames manually before declaring production ready;
10. publish an artifact manifest only after all of the above pass.

Avoid fragile shell parsing for review timestamps. In particular, do not emit literal `\\t` from JavaScript and then expect Bash `IFS=$'\\t'` to parse it. Use newline arrays, JSON, or another unambiguous mechanism.

## Render-performance lesson

A four-minute 1080p/30fps HyperFrames render should not be diagnosed from wall-clock time alone. First inspect the workflow step state.

During Lesson 01, an apparent long render was actually failing **before render** at lint. Once the real render ran with two workers it completed in about eight minutes. Always distinguish:

- workflow not triggered;
- setup/lint failure;
- active frame capture;
- encoding/assembly;
- post-render verification failure.

Heartbeat/status files are useful because they make those states visible without guessing.

## What "done" means

A video is production ready only when:

- audio master + word timing are final;
- QA automation passes;
- every required QA image was manually opened and accepted;
- approval matches current source/audio hashes;
- final render workflow passes;
- final MP4 media properties pass;
- representative frames from the **final MP4** were manually opened;
- final artifact manifest exists.

Anything earlier is progress, not done.
