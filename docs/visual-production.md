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
- generous clean composition.

The goal is a recognizable channel language that looks intentionally illustrated, not like a failed attempt at real photography.

Anime/cartoon directions are allowed when a job explicitly benefits from them, but **stickman is the channel default** because it is fast, readable, expressive, and consistent across abstract business/system topics.

## Hard separation: generated images vs HTML information scenes

**Do not place HTML text, exact numbers, labels, captions, counters, charts, or diagram typography on top of generated images.**

Generated-image scenes and information/typography scenes are separate visual modes.

Use an `image` scene when the job needs character, environment, emotion, metaphor, action, or a visual joke. Keep the generated image clean and let the illustration carry the beat.

When the narration needs precise information such as:

- `180 seats` / `185 tickets`;
- `$200 → $400`;
- a probability comparison;
- a legal/jurisdiction note;
- a cost-vs-cost diagram;
- a punchline rendered as text;

cut to a **separate HTML scene** with its own solid color, gradient, paper texture, grid, dots, lines, or animated background pattern. The HTML scene may use kinetic typography, counters, diagrams, arrows, icons, or controlled vector animation.

Then cut back to a generated-image scene when the narrative returns to people/environment/action.

Do not create hybrid text-over-photo/image cards as the default. A generated image may be composited with non-text atmospheric shapes/masks/transitions, but readable HTML content belongs on its own scene.

This separation should create a deliberate rhythm:

`illustration → information scene → illustration → diagram/text break → illustration`

rather than making every frame a poster.

## Shot cadence

A roughly three-minute narrated explainer should normally contain **at least 30 primary generated-image shots**, plus separate HTML information scenes where needed. A good planning target is about 10–12 generated-image shots per minute, with additional text/diagram cuts increasing total visual changes.

This is an editorial default, not a command to cut randomly. Create a new shot when the narration introduces a new semantic beat, actor/action, location/state, joke, number/comparison, reveal, cause/effect step, example, counterexample, or conclusion turn.

Typical primary image holds should land around **2.5–6 seconds**. Avoid leaving one primary image uninterrupted for more than ~7 seconds unless the stillness is deliberate.

Because HTML information scenes are separate cuts, total scene count will normally be higher than the generated-image count. A 3-minute piece with 30–36 generated images may naturally end up with 45–60 total scenes after typography/diagram breaks.

## Audio synchronization is mandatory

The **rendered narration audio is the timing source of truth**.

Do not time image cuts or information scenes from script estimates or from audio-part duration alone.

Production order:

1. Qwen renders narration.
2. The final WAV/MP3 is assembled.
3. Gemini Transcribe listens to the actual master audio and returns word-level timestamps.
4. The canonical authored transcript is matched back onto those timings.
5. Storyboard shots record a word/phrase anchor.
6. The video build resolves each anchor against `final/<job>.transcript.json`.
7. Image cuts and separate HTML information scenes fire from those resolved timings.

If the final word-level transcript is missing or materially incomplete, visual production should stop. A technically valid MP4 with visibly wrong sync is a failed build.

## HyperFrames skills are part of the production contract

Before authoring a new composition, read the current vendored HyperFrames router and relevant workflow skills under `vendor/hyperframes/skills/`.

For this channel's narrated topic videos, start with `hyperframes/SKILL.md`, `faceless-explainer/SKILL.md`, then the domain skills it routes to (`hyperframes-core`, `hyperframes-animation`, `hyperframes-audio`, `hyperframes-creative`, `hyperframes-cli`, `media-use`, and captions when needed).

The vendored set is synced from `heygen-com/hyperframes` by `.github/workflows/sync-hyperframes-skills.yml` and linked into `.agents/skills/`.

Video Factory deliberately overrides upstream media providers where documented: Qwen is narration, and the private Image Generation API is the image provider. Use HyperFrames' authoring/animation/QA grammar without silently replacing our approved providers.

## Generated-image motion: preserve the artwork

A generated image should not be sacrificed merely to create motion. **Do not default to a large Ken Burns zoom that crops meaningful stickman characters, props, or composition.**

Preferred current treatment:

1. keep the authored image fully visible as a foreground `contain` layer;
2. duplicate the same image behind it as a blurred/dimmed full-bleed backdrop;
3. animate the foreground only a few pixels with a tiny rotation/float and no scale;
4. animate the backdrop more freely because it carries no unique information;
5. optionally add non-text editorial accents (circles, lines, dots, hand-drawn marks) as deterministic motion layers.

This produces life without cutting off the illustration.

For future image generation, request **motion-safe framing**: keep important characters/props away from the outer 8–12% of the frame and leave extra environmental breathing room. If a scene specifically needs a pan, generate overscan or a wider/taller source rather than cropping the only copy of the artwork.

Suitable image-scene motion includes:

- 6–12px foreground drift;
- tiny ±0.1° editorial tilt;
- blurred backdrop drift;
- slow light/texture movement;
- line/dot accent reveals;
- paper-card parallax;
- match cuts between neighboring stickman poses;
- masked transitions between scenes.

The movement should be visible enough to prevent slideshow feeling, but never so strong that the viewer notices the effect before the idea.

## HTML text / pattern scenes are motion compositions

HTML text scenes are first-class visual beats, not static title cards and not overlays.

A text scene should normally have **three active layers**:

- a background system (grid, seat map, ticket strips, probability dots, line field, paper texture, gradient glow);
- a primary information object (number, phrase, comparison, equation);
- a secondary motion/detail layer (echo typography, rail, underline, marker dots, counters, accents).

Avoid leaving one small text block in a corner with most of the canvas doing nothing. Empty space is allowed only when it creates intentional tension or emphasis.

Typical motion grammar:

- headline reveal by mask/clip, not a generic fade;
- number or key word lands with a short scale/position impact;
- subline follows 120–350ms later;
- background pattern drifts across the full scene duration;
- rails/lines draw on;
- echo typography or geometry moves independently at low contrast;
- diagrams assemble in semantic order;
- no infinite screen-saver loops in the authoritative render.

For example, `180 SEATS` should feel like a designed infographic moment: the number owns the canvas, the seat-grid participates in the beat, `SEATS` reveals as a secondary layer, and background geometry keeps moving subtly. The next `185 TICKETS` beat can visually introduce the surplus rather than merely replacing one static number with another.

## HTML diagram scenes

Use separate diagram scenes when they clarify a system better than an illustration can, especially for flows of money/information, probability/state changes, timelines, process steps, comparisons, quantities, and ratios.

These scenes can use controlled HTML/CSS/SVG/vector animation because precision is the point. They should still feel like part of the same channel through palette, typography, spacing, and motion rhythm.

## Image-generation provider

Production image generation uses the private Image Generation API documented at `tools/image-gen/README.md`.

Live base URL:

`https://agent.wpaikits.site/v1/workflow/jobs-images`

Authentication is provided only through `IMAGE_API_TOKEN`. Never write tokens into prompts, source files, logs, issues, or documentation.

The service supports prompt-only generation, optional reference images, arbitrary supported aspect ratios, asynchronous queued jobs, and **API batches of up to 20 requests**.

The Video Factory client supports larger visual plans by automatically splitting them into multiple API batches while keeping global output numbering stable. A 36-shot plan therefore becomes a 20-image API batch plus a 16-image API batch without changing the storyboard contract.

Generated VPS files expire after 24 hours. Download required assets into production storage promptly.

## Prompting principles for this channel

Prompts should aim for a coherent stickman editorial universe rather than unrelated pretty pictures.

Every prompt should repeat enough of the channel style contract to resist drift. When relevant specify the single narrative idea, stickman actor count/pose/gesture/emotion, simplified environment/props, camera/framing/composition, channel palette/rendering, continuity requirements, no readable embedded text/logos, motion-safe breathing room, and target aspect ratio through the API field.

Do not reserve image space for HTML copy. HTML copy lives on its own scene.

Avoid asking the image model to render critical small text, exact numerical dashboards, boarding passes with readable data, or dense diagrams.

## Continuity and reference images

Reference images are encouraged when they improve continuity of recurring stickman characters, props, or visual motifs. Use only sources we own or are authorized to use.

For recurring protagonists, consider generating an early clean character/key-style frame and using it as a reference on later image requests when the API's reference behavior materially improves consistency.

## Storyboard contract

A storyboard/visual-plan entry should identify:

- `id` / ordered shot number;
- visual mode: `image`, `text`, or `diagram`;
- **anchor phrase** from the spoken script;
- generation prompt for `image` shots;
- target aspect ratio for generated images;
- HTML scene content/background/motion concept for `text`/`diagram` scenes;
- optional continuation/reference relationship to another shot.

Do not use a `composite` mode for readable HTML-on-image layouts in normal channel production.

Shot timecodes are derived after word alignment. Do not hard-code estimates in the creative plan when an anchor phrase can resolve the timing.

## Quality bar

A generated visual should be rejected or regenerated when it contradicts the narration, contains distracting anatomy/object errors even within a simple illustration style, has accidental gibberish text in focal areas, cannot support intended motion, breaks the established stickman style without reason, reads as generic AI photoreal/stock imagery, or repeats essentially the same pose/composition for too many adjacent beats.

A completed video should be rejected when narration-triggered visual events are visibly early/late, readable HTML is laid over generated imagery instead of using a separate scene, a primary image sits on screen too long without narrative reason, image changes feel arbitrary rather than beat-driven, text scenes read as mostly empty static cards, motion crops meaningful illustration content, the visual style drifts unintentionally, or important punchlines land without an intentional visual response.

The goal is polished visual storytelling with fast semantic pacing, exact narration sync, a recognizable illustrated identity, and a clear separation between illustration and information design.
