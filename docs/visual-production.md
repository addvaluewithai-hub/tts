# Visual production policy

## Default: image-first, stickman-led storytelling

Video Factory should prefer **generated illustrations as the primary visual material** for narrated explainer videos.

For the current channel, the default visual identity is **editorial stickman illustration**, not photoreal AI imagery.

The objective is not to make a slideshow. Strong generated frames are source material; editing, timing, composition, typography, and transitions turn them into a video.

## Channel visual identity: editorial stickman

Default prompt language should describe a coherent illustrated world:

- simple expressive stick-figure adults;
- clean black or very dark ink lines;
- warm off-white / paper-like background;
- restrained navy, red, amber, or muted accent shapes;
- minimal facial features but readable emotion/body language;
- clear silhouette and gesture;
- simplified props and environments;
- editorial explainer / newspaper illustration sensibility;
- flat or lightly textured 2D rendering;
- no photoreal skin, cinematic photography, fake lens bokeh, or pseudo-stock-photo look;
- no embedded critical text or exact numbers;
- generous negative space when a controlled overlay will be added later.

The goal is a recognizable channel language that looks intentionally illustrated, not like a failed attempt at real photography.

Anime/cartoon directions are allowed when a job explicitly benefits from them, but **stickman is the channel default** because it is fast, readable, expressive, and consistent across abstract business/system topics.

## Shot cadence

A roughly three-minute narrated explainer should normally contain **at least 30 primary visual shots**. A good planning target is about 10–12 primary shots per minute.

This is an editorial default, not a command to cut randomly. Create a new shot when the narration introduces a new:

- semantic beat;
- actor/action;
- location or state;
- joke/punchline;
- number or comparison;
- reveal;
- cause/effect step;
- example;
- counterexample;
- conclusion turn.

Typical primary still holds should land around **2.5–6 seconds**. Avoid leaving one primary image uninterrupted for more than ~7 seconds unless the stillness is deliberate and supported by meaningful internal overlays/motion.

For a 3-minute script, 30 is the floor; 32–40 is often healthier when the narration is fast.

## Audio synchronization is mandatory

The **rendered narration audio is the timing source of truth**.

Do not time image cuts or punchline overlays from script estimates or from audio-part duration alone.

Production order:

1. Qwen renders narration.
2. The final WAV/MP3 is assembled.
3. HyperFrames local transcription listens back to the actual Qwen audio and creates word-level timestamps.
4. Storyboard shots record a word/phrase anchor.
5. The video build resolves each anchor against `final/<job>.transcript.json`.
6. Cuts, text reveals, counters, jokes, and diagrams fire from those resolved timings.

If the final word-level transcript is missing or materially incomplete, visual production should stop. A technically valid MP4 with visibly wrong sync is a failed build.

## HyperFrames skills are part of the production contract

Before authoring a new composition, read the current vendored HyperFrames router and relevant workflow skills under:

`vendor/hyperframes/skills/`

For this channel's narrated topic videos, start with:

- `hyperframes/SKILL.md`;
- `faceless-explainer/SKILL.md`;
- then the domain skills it routes to (`hyperframes-core`, `hyperframes-animation`, `hyperframes-audio`, `hyperframes-creative`, `hyperframes-cli`, `media-use`, and captions when needed).

The vendored set is synced from `heygen-com/hyperframes` by `.github/workflows/sync-hyperframes-skills.yml` and linked into `.agents/skills/`.

Video Factory deliberately overrides upstream media providers where documented: Qwen is narration, and the private Image Generation API is the image provider. Use HyperFrames' authoring/animation/QA grammar without silently replacing our approved providers.

## Recommended composition mix

Use these as editorial defaults, not hard quotas:

- roughly 75–85% generated-image-led illustrated shots;
- roughly 10–15% text-led rhythm breaks with animated background patterns;
- roughly 5–15% diagrams, arrows, labels, counters, charts, and explanatory overlays.

A video may deviate when the topic genuinely benefits from more diagrams or typography.

## Generated-image shots

For each narrative beat, prefer one clear visual idea over dense explanatory layouts. Generate the asset at the final target aspect ratio whenever possible.

Common treatments after generation:

- quick editorial cuts;
- slow push-in / pull-out;
- horizontal or vertical pan;
- crop/reframe animation;
- foreground/background compositing;
- masked reveals;
- subtle parallax when the illustration supports it;
- controlled labels/arrows/price tags/counters/highlights;
- match cuts between neighboring stickman poses or props;
- split-screen comparisons;
- hold-and-punch timing for jokes.

Do not assume every generated image needs constant movement. Intentional stillness can make a reveal or joke land harder, but long passive holds are not the default.

## Text-led breaks

Text-only scenes are allowed and encouraged as rhythm changes when they improve pacing. Typical uses:

- punchlines;
- surprising numbers;
- section pivots;
- a short question before a reveal;
- simple A/B comparisons;
- one-line conclusions.

Use animated background patterns, restrained kinetic typography, and clean negative space. Avoid turning the whole video into a presentation deck.

A text break still needs a word/phrase timing anchor when it corresponds to narration.

## Diagrams and UI-style graphics

Use diagrams when they clarify a system better than an illustration can, especially for:

- flows of money or information;
- probability/state changes;
- timelines;
- process steps;
- comparisons;
- quantities and ratios.

Do not default to constructing complete narrative scenes in HTML/CSS/vector UI merely because the rendering stack can do it. Generated illustrations carry the story/context; controlled overlays carry precision.

## Image-generation provider

Production image generation uses the private Image Generation API documented at:

`tools/image-gen/README.md`

Live base URL:

`https://agent.wpaikits.site/v1/workflow/jobs-images`

Authentication is provided only through `IMAGE_API_TOKEN`. Never write tokens into prompts, source files, logs, issues, or documentation.

The service supports prompt-only generation, optional reference images, arbitrary supported aspect ratios, asynchronous queued jobs, and **API batches of up to 20 requests**.

The Video Factory client supports larger visual plans by automatically splitting them into multiple API batches while keeping global output numbering stable. A 32-shot plan therefore becomes a 20-image API batch plus a 12-image API batch without changing the storyboard contract.

Generated VPS files expire after 24 hours. Download required assets into production storage promptly.

## Prompting principles for this channel

Prompts should aim for a coherent stickman editorial universe rather than unrelated pretty pictures.

Every prompt should repeat enough of the channel style contract to resist drift. When relevant specify:

1. the single narrative idea the frame must communicate;
2. stickman actor count, pose, gesture, and emotion;
3. simplified environment/props;
4. camera/framing/composition;
5. the channel palette and flat editorial rendering;
6. continuity requirements from adjacent shots;
7. required empty space for later labels/typography;
8. no readable embedded text or logos;
9. target aspect ratio through the API field, not by asking the model to fake a crop.

Avoid asking the image model to render critical small text, exact numerical dashboards, boarding passes with readable data, or dense diagrams. Add those elements in post-production where they can be controlled precisely.

## Continuity and reference images

Reference images are encouraged when they improve continuity of recurring stickman characters, props, or visual motifs. Use only sources we own or are authorized to use.

For recurring protagonists, consider generating an early clean character/key-style frame and using it as a reference on later image requests when the API's reference behavior materially improves consistency.

## Storyboard contract

A storyboard/visual-plan entry should identify:

- `id` / ordered shot number;
- visual mode: `image`, `text`, `diagram`, or `composite`;
- **anchor phrase** from the spoken script;
- generation prompt for image/composite shots;
- target aspect ratio;
- intended overlay/punchline, if any;
- optional continuation/reference relationship to another shot.

Shot timecodes are derived after word alignment. Do not hard-code estimates in the creative plan when an anchor phrase can resolve the timing.

## Quality bar

A generated visual should be rejected or regenerated when it:

- contradicts the narration;
- contains distracting anatomy/object errors even within a simple illustration style;
- has accidental gibberish text in focal areas;
- cannot support the intended crop/motion;
- breaks the established stickman style without editorial reason;
- reads as generic AI photoreal/stock imagery;
- makes a factual diagram or number visually ambiguous;
- repeats essentially the same pose/composition for too many adjacent beats.

A completed video should be rejected when:

- narration-triggered visual events are visibly early/late;
- a primary image sits on screen too long without a narrative reason;
- image changes feel arbitrary rather than beat-driven;
- the visual style drifts between photoreal, 3D, anime, and flat illustration unintentionally;
- important punchlines land without an intentional visual response.

The goal is polished visual storytelling with fast semantic pacing, exact narration sync, and a recognizable illustrated identity.
