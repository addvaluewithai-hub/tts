# Introduce Yourself — reference production

This is the canonical approved Lesson 01 V4 source migrated from `addvaluewithai-hub/videos`.

Why it stays here:

- it is a known-good audio-first HyperFrames production;
- it uses exact word timing from `final/introduce-yourself.transcript.json`;
- it demonstrates deterministic GSAP motion, Arabic/English bidi, and contained Lottie;
- it was manually reviewed at full resolution before final render;
- the final 1920×1080 / 30fps MP4 matched the 244.08s audio master within 0.02s.

Use it as a **reference for factory mechanics, not a visual template that every future video must copy**.

Important historical fixes already incorporated here:

- source template is `.tpl`, so HyperFrames sees only one root `.html` after build;
- all timed scenes use stable IDs and `class="clip"`;
- the audio element has a stable ID;
- Lottie registers one real AnimationItem and uses scene-local seeking;
- risk beats are clamped after visible reveal time;
- progression strips are expected to cover the whole scene;
- final render review must happen on frames extracted from the final MP4.

The older V1/V2/V3 experiments are intentionally not migrated into the production factory.
