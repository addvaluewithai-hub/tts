# TTS Factory

A GitHub-native production pipeline that turns lesson transcripts into:

- short, retakeable TTS WAV parts;
- one assembled WAV + MP3 per lesson;
- word-level timing JSON for synchronized video generation;
- WebVTT captions;
- cached manifests so unchanged work does not spend model calls again.

```text
transcripts/<lesson>/*.txt
        ↓
Gemini TTS
        ↓
audio/<lesson>/*.wav
        ↓
assemble
        ↓
final/<lesson>.wav + .mp3
        ↓
per-part Gemini audio alignment
        ↓
final/<lesson>.transcript.json + .vtt
```

For autonomous/coding/video agents, **read [`AGENTS.md`](AGENTS.md)**. It is the operational input/output contract.

## Quick start

### 1. Add the API key once

Create this GitHub Actions repository secret:

```text
GEMINI_API_KEY
```

### 2. Add a lesson

Put short numbered transcript parts under one lesson folder:

```text
transcripts/introduce-yourself/
  01-intro.txt
  02-name.txt
  03-origin.txt
  04-closing.txt
```

Filename order is playback order. Short semantic parts are preferred because they make retakes, voice consistency, and word alignment more reliable.

### 3. Push to `main`

The **TTS Factory** GitHub Action runs automatically. It can also be started manually from the Actions tab.

### 4. Use the outputs

A completed lesson produces:

```text
audio/introduce-yourself/
  01-intro.wav
  01-intro.json
  01-intro.timing.json
  ...

done/introduce-yourself/
  01-intro.txt
  ...

final/
  introduce-yourself.wav
  introduce-yourself.mp3
  introduce-yourself.json
  introduce-yourself.transcript.json
  introduce-yourself.transcript.vtt
```

`final/<lesson>.transcript.json` is the primary machine handoff for downstream video generation.

## One-command factory

GitHub Actions and local agents use the same entry point:

```bash
python scripts/run_factory.py
```

It runs these stages in order:

```text
1. TTS       transcripts/ -> audio/ + done/
2. Assemble  audio/<lesson>/ -> final WAV/MP3
3. Align     short WAV parts -> timing caches + final JSON/VTT
```

For recovery/debugging, run one stage only:

```bash
python scripts/run_factory.py --stage tts
python scripts/run_factory.py --stage assemble
python scripts/run_factory.py --stage align
```

## Transcript controls

Plain text uses the defaults in `tts_config.yaml`:

```text
Welcome to the lesson.
```

Optional YAML front matter controls one part without being spoken:

```text
---
voice: Sulafat
audio_profile: A warm, patient teacher speaking directly to one learner.
scene: A quiet studio with a close microphone.
director_notes: Conversational, encouraging, and precise. Preserve the transcript exactly.
---
[gentle] Welcome to the lesson.

[clear] Today we are going to practice introducing yourself.
```

Supported per-part overrides:

- `model`
- `voice`
- `speakers`
- `audio_profile`
- `scene`
- `director_notes`
- `max_chars_per_request`

Two-speaker example:

```text
---
speakers:
  - speaker: Maya
    voice: Kore
  - speaker: Leo
    voice: Puck
scene: A clean podcast studio.
director_notes: Natural conversational turn-taking.
---
Maya: Reliability first.
Leo: Then automate the repetitive parts.
```

See `examples/` for copyable source examples.

## Video synchronization output

`final/<lesson>.transcript.json` uses schema v2 and contains:

- final lesson duration in milliseconds;
- deterministic start/end boundaries for every source audio part;
- one semantic segment per part;
- model-derived word start/end timestamps across the full lesson;
- language labels;
- model/hash metadata for caching and reproducibility.

Use `parts[].start_ms/end_ms` as hard section boundaries. Use `words[]` for subtitles, highlights, scene cues, graphics, and other fine synchronization.

Word timings are model-derived alignment, not sample-accurate phoneme/lip-sync data.

## Retakes

To replace only one part, put the revised transcript back at the same relative path:

```text
transcripts/introduce-yourself/03-origin.txt
```

The factory regenerates that changed part, replaces the canonical successful source in `done/`, rebuilds the lesson master, and re-aligns only audio whose hash changed. Unchanged timing caches are reused.

Git history remains the archive of older successful transcript versions.

## Configuration

`tts_config.yaml` is the single source of truth for synthesis, assembly, and alignment.

Current structure:

```yaml
model: gemini-3.1-flash-tts-preview
voice: Kore
max_chars_per_request: 5000
request_delay_seconds: 2

retry:
  max_attempts: 5
  initial_delay_seconds: 4
  max_delay_seconds: 60

assembly:
  gap_ms: 300
  mp3_bitrate: 192k

transcription:
  enabled: true
  models:
    - gemini-3.5-flash-lite
    - gemini-3.1-flash-lite
  attempts_per_model: 2
  initial_delay_seconds: 3
  max_delay_seconds: 20
  write_vtt: true
```

Only audio-input models belong in `transcription.models`.

## Reliability model

The factory is intentionally idempotent and recovery-friendly:

- failed TTS inputs stay in `transcripts/`;
- a transcript moves to `done/` only after its WAV is safely written;
- source/config hashes prevent unnecessary TTS regeneration;
- assembly fingerprints prevent unnecessary master rebuilds;
- per-part audio hashes preserve/reuse valid timing caches;
- timing responses are validated and can fall back across configured audio models;
- the workflow commits successfully produced factory state even if a later stage fails;
- generated commits include `[skip ci]` to avoid a second no-op workflow run.

## Local use

Requirements: Python 3.12+, `ffmpeg`, and `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="..."

python -m unittest discover -s tests -v
python scripts/run_factory.py
```

## Repository contract

- `transcripts/` — inbox; humans/agents write new source here.
- `audio/` — generated retakeable parts, TTS manifests, and timing caches.
- `done/` — latest successfully processed source transcript for each part.
- `final/` — assembled masters and downstream video-sync handoff files.
- `examples/` — tiny source-format examples only; not part of the live queue.
- `scripts/` — pipeline implementation.
- `tests/` — offline unit tests.
- `AGENTS.md` — detailed agent operating contract.

The working directories are intentionally empty in the clean repository. Generated lesson artifacts are production state, not bundled demo content.
