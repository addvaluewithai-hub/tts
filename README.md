# Video Factory

This repository is the production system for **audio-first, timing-driven videos**. The repository name is historical; TTS is now one stage of the factory, not the whole product.

The factory is intentionally not English-course-specific. A job can describe an English lesson, another course, an explainer, or another narrated video as long as its `input/<job-id>/` package gives the agent enough direction.

For autonomous agents, read [`AGENTS.md`](AGENTS.md) first, then [`docs/PRODUCTION_PLAYBOOK.md`](docs/PRODUCTION_PLAYBOOK.md), and [`docs/SOUNDTRACK.md`](docs/SOUNDTRACK.md) when music/SFX are enabled.

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
Gemini TTS short parts
        ↓
assembled dry WAV + MP3
        ↓
word-level audio alignment
        ↓
optional Lyria music + licensed SFX soundtrack mix
        ↓
final/<job-id>.transcript.json + dry/mixed program audio
        ↓
video source authored from direction + exact timing
        ↓
HyperFrames QA render
        ↓
manual full-resolution visual review
        ↓
hash-bound approval
        ↓
final 1080p/30fps render + ffprobe + final-frame review
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
1. TTS         transcripts/ -> audio/ + done/
2. Assemble    audio/<job>/ -> final/<job>.wav + .mp3
3. Align       short WAV parts -> final transcript JSON/VTT
4. Soundtrack  optional Lyria/local music + licensed SFX -> final/<job>.mix.wav/.mp3
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
- Do not add per-part `max_chars_per_request` during normal production. The global maximum in `tts_config.yaml` is only a safety net.
- For one speaker, use `voice:`. Use `speakers:` only for genuine multi-speaker synthesis.
- Protect authored pronunciation/performance markup (`[WARM]`, `<lang>`, `<phoneme>`, IPA) unless intentionally revising the source.
- `Speaker 1:`-style labels are silent role markers, not spoken copy; omit them in new single-speaker jobs.
- On Gemini 429, preserve successful work, wait 60 seconds, and retry remaining work in the same workflow run rather than changing the lesson text.
- Soundtrack is opt-in and Lyria generation is cached; do not make repeated paid music calls for unrelated retries.
- Every production SFX file must have a traceable source URL and license in the job's `sfx/manifest.yaml`.

See [`docs/SOUNDTRACK.md`](docs/SOUNDTRACK.md) for the Lyria/SFX contract and sourcing policy.

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

The approved Lesson 01 V4 production is kept in this repository as the reference implementation. It demonstrates audio-driven word cues, Arabic/English layout, deterministic GSAP timing, contained Lottie, manual visual QA, and final-render verification.

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
- Lottie registers one real AnimationItem and must be visibly reviewed;
- approval is invalidated when source SHA or transcript hash changes.

## Final definition of done

A video is production-ready only when all of these are true:

1. dry master audio and `final/<job>.transcript.json` exist from a successful audio state;
2. optional soundtrack, when enabled, has a current `final/<job>.soundtrack.json` and mix;
3. authoritative video QA automation passes using the intended program audio;
4. required QA images were manually opened and accepted;
5. approval matches current source SHA and transcript SHA-256;
6. final render passes;
7. MP4 is non-empty and matches requested resolution/fps;
8. MP4 duration is within 0.15s of the audio master;
9. representative frames extracted from the **final MP4** were manually opened;
10. final artifact manifest exists.

## Credentials

GitHub Actions requires the repository secret:

```text
GEMINI_API_KEY
```

Lyria is a paid Gemini API feature and is disabled by default. Check current Google pricing before opting a job into generated music.

Local audio work requires Python 3.12+, FFmpeg, and `GEMINI_API_KEY` (or `GOOGLE_API_KEY` for non-workflow local use where supported).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/ingest_input.py
python scripts/run_factory.py
```
