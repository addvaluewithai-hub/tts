# TTS Factory — Agent Contract

This repository is an operational factory, not a library demo. An agent should be able to create lesson inputs, run the pipeline, and consume the final synchronized audio without reading implementation details.

## Golden rule

Write new work only under `transcripts/`. Treat `audio/`, `done/`, and `final/` as factory-managed state.

## Input contract

A production lesson is a folder of short transcript parts:

```text
transcripts/<lesson-id>/
  01-intro.txt
  02-concept.txt
  03-example.txt
  04-closing.txt
```

Rules:

1. Use a stable, filesystem-safe lesson ID such as `introduce-yourself`.
2. Prefix parts with zero-padded numbers so lexical filename order is playback order.
3. Prefer short semantic parts over one very long file. This improves retakes, voice consistency, and timestamp alignment.
4. Use `.txt` or `.md` only.
5. Do not place generated audio or timing data in `transcripts/`.

## Transcript format

Plain text uses the global defaults from `tts_config.yaml`.

Optional YAML front matter can override TTS behavior for one part:

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

Supported per-part keys are:

- `model`
- `voice`
- `speakers` (one or two speaker mappings)
- `audio_profile`
- `scene`
- `director_notes`
- `max_chars_per_request`

Front matter is control data and must not be spoken.

## Run contract

Preferred production path: commit transcript files to `main`. GitHub Actions runs the full factory automatically.

Local/full run:

```bash
python scripts/run_factory.py
```

Recovery/debug stage only:

```bash
python scripts/run_factory.py --stage tts
python scripts/run_factory.py --stage assemble
python scripts/run_factory.py --stage align
```

The full stage order is always:

```text
1. TTS       transcripts/ -> audio/ + done/
2. Assemble  audio/<lesson>/ -> final/<lesson>.wav + .mp3
3. Align     short WAV parts -> timing caches + final transcript JSON/VTT
```

If a stage fails, the full runner stops before downstream stages. GitHub Actions still commits any successfully produced factory state for inspection/retry, then marks the run failed.

## Output contract

For each completed lesson `<lesson-id>`, expect:

```text
audio/<lesson-id>/
  01-intro.wav
  01-intro.json
  01-intro.timing.json
  ...

done/<lesson-id>/
  01-intro.txt
  ...

final/
  <lesson-id>.wav
  <lesson-id>.mp3
  <lesson-id>.json
  <lesson-id>.transcript.json
  <lesson-id>.transcript.vtt
```

Meaning:

- `audio/<lesson>/<part>.wav` — retakeable source audio part.
- `audio/<lesson>/<part>.json` — TTS generation manifest/hash.
- `audio/<lesson>/<part>.timing.json` — cached Gemini word alignment for that exact WAV.
- `done/<lesson>/<part>.*` — successfully processed source transcript used as alignment reference.
- `final/<lesson>.wav` — lossless assembled master.
- `final/<lesson>.mp3` — convenient delivery master.
- `final/<lesson>.json` — assembly manifest and exact duration.
- `final/<lesson>.transcript.json` — authoritative machine handoff for video synchronization.
- `final/<lesson>.transcript.vtt` — segment-level WebVTT captions.

## Video-agent handoff

Use `final/<lesson>.transcript.json` as the primary synchronization map. The current schema is version 2 and uses `alignment_mode: "per_part"`.

Important fields:

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

Use `parts[].start_ms/end_ms` as deterministic hard section boundaries. Use `words[]` as model-derived fine timing for captions, highlights, scene cues, and synchronized graphics.

## Retake contract

To replace one part, put a new transcript at the same relative path under `transcripts/`, for example:

```text
transcripts/introduce-yourself/03-example.txt
```

The factory should regenerate only the changed TTS part. Assembly then rebuilds the lesson master. Timing caches for unchanged WAVs are reused; the changed WAV is aligned again.

Do not manually delete unrelated timing caches to force a retake.

## Idempotency

The factory hashes source text/config, WAV parts, assembly settings, and timing configuration. Re-running unchanged work should reuse matching outputs rather than consume new model calls.

## Configuration

`tts_config.yaml` is the source of truth for:

- default TTS model and voice direction;
- chunking/retry behavior;
- silence between assembled parts and MP3 bitrate;
- timestamp-alignment router models and retry behavior.

Do not duplicate configuration values into agent code unless there is a strong reason.

## Credentials

The factory expects `GEMINI_API_KEY` (or `GOOGLE_API_KEY` locally). In GitHub Actions, use the repository secret named `GEMINI_API_KEY`.

## Definition of done

A lesson is ready for downstream video work when the final MP3/WAV and `final/<lesson>.transcript.json` exist from the same successful pipeline state. If the workflow is red, inspect the failed stage before treating newly generated output as final.
