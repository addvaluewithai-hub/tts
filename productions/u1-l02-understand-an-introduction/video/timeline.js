/* global gsap */
const T = window.__U1L02_TIMING__;
if (!T) throw new Error('Missing window.__U1L02_TIMING__');

const tl = gsap.timeline({ paused: true });
const scenes = T.scenes;
const ease = 'power3.out';

function showScene(n) {
  const s = scenes[n - 1];
  const sel = `.s${n}`;
  tl.set(sel, { autoAlpha: 1 }, s.start);
  if (n < scenes.length) tl.set(sel, { autoAlpha: 0 }, Math.max(s.start, s.end - 0.04));
}

function reveal(selector, at, from = {}) {
  tl.fromTo(selector,
    { autoAlpha: 0, y: 26, scale: 0.985, ...from },
    { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: 0.52, ease },
    at,
  );
}

function pulse(cueKey, at, hold = 1.15) {
  const selector = `[data-cue="${cueKey}"]`;
  tl.to(selector, { scale: 1.025, duration: 0.18, ease: 'power2.out' }, at);
  tl.to(selector, { scale: 1, duration: 0.28, ease: 'power2.inOut' }, at + hold);
}

tl.set('.scene', { autoAlpha: 0 }, 0);
for (let n = 1; n <= scenes.length; n += 1) showScene(n);

// Scene 1 — listen before translating.
reveal('.s1 .topline', scenes[0].start + 0.08, { y: -18 });
reveal('.s1 .eyebrow', scenes[0].start + 0.25, { x: -30, y: 0 });
reveal('.s1 h1', scenes[0].start + 0.5, { x: -42, y: 0 });
reveal('.s1 .sub', scenes[0].start + 0.9, { x: -25, y: 0 });
reveal('.s1 .voice-card', Math.max(scenes[0].start + 0.8, T.cues.listen.model - 0.5), { x: 48, y: 0 });
tl.fromTo('.s1 .waveform i',
  { scaleY: 0.28, opacity: 0.35 },
  { scaleY: 1, opacity: 1, duration: 0.32, stagger: 0.055, ease: 'power2.out' },
  T.cues.listen.model,
);
reveal('.s1 .who-question', Math.max(scenes[0].start + 1.4, T.cues.listen.who - 0.35), { x: -32, y: 0 });
pulse('listen.model', T.cues.listen.model, 1.5);
pulse('listen.who', T.cues.listen.who, 1.4);

// Scene 2 — identify Alex, then recognize signals.
reveal('.s2 .topline', scenes[1].start + 0.08, { y: -18 });
reveal('.s2 .big-who', scenes[1].start + 0.25, { x: -55, y: 0, scale: 0.95 });
reveal('.s2 .identity-card', Math.max(scenes[1].start + 0.55, T.cues.alex.name - 0.35), { y: 35 });
tl.fromTo('.s2 .signal',
  { autoAlpha: 0, x: 46 },
  { autoAlpha: 1, x: 0, duration: 0.42, stagger: 0.16, ease },
  scenes[1].start + 0.9,
);
pulse('alex.name', T.cues.alex.name, 1.25);
pulse('alex.from', T.cues.alex.from, 1.2);
pulse('alex.lives', T.cues.alex.lives, 1.3);

// Scene 3 — complete fact board and separate facts from translation.
reveal('.s3 .topline', scenes[2].start + 0.08, { y: -18 });
reveal('.s3 .profile-summary', scenes[2].start + 0.25, { y: 34 });
tl.fromTo('.s3 .fact',
  { autoAlpha: 0, y: 24 },
  { autoAlpha: 1, y: 0, duration: 0.38, stagger: 0.12, ease },
  scenes[2].start + 0.65,
);
reveal('.s3 .translation-rule', scenes[2].start + 1.3, { x: -32, y: 0 });
reveal('.s3 .me-lane', Math.max(scenes[2].start + 1.7, T.cues.facts.firstPerson - 0.4), { x: 36, y: 0 });
pulse('facts.role', T.cues.facts.role, 1.25);
pulse('facts.firstPerson', T.cues.facts.firstPerson, 1.4);

// Scene 4 — ownership contrast between speaker and Omar.
reveal('.s4 .topline', scenes[3].start + 0.08, { y: -18 });
reveal('.s4 .owner-lane.me', scenes[3].start + 0.25, { x: -45, y: 0 });
reveal('.s4 .versus', scenes[3].start + 0.55, { scale: 0.7, y: 0 });
reveal('.s4 .owner-lane.omar', Math.max(scenes[3].start + 0.75, T.cues.omar.model - 0.45), { x: 48, y: 0 });
reveal('.s4 .omar-facts>div:nth-child(1)', Math.max(scenes[3].start + 1.2, T.cues.omar.from - 0.25), { x: 24, y: 0 });
reveal('.s4 .omar-facts>div:nth-child(2)', Math.max(scenes[3].start + 1.45, T.cues.omar.lives - 0.25), { x: 24, y: 0 });
reveal('.s4 .omar-facts>div:nth-child(3)', T.cues.omar.lives + 0.65, { x: 24, y: 0 });
pulse('omar.identity', T.cues.omar.identity, 1.3);
pulse('omar.from', T.cues.omar.from, 1.15);
pulse('omar.lives', T.cues.omar.lives, 1.25);

// Scene 5 — Layla reinforces pronoun ownership.
reveal('.s5 .topline', scenes[4].start + 0.08, { y: -18 });
reveal('.s5 .pronoun-card.muted', scenes[4].start + 0.25, { x: -36, y: 0 });
reveal('.s5 .pronoun-card.she', Math.max(scenes[4].start + 0.45, T.cues.layla.model - 0.35), { y: 28 });
reveal('.s5 .layla-card', Math.max(scenes[4].start + 0.65, T.cues.layla.model - 0.25), { x: 42, y: 0 });
reveal('.s5 .teacher-fact', Math.max(scenes[4].start + 1.1, T.cues.layla.teacher - 0.3), { y: 24 });
reveal('.s5 .summary-rule', Math.max(scenes[4].start + 1.4, T.cues.layla.summary - 0.35), { y: 28 });
pulse('layla.model', T.cues.layla.model, 1.2);
pulse('layla.teacher', T.cues.layla.teacher, 1.3);
pulse('layla.summary', T.cues.layla.summary, 1.4);

// Scene 6 — compact mental model for practice.
reveal('.s6 .topline', scenes[5].start + 0.08, { y: -18 });
reveal('.s6 .strategy-title small', scenes[5].start + 0.28, { y: 18 });
reveal('.s6 .strategy-title h1', scenes[5].start + 0.48, { y: 26, scale: 0.97 });
tl.fromTo('.s6 .strategy-step',
  { autoAlpha: 0, y: 32, scale: 0.97 },
  { autoAlpha: 1, y: 0, scale: 1, duration: 0.46, stagger: 0.18, ease },
  scenes[5].start + 0.9,
);
reveal('.s6 .practice-cta', Math.max(scenes[5].start + 1.4, T.cues.close.practice - 0.35), { y: 26 });
reveal('.s6 .meaning-cta', Math.max(scenes[5].start + 1.8, T.cues.close.meaning - 0.35), { y: 26 });
tl.to('.s6 .meaning-cta', { scale: 1.04, duration: 0.2, ease: 'power2.out' }, T.cues.close.meaning);
tl.to('.s6 .meaning-cta', { scale: 1, duration: 0.32, ease: 'power2.inOut' }, T.cues.close.meaning + 1.4);

window.__U1L02_TIMELINE__ = tl;
