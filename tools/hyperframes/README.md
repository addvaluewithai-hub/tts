# HyperFrames in Video Factory

HyperFrames is the deterministic composition/render layer for Video Factory.
The upstream framework also ships agent skills that encode its current authoring,
media, animation, caption, QA, preview, and render contracts.

Upstream: `https://github.com/heygen-com/hyperframes`

## Skill policy

Do not author a fresh Video Factory composition from memory.

For video work, read the vendored skill router first:

`vendor/hyperframes/skills/hyperframes/SKILL.md`

For this channel's narrated topic explainers, the primary workflow is:

`vendor/hyperframes/skills/faceless-explainer/SKILL.md`

Load domain skills as required, especially:

- `hyperframes-core`
- `hyperframes-animation`
- `hyperframes-audio`
- `hyperframes-cli`
- `hyperframes-creative`
- `media-use`
- `embedded-captions`

The official upstream guidance is authoritative when it conflicts with old local
HyperFrames habits, except where this repository deliberately overrides a
provider (Qwen narration and the private image API).

## Keeping skills current

`.github/workflows/sync-hyperframes-skills.yml` clones the current upstream
repository and vendors its complete published `skills/` tree under:

`vendor/hyperframes/skills/`

It also records the exact upstream commit in:

`vendor/hyperframes/UPSTREAM_SHA`

and links each skill into `.agents/skills/` for compatible agent loaders.

The sync runs manually, when its workflow changes, and weekly. It preserves
unrelated local agent skills.

For an interactive/local agent environment, the upstream equivalent is:

```bash
npx hyperframes skills update
npx hyperframes skills update faceless-explainer
```

## Video Factory provider overrides

HyperFrames skills describe a general media pipeline. Video Factory intentionally
uses these local provider choices:

- narration: Qwen3-TTS 0.6B on Modal (`tools/qwen-tts/`);
- narration word timing: `hyperframes transcribe` listening back to final Qwen
  WAV parts (`scripts/transcribe_final_hyperframes.py`);
- generated visuals: private Image Generation API (`tools/image-gen/`);
- visual identity for the current channel: editorial stickman illustration,
  rather than photoreal AI imagery.

Do not replace those providers just because an upstream workflow documents a
HeyGen/Kokoro/image-provider default. Borrow HyperFrames' production grammar and
technical contracts; keep Video Factory's approved providers.

## Synchronization rule

Narration audio is the timing source of truth.

The production sequence is:

1. Qwen renders the authored narration.
2. The factory assembles the actual WAV master.
3. HyperFrames local transcription derives word-level timestamps from the
   generated audio.
4. Visual shots and overlays anchor to words/phrases from that transcript.
5. HyperFrames preview/QA/render operates on the same audio and timings.

Never schedule a punchline, reveal, image cut, number, or explanatory overlay
from estimated script timing when a word anchor exists.

## Visual pacing rule

For a roughly three-minute narrated explainer, plan at least 30 primary visual
shots unless the direction explicitly calls for a slower visual language.
The goal is not arbitrary churn: each cut should correspond to a new semantic
beat, joke, reveal, comparison, or visual continuation.

A primary still should normally not carry an entire long paragraph. Use several
related stickman illustrations, controlled camera moves, and occasional text or
diagram breaks instead.
