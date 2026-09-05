/* global gsap */
const T = window.__AIRLINE_TIMING__;
if (!T) throw new Error('Missing window.__AIRLINE_TIMING__');

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
    { autoAlpha: 0, y: 28, scale: 0.985, ...from },
    { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: 0.48, ease },
    at,
  );
}
function push(selector, scene, scale = 1.11, x = 0, y = 0) {
  tl.fromTo(selector,
    { scale: 1.035, x: 0, y: 0 },
    { scale, x, y, duration: Math.max(1, scene.duration), ease: 'none' },
    scene.start,
  );
}
function crossfade(a, b, at) {
  tl.to(a, { autoAlpha: 0, duration: 0.55, ease: 'power2.inOut' }, at);
  tl.fromTo(b, { autoAlpha: 0, scale: 1.06 }, { autoAlpha: 1, scale: 1.035, duration: 0.65, ease: 'power2.inOut' }, at);
}

// Decorative probability dots are deterministic DOM, not image-model text.
const dotHost = document.querySelector('.prob-dots');
if (dotHost) {
  for (let i = 0; i < 24; i += 1) {
    const d = document.createElement('i');
    d.style.left = `${8 + ((i * 37) % 84)}%`;
    d.style.top = `${18 + ((i * 53) % 58)}%`;
    dotHost.appendChild(d);
  }
}

tl.set('.scene', { autoAlpha: 0 }, 0);
tl.set('.img-b', { autoAlpha: 0 }, 0);
for (let i = 1; i <= 7; i += 1) showScene(i);

// 1 — paradox, then expiring inventory.
push('.s1 .img-a', scenes[0], 1.12, -18, -8);
reveal('.s1 .seat-count', T.cues.hook.seats, { x: -45, y: 0 });
reveal('.s1 .ticket-count', T.cues.hook.tickets, { x: 45, y: 0 });
tl.fromTo('.s1 .ticket-stack i',
  { autoAlpha: 0, y: -60, rotate: -6 },
  { autoAlpha: 1, y: 0, rotate: 0, duration: 0.28, stagger: 0.10, ease: 'back.out(1.5)' },
  T.cues.hook.tickets + 0.35,
);
reveal('.s1 .kindergarten', T.cues.hook.kindergarten, { x: -35, y: 0 });
const s1Switch = Math.max(scenes[0].start + 3.5, T.cues.hook.zero - 2.7);
crossfade('.s1 .img-a', '.s1 .img-b', s1Switch);
reveal('.s1 .zero-card', Math.max(s1Switch + 0.3, T.cues.hook.zero - 1.1), { scale: 0.92, y: 0 });
tl.fromTo('.s1 .zero-card b', { scale: 0.6 }, { scale: 1, duration: 0.35, ease: 'back.out(1.8)' }, T.cues.hook.zero);

// 2 — forecast model and the perfect case.
push('.s2 .img-a', scenes[1], 1.10, 14, 0);
reveal('.s2 .eyebrow', scenes[1].start + 0.15, { x: -25, y: 0 });
reveal('.s2 .forecast-line', T.cues.forecast.model, { y: 35 });
tl.fromTo('.s2 .prob-dots i',
  { autoAlpha: 0, scale: 0.2 },
  { autoAlpha: 0.75, scale: 1, duration: 0.32, stagger: 0.045, ease: 'power2.out' },
  T.cues.forecast.model + 0.25,
);
crossfade('.s2 .img-a', '.s2 .img-b', Math.max(T.cues.forecast.five, T.cues.forecast.humans - 1.2));
reveal('.s2 .promotion', T.cues.forecast.promotion, { x: -30, y: 0 });
tl.to('.s2 .promotion', { scale: 1.035, duration: 0.22, yoyo: true, repeat: 1 }, T.cues.forecast.promotion + 0.35);

// 3 — three outcomes; failure case becomes a crowded gate.
push('.s3 .img-a', scenes[2], 1.08, -10, 0);
reveal('.s3 .eyebrow', scenes[2].start + 0.18, { x: -20, y: 0 });
reveal('.s3 .sim-seven', T.cues.simulation.seven, { y: 40 });
reveal('.s3 .sim-five', T.cues.simulation.five, { y: 40 });
reveal('.s3 .sim-zero', T.cues.simulation.nobody, { y: 40, scale: 0.94 });
crossfade('.s3 .img-a', '.s3 .img-b', T.cues.simulation.nobody + 0.3);
reveal('.s3 .statistical', T.cues.simulation.nobody + 0.7, { x: -35, y: 0 });
reveal('.s3 .auction-label', T.cues.simulation.auction, { x: 35, y: 0 });

// 4 — volunteers and the joke.
push('.s4 .img-a', scenes[3], 1.09, 10, -4);
reveal('.s4 .eyebrow', scenes[3].start + 0.15, { x: -20, y: 0 });
reveal('.s4 .volunteer-title', T.cues.volunteers.ask, { x: -45, y: 0 });
reveal('.s4 .us-note', T.cues.volunteers.us, { x: 35, y: 0 });
reveal('.s4 .offer', T.cues.volunteers.two, { y: 42, scale: 0.9 });
reveal('.s4 .offer-two', T.cues.volunteers.four, { y: 42, scale: 0.9 });
crossfade('.s4 .img-a', '.s4 .img-b', Math.max(T.cues.volunteers.two, T.cues.volunteers.four - 0.6));
reveal('.s4 .destination', T.cues.volunteers.destination, { x: 40, y: 0 });

// 5 — cost tradeoff.
push('.s5 .left-img', scenes[4], 1.08, -18, 0);
push('.s5 .right-img', scenes[4], 1.08, 18, 0);
reveal('.s5 .eyebrow', scenes[4].start + 0.15, { x: -25, y: 0 });
reveal('.s5 .cost-one', T.cues.tradeoff.one, { x: -40, y: 0 });
reveal('.s5 .cost-two', T.cues.tradeoff.two, { x: 40, y: 0 });
reveal('.s5 .balance', Math.max(T.cues.tradeoff.twoCosts, T.cues.tradeoff.two + 0.4), { scale: 0.86, y: 0 });
reveal('.s5 .goal', T.cues.tradeoff.goal, { y: 35 });

// 6 — different flights, different behavior.
push('.s6 .img-a', scenes[5], 1.12, 0, -10);
reveal('.s6 .eyebrow', scenes[5].start + 0.15, { x: -20, y: 0 });
reveal('.s6 .business', T.cues.routes.monday, { x: -45, y: 0 });
reveal('.s6 .holiday', T.cues.routes.holiday, { x: 45, y: 0 });
tl.fromTo('.s6 .data-row span',
  { autoAlpha: 0, y: 24 },
  { autoAlpha: 1, y: 0, duration: 0.32, stagger: 0.12, ease },
  T.cues.routes.holiday + 0.65,
);
reveal('.s6 .rule-card', T.cues.routes.some, { y: 38, scale: 0.94 });
tl.to('.s6 .rule-card strong', { scale: 1.04, duration: 0.2, yoyo: true, repeat: 1 }, T.cues.routes.rule);

// 7 — final idea: seat -> model -> aircraft.
push('.s7 .img-a', scenes[6], 1.11, -12, 0);
reveal('.s7 .weird', T.cues.close.weird, { x: -40, y: 0 });
reveal('.s7 .probability', T.cues.close.weird + 1.0, { x: -40, y: 0 });
reveal('.s7 .seat22', T.cues.close.seat, { scale: 0.86, y: 0 });
reveal('.s7 .question', T.cues.close.seat + 1.0, { x: -30, y: 0 });
crossfade('.s7 .img-a', '.s7 .img-b', Math.max(T.cues.close.forgot - 0.5, scenes[6].start + 5));
reveal('.s7 .final-line', T.cues.close.forgot, { x: -35, y: 0 });
tl.to('.s7 .final-line strong', { color: '#ffdfb5', scale: 1.025, transformOrigin: 'left center', duration: 0.32 }, T.cues.close.counted);

window.__AIRLINE_TIMELINE__ = tl;
