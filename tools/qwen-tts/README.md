# Qwen TTS tool

Video Factory narration is rendered by the private **Qwen3-TTS 0.6B** service deployed on Modal from:

`addvaluewithai-hub/free-image-editing`

The repository name is legacy. For Video Factory, that repository is a **TTS provider only**. Do not route image-generation work to it.

## Production defaults

- Provider: Qwen3-TTS 0.6B on Modal
- Preset model: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- Default English channel voice: **Aiden**
- Language: English
- Per-request service limit: 2400 characters
- Production factory chunk target: 2200 characters

Aiden is the default because the channel needs a clear, modern, friendly narrator rather than an aggressive commercial read. Ryan remains available for experiments. The 0.6B CustomVoice checkpoint does not provide reliable free-form style instruction, so delivery personality should primarily come from authored wording, punctuation, pauses, sentence length, and chunking.

## Authentication

The Modal API is private and requires proxy authentication.

Set:

```bash
export QWEN_TTS_API_URL='https://YOUR-ENDPOINT.modal.run'
export MODAL_PROXY_TOKEN_ID='wk-...'
export MODAL_PROXY_TOKEN_SECRET='ws-...'
```

Never commit these values.

## Preset voice

```bash
python tools/qwen-tts/client.py tts \
  "Your plane has 180 seats. The airline sells 185 tickets." \
  --speaker Aiden \
  --language English \
  --out /tmp/narration.wav
```

## Voice clone

The same Modal deployment also exposes Qwen3-TTS 0.6B Base for voice cloning. Use only a reference recording we own or are authorized to use.

```bash
python tools/qwen-tts/client.py clone reference.wav \
  "This is the target narration." \
  --reference-text "This is the exact reference transcript." \
  --language English \
  --out /tmp/cloned.wav
```

High-fidelity cloning should include the exact reference transcript. `--x-vector-only` is a fallback when the reference transcript is unavailable.

## Factory integration

The production audio stage uses `scripts/process_tts_qwen.py`, not this CLI wrapper. The wrapper exists for manual tests and agents.

`tts_config.yaml` is the source of truth for the default speaker and chunking. The GitHub Actions audio workflow reads the Modal URL from the repository variable `QWEN_TTS_API_URL` and credentials from Actions secrets.

Gemini may still be used by the separate word-alignment stage. It is **not** the narration renderer.
