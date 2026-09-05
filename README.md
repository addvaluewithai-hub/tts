# Video Factory

This repository is the production system for **audio-first, timing-driven, image-first videos**. The repository name is historical; TTS is one stage of the factory, not the whole product.

The factory is intentionally not course-specific. A job can describe an explainer, lesson, documentary-style piece, or another narrated video as long as its `input/<job-id>/` package gives the agent enough direction.

For autonomous agents, read [`AGENTS.md`](AGENTS.md) first, then [`docs/PRODUCTION_PLAYBOOK.md`](docs/PRODUCTION_PLAYBOOK.md) and [`docs/visual-production.md`](docs/visual-production.md). Read [`docs/SOUNDTRACK.md`](docs/SOUNDTRACK.md) whenever music/SFX are enabled.

## Production providers

### Narration

Production narration is rendered by **Qwen3-TTS 0.6B on Modal**. The deployed service lives in the separately maintained repository:

`addvaluewithai-hub/free-image-editing`

That repository name is legacy. For Video Factory it is a **TTS provider only**.

Default English channel voice: **Aiden**.

The factory calls the private Modal endpoint through `scripts/process_tts_qwen.py`. The helper client and provider notes live in [`tools/qwen-tts/`](tools/qwen-tts/).

Gemini is no longer the narration renderer. It may still be used by the separate word-alignment stage until that stage is replaced.

### Images

Production image generation uses the private Image Generation API:

```text
https://agent.wpaikits.site/v1/workflow/jobs-images
```

It supports prompt generation, optional reference images, arbitrary supported aspect ratios, asynchronous queued jobs, and batches of up to 20 requests. Generated VPS files expire after 24 hours, so production assets should be downloaded when needed.

The helper client and full contract live in [`tools/image-gen/`](tools/image-gen/).

## The one-folder input contract

Humans and agents add new work only under:

```text
input/<job-id>/
```

Minimum package:

```text
input/my-video/
  job.yaml
  direction.md
  transcript/
    01-intro.txt
    02-example.txt
    03-closing.txt
```

Optional job-specific material can live beside it:

```text
  pronunciation-map.json
  assets/
  music/
  sfx/
  references/
  data/
```

Several input folders may exist. **`input/ACTIVE` selects the one production the factory is allowed to advance right now.** We deliberately do one video at a time until multi-job scheduling is worth the extra complexity.

See [`input/README.md`](input/README.md) and copy [`input/_template/`](input/_template/).

## Pipeline

```text
input/<job-id>/
        ↓
ingest active input
        ↓
Qwen3-TTS 0.6B narration on Modal
        ↓
assembled dry WAV + MP3
        ↓
word-level audio alignment
        ↓
optional music + licensed SFX soundtrack mix
        ↓
final/<job-id>.transcript.json + dry/mixed program audio
        ↓
image-first storyboard + generated visual assets
        ↓
video source authored from images + direction + exact timing
        ↓
HyperFrames QA render
        ↓
manual full-resolution visual review
        ↓
hash-bound approval
        ↓
final render + ffprobe + final-frame review
        ↓
GitHub Actions final artifact
```

## Directory contract

```text
input/                     human/agent source packages + ACTIVE pointer
transcripts/               internal TTS queue materialized from active input
audio/                     retakeable generated TTS parts + timing caches
done/                      successful TTS source state
final/                     dry audio, timing, optional music/mix + manifests
productions/<job-id>/video agent-authored deterministic video source
tools/                     provider clients and durable integration docs
.factory-status/            machine-readable audio/video workflow state
approvals/                  manual visual approval bound to source/audio hashes
scripts/                    factory implementation
tests/                      offline unit tests
docs/                       durable production knowledge
```

`input/` is source. The other production directories are factory/agent-managed state.

## Audio stage

```bash
python scripts/ingest_input.py
python scripts/run_factory.py
```

`run_factory.py` performs:

```text
1. TTS         transcripts/ -> audio/ + done/ via Qwen Modal
2. Assemble    audio/<job>/ -> final/<job>.wav + .mp3
3. Align       short WAV parts -> final transcript JSON/VTT
4. Soundtrack  optional music + licensed SFX -> final/<job>.mix.wav/.mp3
```

The primary synchronization handoff remains:

```text
final/<job-id>.transcript.json
```

Current alignment schema is v2 and contains duration, part boundaries, segments, and model-derived word timestamps. The dry narration stays authoritative for timing; adding/changing soundtrack content does not rewrite word timing or require a TTS retake.

When soundtrack is enabled, video QA and final render prefer:

```text
final/<job-id>.mix.wav
```

Otherwise they use `final/<job-id>.wav`.

## Audio authoring rules

- Prefer several short numbered transcript parts rather than one long TTS request.
- Audio parts are retry/retake boundaries; **they do not define video scene count**.
- Qwen's service request cap is 2400 characters; the factory targets 2200 for headroom.
- The production preset voice is **Aiden / English** unless a job intentionally overrides it.
- Qwen3-TTS 0.6B CustomVoice does not provide reliable free-form style instruction. Put personality into the writing, punctuation, pauses, sentence length, and chunking.
- Renderer-only bracket cues and XML-like tags are stripped before Qwen synthesis so they are not spoken aloud.
- `Speaker 1:`-style labels are silent role markers, not spoken copy; omit them in new single-speaker jobs.
- On provider rate limits, preserve successful work and retry infrastructure; do not rewrite narration to solve quota/transport failures.
- Voice cloning is available through the same Modal stack, but references must be owned/authorized and high-fidelity cloning should include the exact reference transcript.
- Soundtrack remains opt-in and independent of the narration provider.

See [`tools/qwen-tts/README.md`](tools/qwen-tts/README.md) for the TTS provider contract.

## Image-first visual authoring

The default visual strategy is **generated-image-led storytelling**, not building every narrative scene from HTML/CSS/vector UI.

As a practical editorial target:

- ~70–80% generated-image-led shots;
- ~10–20% text-led rhythm breaks with animated background patterns;
- ~10% diagrams, labels, counters, arrows, charts, and explanatory overlays.

These are defaults, not quotas. Use diagrams more heavily when the subject needs precision.

Generated images should become moving shots through pan, zoom, reframing, parallax, compositing, masks, and transitions. Text-only scenes are useful for punchlines, numbers, section pivots, and short questions. Avoid turning the whole video into a slide deck.

Do not ask the image model to render critical small text or exact dense diagrams. Generate the environmental/emotional frame, then add precise typography and data overlays in post.

See [`docs/visual-production.md`](docs/visual-production.md) and [`tools/image-gen/README.md`](tools/image-gen/README.md).

## Video source contract

Each authored production lives under:

```text
productions/<job-id>/video/
```

The visual design can vary per job, but the production must build deterministically from the final audio/timing and emit:

```text
index.html
build-meta.json
```

`build-meta.json` provides scene boundaries plus authoritative `finalHolds[]` and `riskBeats[]` for QA.

## Visual QA contract

Automated checks are gates, not approval. A reviewer/agent must actually open every full-resolution scene final, every risk beat, and every full-duration progression strip before creating approval.

Important hard-won rules are recorded in [`docs/PRODUCTION_PLAYBOOK.md`](docs/PRODUCTION_PLAYBOOK.md), including:

- one HyperFrames root `.html` composition;
- editable templates use `.tpl`, not a second `.html` root;
- timed scenes use `class="clip"` and stable IDs;
- audio elements have stable IDs;
- `set -o pipefail` when lint/validate output is piped to `tee`;
- `ffmpeg -nostdin` in review loops;
- progression strips sample the whole scene;
- approval is invalidated when source SHA or transcript hash changes.

## Final definition of done

A video is production-ready only when all of these are true:

1. dry master audio and `final/<job>.transcript.json` exist from a successful audio state;
2. optional soundtrack, when enabled, has a current soundtrack manifest and mix;
3. intended generated image assets are downloaded into production storage and visually reviewed;
4. authoritative video QA automation passes using the intended program audio;
5. required QA images were manually opened and accepted;
6. approval matches current source SHA and transcript SHA-256;
7. final render passes;
8. MP4 is non-empty and matches requested resolution/fps;
9. MP4 duration matches the audio master within the production tolerance;
10. representative frames extracted from the **final MP4** were manually opened;
11. final artifact manifest exists.

## Credentials and configuration

GitHub Actions narration requires:

```text
Repository variable:
QWEN_TTS_API_URL

Repository secrets:
MODAL_PROXY_TOKEN_ID
MODAL_PROXY_TOKEN_SECRET
```

The current alignment stage also requires:

```text
GEMINI_API_KEY
```

Image generation requires:

```text
IMAGE_API_TOKEN
```

The image client defaults to the production base URL. `IMAGE_API_BASE_URL` is an optional override for testing another deployment.

Never commit credential values.

Local work requires Python 3.12+ and FFmpeg:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/ingest_input.py
python scripts/run_factory.py
```
