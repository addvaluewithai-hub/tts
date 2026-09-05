/* global gsap */
const T = window.__AIRLINE_TIMING__;
if (!T) throw new Error('Missing window.__AIRLINE_TIMING__');
if (T.compositionId !== 'airline-overbooking-v3') {
  throw new Error(`Unexpected timing composition: ${T.compositionId}`);
}

const tl = gsap.timeline({ paused: true });

function imageMove(name) {
  const moves = {
    'push-left':  { from: { x: 26, y: 0, scale: 1.018 }, to: { x: -22, y: 0, scale: 1.078 } },
    'push-right': { from: { x: -26, y: 0, scale: 1.018 }, to: { x: 22, y: 0, scale: 1.078 } },
    'push-up':    { from: { x: 0, y: 24, scale: 1.018 }, to: { x: 0, y: -20, scale: 1.078 } },
    'push-down':  { from: { x: 0, y: -24, scale: 1.018 }, to: { x: 0, y: 20, scale: 1.078 } },
  };
  return moves[name] || moves['push-left'];
}

function animateImage(scene) {
  const root = document.getElementById(scene.domId);
  if (!root) throw new Error(`Missing image scene DOM: ${scene.domId}`);
  const shell = root.querySelector('.image-shell');
  if (!shell) throw new Error(`Missing image shell: ${scene.domId}`);

  const move = imageMove(scene.motion);
  tl.fromTo(
    shell,
    { ...move.from, opacity: 0.94 },
    {
      ...move.to,
      opacity: 1,
      duration: Math.max(0.12, scene.duration),
      ease: 'none',
      immediateRender: false,
    },
    scene.start,
  );
}

function animateInformation(scene) {
  const root = document.getElementById(scene.domId);
  if (!root) throw new Error(`Missing information scene DOM: ${scene.domId}`);

  const pattern = root.querySelector('.pattern-layer');
  const headline = root.querySelector('.info-headline');
  const middle = root.querySelector('.info-middle');
  const subline = root.querySelector('.info-subline');

  const duration = Math.max(0.12, scene.duration);
  if (pattern) {
    const sign = scene.index % 2 === 0 ? 1 : -1;
    tl.fromTo(
      pattern,
      { x: -12 * sign, y: 8 * sign, rotation: -0.35 * sign, scale: 1.01 },
      {
        x: 14 * sign,
        y: -10 * sign,
        rotation: 0.35 * sign,
        scale: 1.025,
        duration,
        ease: 'none',
        immediateRender: false,
      },
      scene.start,
    );
  }

  const inTime = Math.min(0.44, Math.max(0.12, duration * 0.28));
  if (headline) {
    const impact = root.querySelector('.variant-punch, .variant-offer-hot');
    tl.fromTo(
      headline,
      impact
        ? { opacity: 0, scale: 0.72, x: -34 }
        : { opacity: 0, x: -96, y: 10, scale: 0.97 },
      {
        opacity: 1,
        x: 0,
        y: 0,
        scale: 1,
        duration: inTime,
        ease: impact ? 'back.out(1.5)' : 'power3.out',
        immediateRender: false,
      },
      scene.start + 0.02,
    );
  }

  if (middle) {
    tl.fromTo(
      middle,
      { opacity: 0, scale: 0.68, rotation: -2 },
      {
        opacity: 1,
        scale: 1,
        rotation: 0,
        duration: Math.min(0.38, Math.max(0.12, duration * 0.24)),
        ease: 'back.out(1.35)',
        immediateRender: false,
      },
      scene.start + Math.min(0.2, duration * 0.22),
    );
  }

  if (subline) {
    tl.fromTo(
      subline,
      { opacity: 0, y: 54, x: 18 },
      {
        opacity: 1,
        y: 0,
        x: 0,
        duration: Math.min(0.42, Math.max(0.12, duration * 0.26)),
        ease: 'power3.out',
        immediateRender: false,
      },
      scene.start + Math.min(middle ? 0.34 : 0.18, duration * 0.36),
    );
  }

  // Let the read settle. No perpetual breathing/screen-saver motion.
  if (headline && duration > 1.0) {
    tl.to(
      headline,
      {
        scale: 1.018,
        duration: Math.min(0.22, duration * 0.1),
        ease: 'power2.out',
        yoyo: true,
        repeat: 1,
      },
      scene.start + Math.min(duration * 0.55, 0.78),
    );
  }
}

for (const scene of T.scenes) {
  if (scene.mode === 'image') animateImage(scene);
  else animateInformation(scene);
}

window.__timelines = window.__timelines || {};
window.__timelines['airline-overbooking-v3'] = tl;
