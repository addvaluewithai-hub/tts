# Video Factory tools

Durable provider integrations live here so an agent can discover how external production services are called without relying on chat history.

## `qwen-tts/`

Private Qwen3-TTS 0.6B service on Modal.

- Production narration provider
- Default voice: Aiden / English
- Modal app source: `addvaluewithai-hub/free-image-editing` (legacy repo name; TTS only for Video Factory)
- Auth: `QWEN_TTS_API_URL`, `MODAL_PROXY_TOKEN_ID`, `MODAL_PROXY_TOKEN_SECRET`

## `image-gen/`

Private image-generation API.

- Live base URL: `https://agent.wpaikits.site/v1/workflow/jobs-images`
- Prompt generation + optional reference images
- Batch size: 1–20
- Async queued processing
- Auth: `IMAGE_API_TOKEN`
- Temporary output hosting: 24 hours

The image service is independent of `free-image-editing`. Do not conflate the two providers.
