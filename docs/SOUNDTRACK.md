# Soundtrack stage

The factory keeps **speech timing** and **program audio** separate.

The dry narration remains the authoritative timing master:

```text
final/<job>.wav
final/<job>.transcript.json
```

After word alignment succeeds, the optional soundtrack stage may add music and SFX and produce:

```text
final/<job>.music.mp3
final/<job>.music.json
final/<job>.mix.wav
final/<job>.mix.mp3
final/<job>.soundtrack.json
```

Video QA and final render prefer `final/<job>.mix.wav` when it exists; otherwise they use the dry master. This lets music/SFX change without invalidating word timing or forcing a TTS retake.

## Safety and cost rules

- Soundtrack is opt-in: `soundtrack.enabled: false` by default.
- Lyria is never called unless both soundtrack and music are explicitly enabled.
- Generated music is cached by model + prompt fingerprint. A retry of unrelated factory work must reuse the same music file instead of making another paid generation request.
- The Lyria API is a paid service; check the current Gemini API pricing before enabling it for a production.
- Keep narration intelligible. Background music should be quiet and duck under speech.
- Default to instrumental-only background beds for teaching/explainer videos unless the creative direction explicitly asks for vocals.

## Lyria

Current supported model IDs:

```text
lyria-3-clip-preview
lyria-3-pro-preview
```

The factory uses the Gemini Interactions API through `google-genai`.

Typical job config:

```yaml
soundtrack:
  enabled: true

  music:
    enabled: true
    source: lyria
    model: lyria-3-clip-preview
    instrumental: true
    prompt: >-
      Warm modern educational background music, soft keys, light percussion,
      optimistic but restrained, lots of space for spoken narration.
    gain_db: -28
    fade_in_seconds: 0.6
    fade_out_seconds: 1.2
    duck_threshold: 0.025
    duck_ratio: 8
    duck_attack_ms: 20
    duck_release_ms: 300
```

Use Clip for short loopable beds and Pro when the production truly needs a longer composed piece. The mixer can loop a short bed to the exact narration duration.

To avoid a generation call entirely, use a job-local music file **only when its license permits storing the raw asset in this public repository**:

```yaml
music:
  enabled: true
  source: file
  file: music/bed.mp3
  gain_db: -28
```

## SFX sourcing policy

This factory repository is public. A license that permits using a stock sound **inside a finished video** does not automatically permit redistributing the raw sound file in a public Git repository.

For raw SFX committed under `input/<job>/sfx/`, prefer licenses that clearly permit redistribution:

1. **Kenney audio packs** — preferred starter source. Kenney game assets are CC0; Interface Sounds, UI Audio, Impact Sounds and related audio packs are suitable for common clicks, confirmations, transitions and impacts.
2. **Freesound CC0** — strong secondary source. Verify the exact file is CC0 before committing it. CC BY can be used only when redistribution is allowed and the required attribution is preserved.
3. **Other CC0/public-domain libraries** — acceptable when the exact asset page/license is recorded.

**Mixkit and Pixabay remain useful end-product stock libraries**, but do not commit their raw stock files to this public repository unless the exact applicable license explicitly permits that redistribution. Their normal stock licenses are intended for use in projects and include restrictions around standalone/raw redistribution.

Do not hot-link, scrape, or mass-download SFX libraries at render time. Curate each sound intentionally and preserve its license trail.

Job layout:

```text
input/<job>/
  sfx/
    manifest.yaml
    soft-whoosh.wav
    click.wav
```

Every used file must have a manifest entry:

```yaml
files:
  soft-whoosh.wav:
    source_url: https://original-source-page.example/sound
    license: Creative Commons CC0
    redistribution: true
    attribution: ""
```

`redistribution: true` is an explicit production assertion that the exact license allows the raw asset to be stored/distributed from this public repo. The soundtrack stage refuses used SFX without it. Do not set it to true merely to pass validation.

The lower-level mixer also requires `source_url` and `license`. If a redistributable license requires attribution, populate `attribution` and preserve it in downstream credits.

## SFX timing

SFX events support four timing modes:

```yaml
soundtrack:
  enabled: true
  sfx:
    enabled: true
    gain_db: -8
    events:
      - file: soft-whoosh.wav
        anchor_text: "Tell me about yourself"
        offset_ms: -150

      - file: click.wav
        part: 3
        offset_ms: 300

      - file: click.wav
        at_seconds: 12.5
```

For cues tied to spoken words, prefer `anchor_text` over absolute seconds. Anchors resolve against the authoritative `words[]` timing in `final/<job>.transcript.json`, so they move with a TTS retake.

Available timing keys:

- `anchor_text` — phrase matched against timed words; optional `occurrence` and `offset_ms`.
- `part` — 1-based part number or exact part filename; optional `offset_ms`.
- `at_ms` — absolute milliseconds.
- `at_seconds` — absolute seconds.

## Mix behavior

The program mix is produced with FFmpeg:

- narration is the duration master;
- music loops if necessary and is trimmed to narration duration;
- configurable fades are applied;
- music is side-chain compressed under narration;
- SFX are delayed to their resolved timestamps;
- a limiter protects the final bus;
- output is stereo 48 kHz WAV plus 192 kbps MP3.

`final/<job>.soundtrack.json` records the dry-audio hash, soundtrack config fingerprint, generated/local music metadata, every SFX file hash, source URL, license, resolved cue time, and final mix hashes.
