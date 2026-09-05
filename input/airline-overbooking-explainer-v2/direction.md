# Creative direction — Why Airlines Sell More Tickets Than Seats (V3)

Create a fast, witty, English-language **stickman editorial explainer** about airline overbooking.

## Core promise
The viewer should feel like they discovered a hidden system, not attended a lesson. Curiosity first, explanation second.

## Tone
Smart, fast, playful, adult, slightly dry humor. The narrator sounds amused by the system, not angry at airlines. No meme spam, no childish cartoon energy, no classroom framing.

## Narration and synchronization
Use the existing Qwen3-TTS 0.6B / Aiden narration. The rendered audio is the timing source of truth.

Do **not** schedule visuals from estimated script timing or from the seven audio-part durations. HyperFrames local transcription must listen back to the generated Qwen audio and produce word-level timings. Every primary image cut and narration-linked HTML scene must resolve from an explicit word/phrase anchor in `final/airline-overbooking-explainer-v2.transcript.json`.

If word alignment is unavailable or anchor resolution fails, stop the video build rather than rendering a visibly unsynchronized cut.

## Visual identity
The default style for this video and channel is **2D editorial stickman illustration**.

Use:
- simple expressive stick figures with round heads, dot eyes, readable poses and gestures;
- clean black/dark ink lines;
- warm off-white/paper background;
- restrained dark navy plus muted red/amber accent shapes;
- simplified airport, airplane, ticket, phone, desk and luggage props;
- flat/lightly textured illustration with strong silhouettes;
- clean editorial composition.

Avoid:
- photoreal people or environments;
- fake stock photography;
- realistic skin/anatomy;
- 3D-render look;
- lens bokeh/cinematic-photo language;
- embedded readable text, exact numbers or logos inside generated images;
- accidental switching between anime, photoreal, 3D and flat illustration.

## Hard rule: HTML never sits on the generated image
Generated stickman images and HTML information design are **separate scenes**.

When the narration needs exact text, numbers, a counter, legal note, chart or diagram, cut away from the image to a dedicated HTML scene with its own solid/gradient/pattern background.

Examples:
- `180 SEATS` is a separate kinetic-type scene.
- `185 TICKETS` is a separate scene or direct matched cut.
- `NO, NOBODY FAILED KINDERGARTEN` is a separate dry punchline card.
- `$200 → $400` is a separate animated offer/counter scene.
- `COST ONE` / `COST TWO` is a separate diagram scene.

Then return to a clean stickman illustration. Do not put these readable HTML elements over the generated artwork.

Use animated background motifs such as seat grids, ticket strips, dots, probability particles, subtle lines, paper texture, or channel-color geometric patterns. Keep them tasteful and fast.

## Shot cadence
Generate **36 primary stickman images** for this ~3-minute piece. This is intentionally much denser than V2.

Typical image hold: roughly 2.5–6 seconds. Avoid an uninterrupted primary still longer than ~7 seconds.

The separate HTML information scenes are additional cuts, so the finished edit may naturally contain 40–50 total scenes even though only 36 are generated images.

Cuts must correspond to new semantic beats, jokes, examples, comparisons or reveals — never arbitrary image churn.

## HyperFrames workflow
Before authoring/revising the composition, read the current vendored HyperFrames router and the `faceless-explainer` workflow under `vendor/hyperframes/skills/`, plus any routed core/audio/animation/creative/media skills.

Use HyperFrames as the deterministic authoring, timing, preview, QA and render shell. Keep Video Factory's approved providers: Qwen for narration and the private Image Generation API for generated images.

## Story structure
1. Hook: 180 seats, 185 tickets. “No, nobody failed kindergarten.”
2. Reveal predictable no-shows and expiring seat inventory.
3. Show the forecast and the perfect case.
4. Run the 7 / 5 / 0 no-show outcomes.
5. Escalate to the crowded gate and auction-like volunteer offer.
6. Reveal the empty-seat-cost vs overbooking-cost tradeoff.
7. Show different route behavior and that not every airline oversells.
8. Close on the deeper insight: airlines are managing probabilities around chairs.

## Signature humor beats
- `No, nobody failed kindergarten.` — dedicated HTML punchline scene, then a stickman analyst looking mildly offended by the accusation.
- `The spreadsheet gets a tiny promotion.` — clean stickman spreadsheet/trophy gag, no text overlay.
- `starts sounding like an auction.` — gate agent briefly framed like an auctioneer.
- `$200 → $400` — dedicated HTML counter scene, followed by a separate stickman volunteer/suitcase gag.
- `never liked this destination anyway.` — stickman happily leaving while everyone else looks confused.

## Accuracy guardrails
- Overbooking is not universal; some airlines do not oversell.
- No-show figures in the script are hypothetical examples, not industry averages.
- Airlines use revenue-management / forecasting systems and historical behavior; do not claim a universal proprietary formula.
- Passenger rights vary by jurisdiction. The U.S. DOT requires airlines to seek volunteers before involuntary denied boarding due to oversales; do not imply that exact rule is global.

## Audio
One English narrator: Qwen3-TTS 0.6B CustomVoice, Aiden. Conversational, confident and quick but never rushed. Dry comedic timing comes from writing, punctuation and pauses. Soundtrack remains disabled for this test.

## QA
A successful render is not approval.

Reject the cut if:
- a narration-linked image/text event is visibly early or late;
- readable HTML is placed on top of generated artwork;
- a primary image sits too long without a meaningful beat;
- stickman style drifts;
- generated images contain distracting artifacts or gibberish text;
- an HTML scene clips/collides;
- a joke has no visual response;
- image changes feel unrelated to the spoken idea.

Review representative full-resolution frames and progression strips from the actual rendered MP4 before approval.
