# Gemini 3.1 Flash TTS batch pipeline

Drop transcript files into `transcripts/`. GitHub Actions converts them to WAV audio with Google's `gemini-3.1-flash-tts-preview`, writes the results to `audio/`, and moves successfully processed transcript files to `done/`.

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
        | GitHub Actions + Gemini TTS
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

final/
  lesson-01.wav
  lesson-01.mp3
  lesson-01.json

done/
  lesson-01/
    01-intro.txt
    02-explanation.txt
    03-examples.txt
    04-closing.txt
```

The small WAV files remain available so one bad section can be regenerated without rebuilding the whole lesson. After TTS succeeds, `scripts/assemble_lessons.py` sorts the WAV parts by filename and creates one final lossless WAV plus one MP3 for each lesson folder.

The JSON beside each small WAV is a generation manifest containing the source hash, effective voice configuration, model, chunk count, and audio format. The JSON beside the final lesson records the ordered component files, assembly hash, gap, duration, and MP3 settings. These manifests make safe reruns idempotent.

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

All 30 documented voices are supported. A few starting points:

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

Gemini 3.1 Flash TTS supports up to two speakers. Their names in the metadata must match the names in the spoken transcript.

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

Edit `tts_config.yaml` to change defaults for every transcript and lesson assembly:

```yaml
model: gemini-3.1-flash-tts-preview
voice: Kore
audio_profile: A natural, trustworthy narrator.
scene: A clean, quiet recording studio.
director_notes: Speak naturally and conversationally.
max_chars_per_request: 5000
request_delay_seconds: 2
retry:
  max_attempts: 5
  initial_delay_seconds: 4
  max_delay_seconds: 60
assembly:
  gap_ms: 300
  mp3_bitrate: 192k
```

`assembly.gap_ms` controls the silence inserted between small lesson files. `assembly.mp3_bitrate` controls the final MP3 quality. The lossless WAV master is always kept as well.

Per-transcript front matter overrides the global `model`, `voice`, `audio_profile`, `scene`, `director_notes`, and `max_chars_per_request` values.

## Reliability behavior

The processor intentionally runs requests sequentially. It retries `429` and `5xx` API errors with exponential backoff and jitter. A transcript is moved to `done/` only after its WAV and manifest are safely written.

Long transcript files can also be split internally near paragraph/sentence boundaries. Each internal chunk is generated separately as 24 kHz, mono, 16-bit PCM and stitched into that part's WAV file.

Final lesson assembly happens only after the TTS processing step succeeds. The assembler validates that every component WAV uses the same channel count, sample width, and sample rate before joining them. It keeps the small files and produces `final/<lesson>.wav`, `final/<lesson>.mp3`, and a final manifest.

If one transcript fails after all retries, the workflow continues processing the remaining files. Successful outputs are committed, the failed transcript remains in `transcripts/`, and the workflow ends in a failed state so the problem is visible. It does not publish an incomplete newly assembled lesson master from that failed batch.

## Local use

Validate transcript parsing/chunking without making Gemini requests:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/process_tts.py --dry-run
```

Generate TTS locally:

```bash
export GEMINI_API_KEY="..."
python scripts/process_tts.py
```

Assemble existing lesson WAV parts locally (requires `ffmpeg` for MP3 output):

```bash
python scripts/assemble_lessons.py
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Notes on quota

Gemini rate limits are project-level and can include RPM, token, and daily request limits. Your exact active limits should be checked in Google AI Studio. Because transcript chunking can use more than one request per file, the number of API requests can be higher than the number of transcript files. Final WAV/MP3 assembly is local processing and uses no Gemini requests.
