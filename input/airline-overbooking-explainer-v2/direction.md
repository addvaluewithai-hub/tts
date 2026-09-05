# Creative direction — Why Airlines Sell More Tickets Than Seats (V2)

Create a fast, witty, English-language image-first YouTube explainer about airline overbooking.

## Core promise
The viewer should feel like they discovered a hidden system, not attended a lesson. Curiosity first, explanation second.

## Tone
Smart, fast, playful, adult, slightly dry humor. The narrator sounds amused by the system, not angry at airlines. No meme spam, no childish cartoon energy, no classroom framing.

## Visual strategy
Image-first. Most shots should be premium generated editorial/cinematic images, then animated with push-ins, pans, reframing, masks, parallax and transitions. Use HTML/CSS/vector elements mainly for precise overlays: numbers, seat counts, arrows, counters, labels, probability cues and short punchline cards.

Do not ask the image model to render critical text or exact diagrams. Keep all exact typography and numbers in post.

Preferred visual language: premium modern editorial photography with subtle stylized CGI polish; dark navy, warm ivory and restrained red accents; airport lighting; clean composition; generous negative space for overlays. No airline logos or identifiable brands.

## Story structure
1. Hook: 180 seats, 185 tickets. “No, nobody failed kindergarten.”
2. Reveal the missing variable: predictable no-shows and expiring seat inventory.
3. Run a simple visual simulation: 185 tickets, different numbers of no-shows.
4. Escalate to the failure case: everyone shows up.
5. Show volunteers / compensation as the system’s pressure-release valve.
6. Reveal the optimization problem: empty-seat cost vs overbooking cost.
7. Close on the deeper insight: airlines are managing probabilities around seats.

## Pacing
Target 2:30–3:10. Meaningful visual change every 3–7 seconds. New story beat every 10–20 seconds. First 15 seconds must work with zero context. No logo intro, definition, or history.

## Signature beats
- Full-bleed premium cabin image. Overlay seat counter races to 180; five ticket cards slide in with nowhere to go.
- Empty seat image by a plane window. Overlay value falls to $0 at departure.
- Reuse/refocus a cabin image for three fast simulations: 7 no-shows / 5 no-shows / 0 no-shows.
- Fully crowded gate image for the failure case; five clean passenger silhouettes remain outside the seat grid overlay. Punchline: “statistical error has entered the chat.”
- Gate crowd + volunteer image. Compensation counter rises while one traveler raises a hand; suitcase motion can land the joke.
- Conceptual split image for the tradeoff: empty seat vs compensation cost, with the precise scale/labels added in post.
- Final close-up seat/cabin image transitions into a probability-network overlay and collapses to a simple aircraft silhouette.

## Accuracy guardrails
- Overbooking is not universal; some airlines do not oversell.
- No-show figures in the script are hypothetical examples, not industry averages.
- Airlines use revenue-management / forecasting systems and historical behavior; do not claim a universal proprietary formula.
- Passenger rights vary by jurisdiction. The U.S. DOT requires airlines to seek volunteers before involuntary denied boarding due to oversales; do not imply that exact rule is global.

## Audio
One English narrator. Qwen3-TTS 0.6B CustomVoice, Aiden. Conversational, confident and quick but never rushed. Dry comedic timing should come from writing, punctuation and pauses, not unsupported style instructions. Soundtrack disabled for this test.

## QA
Never look like a slideshow. Every still image needs purposeful motion, reframing or overlay progression. Keep generated-image artifacts, anatomy, signage and continuity under manual review. Exact numbers and text must remain crisp and controlled in post.
