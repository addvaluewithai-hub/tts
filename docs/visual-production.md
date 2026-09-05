# Visual production policy

## Default: image-first storytelling

Video Factory should prefer **generated images as the primary visual material** for explainer videos.

The objective is not to make static slideshows. The objective is to use strong generated frames as cinematic source material and create motion through editing.

### Recommended composition mix

Use these as editorial defaults, not hard quotas:

- roughly 70–80% generated-image-led shots;
- roughly 10–20% text-led rhythm breaks with animated background patterns;
- roughly 10% diagrams, arrows, labels, counters, charts, and other explanatory overlays.

A video may deviate when the topic genuinely benefits from more diagrams or typography.

## Generated-image shots

For each narrative beat, prefer one strong visual idea over dense explanatory layouts. Generate the asset at the final target aspect ratio whenever possible.

Common treatments after generation:

- slow push-in / pull-out;
- horizontal or vertical pan;
- crop/reframe animation;
- 2.5D/parallax separation when useful;
- foreground/background compositing;
- masked reveals;
- subtle overlays, labels, arrows, price tags, counters, or highlights;
- match cuts and visual continuity between neighboring images.

Do not assume every generated image needs constant movement. Intentional stillness can make a reveal or joke land harder.

## Text-led breaks

Text-only scenes are allowed and encouraged as rhythm changes when they improve pacing. Typical uses:

- punchlines;
- surprising numbers;
- section pivots;
- a short question before a reveal;
- simple A/B comparisons;
- one-line conclusions.

Use animated background patterns, restrained kinetic typography, and clean negative space. Avoid turning the whole video into a presentation deck.

## Diagrams and UI-style graphics

Use diagrams when they clarify a system better than an image can, especially for:

- flows of money or information;
- probability/state changes;
- timelines;
- process steps;
- comparisons;
- quantities and ratios.

However, do not default to constructing complete narrative scenes in HTML/CSS/vector UI simply because the rendering stack can do it. Generated imagery should carry the emotional and environmental context; overlays should carry precision.

## Image-generation provider

Production image generation uses the private Image Generation API documented at:

`tools/image-gen/README.md`

Live base URL:

`https://agent.wpaikits.site/v1/workflow/jobs-images`

Authentication is provided only through `IMAGE_API_TOKEN`. Never write tokens into prompts, source files, logs, issues, or documentation.

The service supports prompt-only generation, optional reference images, arbitrary supported aspect ratios, asynchronous queued jobs, and batches of up to 20 requests.

Generated VPS files expire after 24 hours. Download required assets into production storage promptly.

## Prompting principles for this channel

Prompts should aim for a coherent editorial-documentary visual language rather than unrelated pretty pictures.

Each shot prompt should specify, when relevant:

1. the single narrative idea the frame must communicate;
2. subject and environment;
3. camera/framing/composition;
4. mood and lighting;
5. visual continuity requirements from adjacent shots;
6. required empty space for later labels or typography;
7. target aspect ratio through the API field, not by asking the model to fake a crop.

Avoid asking the image model to render critical small text, exact numerical dashboards, or dense diagrams. Add those elements in post-production where they can be controlled precisely.

## References

Use reference images only when they materially improve continuity, product fidelity, subject consistency, or art direction. Reference images are sent as base64 by the client and should come from sources we own or are authorized to use.

## Storyboard contract

A storyboard entry should identify its visual mode explicitly:

- `image` — generated image is the primary scene;
- `text` — typography/pattern rhythm break;
- `diagram` — explanatory graphic is primary;
- `composite` — generated image plus substantial explanatory overlays.

For `image` and `composite` scenes, store a generation prompt and intended aspect ratio. A later automated scene generator should be able to batch these prompts through the private image API.

## Quality bar

A generated visual should be rejected or regenerated when it:

- contradicts the narration;
- contains distracting anatomy/object errors;
- has accidental gibberish text in focal areas;
- cannot support the intended crop/motion;
- breaks continuity without editorial reason;
- looks like generic stock imagery when the beat needs a specific idea;
- makes a factual diagram or number visually ambiguous.

The goal is polished visual storytelling, not maximum generation volume.
