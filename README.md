# TTS Factory

A GitHub-native audio production pipeline for turning lesson transcripts into retakeable TTS parts, one final lesson master, and a machine-readable word timeline for synchronized video generation.

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
per-part Gemini word alignment
        ↓
final/<lesson>.transcript.json + .vtt
```

The pipeline is designed to be idempotent: unchanged source/config/audio reuses existing manifests and timing caches instead of spending model calls again.

For automation agents, read [`AGENTS.md`](AGENTS.md). It is the operational input/output contract.

## Quick start

### 1. Add the API key once

In this repository, create the GitHub Actions secret:

```text
GEMINI_API_KEY
```

### 2. Add a lesson

Create short numbered transcript parts under one lesson folder:

```text
transcripts/introduce-yourself/
  01-intro.txt
  02-name.txt
  03-origin.txt
  04-closing.txt
```

Filename order is playback order. Short semantic parts are preferred because they make retakes, voice consistency, and timestamp alignment more reliable.

### 3. Push to `main`

The **TTS Factory** GitHub Action runs automatically. You can also run it manually from the Actions tab.

### 4. Consume the outputs

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

The individual WAVs are kept for selective retakes. `final/<lesson>.transcript.json` is the primary machine handoff for a video agent.

## What each stage does

### 1. TTS

`scripts/process_tts.py`

- discovers `.txt`/`.md` files recursively under `transcripts/`;
- applies global defaults from `tts_config.yaml` plus optional per-file YAML front matter;
- generates 24 kHz mono PCM WAV audio;
- retries retryable model/API failures;
- writes a hash manifest beside every WAV;
- moves a source transcript to `done/` only after its WAV is safely written;
- leaves failed inputs in `transcripts/` for retry.

### 2. Lesson assembly

`scripts/assemble_lessons.py`

- treats each `audio/<lesson>/` folder as one lesson;
- sorts WAV parts by filename;
- validates compatible WAV formats;
- inserts the configured gap between parts;
- writes a lossless final WAV and delivery MP3;
- writes an assembly manifest with exact duration and component order;
- skips rebuilding an unchanged lesson.

### 3. Video-sync alignment

`scripts/transcribe_final.py` + `scripts/transcription_core.py`

- aligns each short source WAV independently with an audio-capable Gemini model;
- uses the successful source in `done/` as a spelling/order reference while treating audio as authoritative;
- rejects obviously incomplete/grouped word timing responses;
- caches each part as `audio/<lesson>/<part>.timing.json`;
- offsets part-relative timings into the final lesson timeline;
- writes schema-v2 JSON plus WebVTT;
- reuses unchanged timing caches during retakes.

## Transcript controls

Plain text uses global defaults:

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

```text
model
voice
speakers
 audio_profile
scene
director_notes
max_chars_per_request
```

For two speakers:

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

See `examples/` for small copyable examples.

## Video handoff

`final/<lesson>.transcript.json` is the authoritative synchronization file for downstream video generation. Current files use:

```json
{
  "schema_version": 2,
  "alignment_mode": "per_part",
  "duration_ms": 123456,
  "parts": [
    {
      "file": "01-intro.wav",
      "start_ms": 0,
      "end_ms": 18000,
      "model": "gemini-3.1-flash-lite",
      "word_count": 42
    }
  ],
  "segments": [
    {
      "start_ms": 0,
      "end_ms": 18000,
      "speaker": "teacher",
      "language": "ar-en",
      "text": "..."
    }
  ],
  "words": [
    {
      "start_ms": 640,
      "end_ms": 920,
      "text": "Hello",
      "language": "en",
      "segment_index": 0
    }
  ]
}
```

`parts[].start_ms/end_ms` are deterministic boundaries derived from the actual WAV lengths and assembly gap. `words[]` is model-derived fine alignment for subtitles, highlights, scene cues, and synchronized graphics.

## Retakes

To replace only one section, put the revised transcript back at the same relative path:

```text
transcripts/introduce-yourself/03-origin.txt
```

The source/config hash forces that part to regenerate. Assembly rebuilds the final master. Unchanged `.timing.json` caches are reused, so only changed audio needs alignment again.

## Configuration

`tts_config.yaml` is the single source of truth. The current defaults are:

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

Run only one recovery/debug stage when needed:

```bash
python scripts/run_factory.py --stage tts
python scripts/run_factory.py --stage assemble
python scripts/run_factory.py --stage align
```

## Repository contract

- `transcripts/` — inbox; humans/agents write new source here.
- `audio/` — generated retakeable parts, TTS manifests, and timing caches.
- `done/` — successfully processed source transcripts.
- `final/` — assembled lesson masters and video-sync handoff files.
- `examples/` — tiny source-format examples only; not part of the live queue.
- `scripts/` — pipeline implementation.
- `tests/` — offline unit tests.

The GitHub Action commits only factory-managed state (`audio`, `done`, `transcripts`, `final`) and marks generated commits with `[skip ci]` to avoid a second no-op run caused by moving inputs out of the inbox.
