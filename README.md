# Gemini 3.1 Flash TTS batch pipeline

Drop transcript files into `transcripts/`. GitHub Actions converts them to WAV audio with Google's `gemini-3.1-flash-tts-preview`, writes the results to `audio/`, moves successfully processed transcript files to `done/`, assembles each lesson, then creates a timestamped transcript for video synchronization.

The pipeline is designed for batch work: add 1 file or 10 files, push once, and let the workflow process them sequentially.

## Repository flow

For production lessons, put the small transcript parts inside one lesson folder and number them in playback order:

```text
transcripts/
  lesson-01/
    01-intro.txt
    02-explanation.txt
    03-examples.txt
    04-closing.txt
        |
        | Gemini TTS
        v
audio/
  lesson-01/
    01-intro.wav
    01-intro.json
    02-explanation.wav
    02-explanation.json
    03-examples.wav
    03-examples.json
    04-closing.wav
    04-closing.json
        |
        | local assembly + Gemini audio understanding
        v
final/
  lesson-01.wav
  lesson-01.mp3
  lesson-01.json
  lesson-01.transcript.json
  lesson-01.transcript.vtt

done/
  lesson-01/
    01-intro.txt
    02-explanation.txt
    03-examples.txt
    04-closing.txt
```

The small WAV files remain available so one bad section can be regenerated without rebuilding the whole lesson. `scripts/assemble_lessons.py` sorts them by filename and creates the final WAV/MP3. `scripts/transcribe_final.py` then sends the final MP3 to Gemini audio understanding and creates the video-sync timing files.

## Video-sync transcript

`final/<lesson>.transcript.json` is the machine-readable handoff for the video agent. It includes:

- final audio duration in milliseconds;
- exact start/end boundaries for every numbered source audio part, calculated locally from the WAV files;
- semantic transcript segments with start/end timestamps, speaker, language, and text;
- best-effort word-level start/end timestamps with Arabic/English language labels;
- the Gemini model that produced the timing alignment;
- hashes so unchanged lessons are not transcribed again.

`final/<lesson>.transcript.vtt` contains the same semantic segments in standard WebVTT form for players/editors.

The source transcript in `done/<lesson>/` is supplied to Gemini as a spelling/alignment reference after silent YAML, SSML/IPA markup, and performance tags are removed. The final audio remains authoritative.

## Transcription model router

The router uses only models that accept audio input:

```yaml
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

Lessons rotate between the configured models to spread daily usage. If the selected model is rate-limited or has a service/model failure, the router retries/falls back to the other model. The hosted `gemma-4-26b-a4b-it` and `gemma-4-31b-it` models are intentionally not in this router because those Gemma 4 sizes do not accept audio input. Embedding models are also irrelevant to this stage.

## One-time setup

1. In Google AI Studio, create/copy your Gemini API key.
2. In this GitHub repo, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Create a secret named exactly `GEMINI_API_KEY`.
4. Add `.txt` or `.md` files under `transcripts/` and push them to `main`.

The workflow also supports **Actions → Generate TTS audio → Run workflow** for a manual run.

## Simplest transcript

A plain text file works with the defaults from `tts_config.yaml`:

```text
Hello. This is my transcript, and Gemini should speak exactly this text.
```

## Control personality, emotion, pace, and voice

Each transcript can start with optional YAML front matter. The metadata is removed before speech generation, so it is not spoken aloud.

```text
---
voice: Sulafat
audio_profile: A warm, thoughtful founder speaking directly to one listener.
scene: A quiet, premium podcast studio. Close microphone.
director_notes: Speak with calm confidence. Use natural pauses. Slow down on important ideas.
---
[serious] Here is the part most people miss.

[curious] What would happen if we designed the workflow before choosing the tool?

[excited] That is where the leverage starts.
```

Gemini TTS supports expressive inline audio tags such as `[excited]`, `[whispers]`, `[laughs]`, `[serious]`, `[tired]`, `[shouting]`, and many more. You can also use free-form tags experimentally.

### Useful built-in voices

All documented TTS voices are supported. A few starting points:

- `Kore` — firm
- `Puck` — upbeat
- `Sulafat` — warm
- `Achird` — friendly
- `Charon` — informative
- `Gacrux` — mature
- `Enceladus` — breathy
- `Iapetus` — clear
- `Schedar` — even
- `Zephyr` — bright

## Multi-speaker transcript

Gemini TTS supports up to two speakers. Their names in the metadata must match the names in the spoken transcript.

```text
---
speakers:
  - speaker: Maya
    voice: Kore
  - speaker: Leo
    voice: Puck
audio_profile: Two friendly AI podcast hosts.
scene: A modern podcast studio.
director_notes: Maya is composed. Leo is energetic and curious.
---
Maya: We need reliability before cleverness.
Leo: [excited] Exactly. Make it boringly dependable first.
```

See `examples/` for ready-to-copy files.

## Global configuration

Edit `tts_config.yaml` to change defaults for TTS, lesson assembly, and final transcription:

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
  write_vtt: true
```

`assembly.gap_ms` controls silence between small lesson files. The lossless WAV master is always kept. Per-transcript front matter overrides the global TTS model/voice/profile/scene/director notes/chunk size.

## Reliability behavior

TTS requests run sequentially and retry `429`/`5xx` errors with exponential backoff. A source transcript moves to `done/` only after its WAV and manifest are safely written.

Final lesson assembly validates WAV format consistency before joining files. Final transcription is hash-based and idempotent: unchanged MP3s with the same router configuration do not spend another API request. Uploaded Gemini Files API copies are deleted after each transcription attempt.

The workflow commits successful outputs even if a later pipeline stage fails, then ends failed so the problem remains visible and can be retried without losing completed work.

## Local use

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="..."

python scripts/process_tts.py
python scripts/assemble_lessons.py
python scripts/transcribe_final.py
python -m unittest discover -s tests -v
```

## Notes on quota

Final WAV/MP3 assembly is local and uses no Gemini requests. Final timestamping uses one audio-understanding request per lesson in the normal case. The router spreads lessons across the configured audio-capable Flash-Lite models and only consumes fallback calls when a primary attempt fails.
