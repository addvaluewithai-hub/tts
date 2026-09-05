# Image Generation API tool

Video Factory visuals use the private image-generation API. This is independent of the legacy-named `free-image-editing` repository, which Video Factory uses for **Qwen TTS only**.

## Live service

```text
https://agent.wpaikits.site/v1/workflow/jobs-images
```

The client defaults to that URL. Override only when intentionally testing another deployment:

```bash
export IMAGE_API_BASE_URL='https://agent.wpaikits.site/v1/workflow/jobs-images'
```

Authentication:

```bash
export IMAGE_API_TOKEN='...'
```

Never commit the token. The GitHub Actions/repository secret should be named `IMAGE_API_TOKEN` when automated image generation is added to CI.

## Capabilities

The API supports:

- prompt-based image generation;
- optional reference images as base64 payloads;
- arbitrary supported aspect ratios from the service, including 16:9, 4:5, and 9:16;
- PNG or other service-supported output formats;
- queued asynchronous processing;
- batch requests of 1–20 images;
- temporary authenticated VPS hosting with automatic expiry after 24 hours.

The coordinating run uses `gpt-5.6-luna` with low reasoning and the native image-generation tool. It is intentionally isolated from Slack, Editor AI Kit, WordPress, and unrelated integrations.

Because service-hosted outputs expire, agents must download generated assets into the production workspace when they are needed beyond the current request.

## Generate one image

```bash
python tools/image-gen/client.py generate \
  --prompt "Cinematic editorial illustration of an airport gate, premium documentary look" \
  --aspect-ratio 16:9 \
  --output-format png \
  --out /tmp/gate.png
```

With one or more references:

```bash
python tools/image-gen/client.py generate \
  --prompt "Create a premium interior application using the supplied surface" \
  --aspect-ratio 4:5 \
  --ref swatch.png \
  --out /tmp/interior.png
```

The client base64-encodes reference files, submits `POST /jobs`, polls the returned `status_url`, and downloads `image.download_url` using the same bearer token.

## Generate a batch

Create `requests.json`:

```json
{
  "requests": [
    {
      "prompt": "Modern airport gate with editorial lighting",
      "aspect_ratio": "16:9",
      "references": []
    },
    {
      "prompt": "Close-up of an empty airline seat with a subtle price tag metaphor",
      "aspect_ratio": "16:9",
      "references": []
    }
  ]
}
```

Then:

```bash
python tools/image-gen/client.py batch \
  --requests requests.json \
  --out-dir /tmp/generated-scenes
```

Batch size is capped at 20 by the service and by the client.

## Production visual policy

Video Factory is **image-first** by default.

Use generated images for the majority of narrative shots, then create motion in editing through reframing, pan, zoom, parallax, overlays, compositing, and transitions. Text-only scenes with animated background patterns are useful as deliberate rhythm breaks, but should not become the dominant visual language.

Do not default to building entire scenes as HTML/CSS/vector UI when a generated image can communicate the idea more naturally and professionally. Diagrams, labels, counters, arrows, and simple charts can still be overlaid when they materially improve comprehension.

See `docs/visual-production.md` for the full policy.
