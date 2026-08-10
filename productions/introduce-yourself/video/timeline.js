/* global gsap, lottie */
const T = window.__V4_TIMING__;
if (!T) throw new Error('Missing window.__V4_TIMING__');

const tl = gsap.timeline({ paused: true });
const ease = 'power3.out';
const scenes = T.scenes;

const booksContainer = document.getElementById('booksLottie');
if (booksContainer && window.lottie) {
  const books = lottie.loadAnimation({
    container: booksContainer,
    renderer: 'svg',
    loop: false,
    autoplay: false,
    path: 'assets/lottie/school-books.json',
  });
  const offsetMs = scenes[8].start * 1000;
  const seekBooks = books.goToAndStop.bind(books);
  books.goToAndStop = (value, isFrame) => {
    if (isFrame) return seekBooks(value, true);
    return seekBooks(Math.max(0, value - offsetMs), false);
  };
  window.__hfLottie = window.__hfLottie || [];
  window.__hfLottie.push(books);
}

function showScene(n) {
  const s = scenes[n - 1];
  const sel = `.s${n}`;
  tl.set(sel, { autoAlpha: 1 }, s.start);
  if (n < scenes.length) tl.set(sel, { autoAlpha: 0 }, Math.max(s.start, s.end - 0.04));
}

function reveal(selector, at, vars = {}) {
  tl.fromTo(selector,
    { autoAlpha: 0, y: 28, scale: 0.985, ...vars },
    { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: 0.55, ease },
    at,
  );
}

function highlight(cueKey, at, hold = 1.15) {
  const selector = `[data-cue="${cueKey}"]`;
  tl.to(selector, {
    scale: 1.025,
    borderColor: '#278f84',
    backgroundColor: '#eaf6f3',
    duration: 0.2,
    ease: 'power2.out',
  }, at);
  tl.to(selector, {
    scale: 1,
    borderColor: '#ded3c5',
    backgroundColor: 'rgba(255,250,243,.55)',
    duration: 0.3,
    ease: 'power2.inOut',
  }, at + hold);
}

tl.set('.scene', { autoAlpha: 0 }, 0);
for (let i = 1; i <= 9; i += 1) showScene(i);

reveal('.s1 .kicker', scenes[0].start + 0.08, { x: -24, y: 0 });
reveal('.s1 .question', scenes[0].start + 0.28, { x: -55, y: 0 });
tl.fromTo('.s1 .sentence-stack span',
  { autoAlpha: 0, x: 55 },
  { autoAlpha: 1, x: 0, duration: 0.4, stagger: 0.28, ease },
  scenes[0].start + 1.3,
);
reveal('.s1 .hero-ar', Math.max(scenes[0].start + 1.2, scenes[0].end - 2.8), { x: 40, y: 0 });

reveal('.s2 .maya-card', scenes[1].start + 0.18, { x: -45, y: 0 });
tl.fromTo('.s2 .model-lines>div',
  { autoAlpha: 0, x: 38 },
  { autoAlpha: 1, x: 0, duration: 0.34, stagger: 0.1, ease },
  scenes[1].start + 0.5,
);
reveal('.s2 .name-note', Math.max(scenes[1].start + 1.2, scenes[1].end - 4), { y: 28 });
highlight('maya.hello', T.cues.maya.hello);
highlight('maya.from', T.cues.maya.from);
highlight('maya.live', T.cues.maya.live);
highlight('maya.role', T.cues.maya.role);
highlight('maya.like', T.cues.maya.like, 1.4);

reveal('.s3 .origin-main', scenes[2].start + 0.2, { x: -50, y: 0 });
tl.fromTo('.s3 .origin-examples>div',
  { autoAlpha: 0, x: 42 },
  { autoAlpha: 1, x: 0, duration: 0.4, stagger: 0.16, ease },
  scenes[2].start + 0.7,
);
highlight('origin.jordan', T.cues.origin.jordan);
highlight('origin.egypt', T.cues.origin.egypt);
highlight('origin.saudi', T.cues.origin.saudi, 1.35);

reveal('.s4 .origin', scenes[3].start + 0.2, { x: -45, y: 0 });
reveal('.s4 .now', scenes[3].start + 0.45, { x: 45, y: 0 });
reveal('.s4 .route', scenes[3].start + 0.9, { scale: 0.8, y: 0 });
tl.fromTo('.s4 .contrast-examples span',
  { autoAlpha: 0, y: 24 },
  { autoAlpha: 1, y: 0, duration: 0.3, stagger: 0.14, ease },
  scenes[3].start + 1.05,
);
highlight('contrast.liveAmman', T.cues.contrast.liveAmman);
highlight('contrast.fromEgypt', T.cues.contrast.fromEgypt);
highlight('contrast.liveDubai', T.cues.contrast.liveDubai, 1.5);

reveal('.s5 .live-word', scenes[4].start + 0.18, { x: -50, y: 0 });
reveal('.s5 .phoneme.good', scenes[4].start + 0.65, { y: 34 });
reveal('.s5 .phoneme.bad', scenes[4].start + 1.05, { y: 34 });
reveal('.s5 .pron-copy', scenes[4].start + 1.35, { x: -25, y: 0 });
reveal('.s5 .repeat-card', Math.max(scenes[4].start + 1.2, T.cues.pronunciation.sentence - 0.45), { x: 50, y: 0 });
highlight('pronunciation.correct', T.cues.pronunciation.correct, 1.1);
highlight('pronunciation.wrong', T.cues.pronunciation.wrong, 1.1);
highlight('pronunciation.sentence', T.cues.pronunciation.sentence, 1.5);

tl.fromTo('.s6 .detail-columns section',
  { autoAlpha: 0, y: 42 },
  { autoAlpha: 1, y: 0, duration: 0.55, stagger: 0.18, ease },
  scenes[5].start + 0.25,
);
reveal('.s6 .quiet-note', Math.max(scenes[5].start + 1, scenes[5].end - 2.7), { x: 35, y: 0 });
highlight('role.designer', T.cues.role.designer);
highlight('role.teacher', T.cues.role.teacher);
highlight('role.engineer', T.cues.role.engineer);
highlight('role.student', T.cues.role.student, 1.35);

tl.fromTo('.s7 .detail-columns section',
  { autoAlpha: 0, y: 42 },
  { autoAlpha: 1, y: 0, duration: 0.55, stagger: 0.18, ease },
  scenes[6].start + 0.25,
);
reveal('.s7 .quiet-note', Math.max(scenes[6].start + 1, scenes[6].end - 3), { x: 35, y: 0 });
highlight('interest.photography', T.cues.interest.photography);
highlight('interest.reading', T.cues.interest.reading);
highlight('interest.football', T.cues.interest.football);
highlight('interest.cooking', T.cues.interest.cooking, 1.35);

reveal('.s8 .omar-card', scenes[7].start + 0.2, { x: 55, y: 0 });
tl.fromTo('.s8 .model-lines>div',
  { autoAlpha: 0, x: -40 },
  { autoAlpha: 1, x: 0, duration: 0.34, stagger: 0.1, ease },
  scenes[7].start + 0.5,
);
highlight('omar.hello', T.cues.omar.hello);
highlight('omar.from', T.cues.omar.from);
highlight('omar.live', T.cues.omar.live);
highlight('omar.role', T.cues.omar.role);
highlight('omar.like', T.cues.omar.like);
highlight('omar.meet', T.cues.omar.meet, 1.4);

reveal('.s9 .final-copy small', scenes[8].start + 0.2, { x: -28, y: 0 });
reveal('.s9 .final-copy h1', scenes[8].start + 0.5, { x: -50, y: 0, scale: 0.96 });
reveal('.s9 .final-copy p', scenes[8].start + 0.95, { x: 25, y: 0 });
tl.fromTo('.s9 .summary-orbit span',
  { autoAlpha: 0, y: 30, scale: 0.94 },
  { autoAlpha: 1, y: 0, scale: 1, duration: 0.4, stagger: 0.18, ease },
  scenes[8].start + 0.8,
);
reveal('.s9 .books-lottie', scenes[8].start + 0.75, { x: 30, y: 0, scale: 0.92 });
reveal('.s9 .say-now', Math.max(scenes[8].start + 1.4, T.cues.closing.seeYou - 0.35), { y: 26 });
tl.to('.s9 .say-now', { scale: 1.055, duration: 0.2, ease: 'power2.out' }, T.cues.closing.seeYou);
tl.to('.s9 .say-now', { scale: 1, duration: 0.3, ease: 'power2.inOut' }, T.cues.closing.seeYou + 1.6);

window.__V4_TIMELINE__ = tl;
