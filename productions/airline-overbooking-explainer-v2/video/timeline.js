/* global gsap */
const T = window.__AIRLINE_TIMING__;
if (!T) throw new Error('Missing window.__AIRLINE_TIMING__');
if (T.compositionId !== 'airline-overbooking-v4') {
  throw new Error(`Unexpected timing composition: ${T.compositionId}`);
}

const tl = gsap.timeline({ paused: true });

function imageMove(name) {
  const moves = {
    'float-left':  { from: { x: 10, y: 2, rotation: 0.08 }, to: { x: -10, y: -3, rotation: -0.08 } },
    'float-right': { from: { x: -10, y: -2, rotation: -0.08 }, to: { x: 10, y: 3, rotation: 0.08 } },
    'float-up':    { from: { x: 2, y: 9, rotation: 0.05 }, to: { x: -2, y: -9, rotation: -0.05 } },
    'float-down':  { from: { x: -2, y: -9, rotation: -0.05 }, to: { x: 2, y: 9, rotation: 0.05 } },
  };
  return moves[name] || moves['float-left'];
}

function animateImage(scene) {
  const root = document.getElementById(scene.domId);
  if (!root) throw new Error(`Missing image scene DOM: ${scene.domId}`);
  const card = root.querySelector('.image-card');
  const backdrop = root.querySelector('.image-backdrop');
  const accents = root.querySelectorAll('.image-accent i');
  if (!card || !backdrop) throw new Error(`Missing V4 image layers: ${scene.domId}`);

  const move = imageMove(scene.motion);
  const duration = Math.max(0.12, scene.duration);

  // Foreground image stays fully visible: no scale/crop. Motion is only a tiny float.
  tl.fromTo(
    card,
    { ...move.from, opacity: 0.965 },
    {
      ...move.to,
      opacity: 1,
      duration,
      ease: 'sine.inOut',
      immediateRender: false,
    },
    scene.start,
  );

  // The duplicated backdrop can move more because it carries no unique information.
  const sign = scene.index % 2 === 0 ? 1 : -1;
  tl.fromTo(
    backdrop,
    { x: -18 * sign, y: 12 * sign, scale: 1.045, rotation: -0.12 * sign },
    {
      x: 22 * sign,
      y: -14 * sign,
      scale: 1.085,
      rotation: 0.12 * sign,
      duration,
      ease: 'none',
      immediateRender: false,
    },
    scene.start,
  );

  accents.forEach((accent, index) => {
    const delay = 0.08 + index * 0.08;
    const from = index === 1
      ? { opacity: 0, scaleX: 0, x: -18 }
      : { opacity: 0, scale: 0.72, y: 12 };
    const to = index === 1
      ? { opacity: 1, scaleX: 1, x: 0 }
      : { opacity: 0.82, scale: 1, y: 0 };
    tl.fromTo(
      accent,
      from,
      {
        ...to,
        duration: Math.min(0.5, Math.max(0.16, duration * 0.22)),
        ease: 'power3.out',
        immediateRender: false,
      },
      scene.start + Math.min(delay, duration * 0.18),
    );

    if (duration > 1.15) {
      tl.to(
        accent,
        {
          x: index === 0 ? -10 * sign : index === 2 ? 12 * sign : 0,
          y: index === 0 ? 8 : index === 2 ? -6 : 0,
          rotation: index === 0 ? 2.2 * sign : 0,
          duration: Math.max(0.2, duration - Math.min(delay + 0.45, duration * 0.3)),
          ease: 'sine.inOut',
        },
        scene.start + Math.min(delay + 0.4, duration * 0.32),
      );
    }
  });
}

function animateInformation(scene) {
  const root = document.getElementById(scene.domId);
  if (!root) throw new Error(`Missing information scene DOM: ${scene.domId}`);

  const pattern = root.querySelector('.pattern-layer');
  const patternBits = root.querySelectorAll('.pattern-layer i');
  const echo = root.querySelector('.info-echo');
  const headline = root.querySelector('.info-headline');
  const middle = root.querySelector('.info-middle');
  const subline = root.querySelector('.info-subline');
  const rails = root.querySelectorAll('.info-rail span');
  const duration = Math.max(0.12, scene.duration);
  const sign = scene.index % 2 === 0 ? 1 : -1;

  if (pattern) {
    tl.fromTo(
      pattern,
      { x: -28 * sign, y: 18 * sign, rotation: -0.55 * sign, scale: 1.015 },
      {
        x: 34 * sign,
        y: -22 * sign,
        rotation: 0.55 * sign,
        scale: 1.04,
        duration,
        ease: 'none',
        immediateRender: false,
      },
      scene.start,
    );
  }

  patternBits.forEach((bit, index) => {
    const localSign = index % 2 === 0 ? 1 : -1;
    tl.fromTo(
      bit,
      { x: 0, y: 0, rotation: 0 },
      {
        x: localSign * (10 + index * 2),
        y: -localSign * (6 + index),
        rotation: localSign * (1.2 + index * 0.18),
        duration,
        ease: 'sine.inOut',
        immediateRender: false,
      },
      scene.start,
    );
  });

  if (echo) {
    tl.fromTo(
      echo,
      { opacity: 0, x: 90 * sign, scale: 0.94 },
      {
        opacity: 0.8,
        x: 0,
        scale: 1,
        duration: Math.min(0.72, Math.max(0.2, duration * 0.3)),
        ease: 'power3.out',
        immediateRender: false,
      },
      scene.start + 0.02,
    );
    if (duration > 1.0) {
      tl.to(
        echo,
        {
          x: -22 * sign,
          y: 8 * sign,
          duration: Math.max(0.22, duration - 0.48),
          ease: 'none',
        },
        scene.start + Math.min(0.48, duration * 0.34),
      );
    }
  }

  const impact = ['punch', 'offer-hot', 'stat', 'seat'].includes(scene.variant);
  const inTime = Math.min(0.54, Math.max(0.16, duration * 0.28));

  if (headline) {
    tl.fromTo(
      headline,
      impact
        ? { opacity: 0, y: 48, scale: 0.82, clipPath: 'inset(100% 0 0 0)' }
        : { opacity: 0, x: -88 * sign, y: 12, scale: 0.97, clipPath: 'inset(0 100% 0 0)' },
      {
        opacity: 1,
        x: 0,
        y: 0,
        scale: 1,
        clipPath: 'inset(0% 0% 0% 0%)',
        duration: inTime,
        ease: impact ? 'back.out(1.28)' : 'power3.out',
        immediateRender: false,
      },
      scene.start + 0.04,
    );
  }

  if (middle) {
    tl.fromTo(
      middle,
      { opacity: 0, scale: 0.66, rotation: -3 * sign },
      {
        opacity: 1,
        scale: 1,
        rotation: 0,
        duration: Math.min(0.48, Math.max(0.14, duration * 0.24)),
        ease: 'back.out(1.4)',
        immediateRender: false,
      },
      scene.start + Math.min(0.22, duration * 0.23),
    );
  }

  if (subline) {
    tl.fromTo(
      subline,
      { opacity: 0, y: 62, x: 20 * sign, clipPath: 'inset(100% 0 0 0)' },
      {
        opacity: 1,
        y: 0,
        x: 0,
        clipPath: 'inset(0% 0% 0% 0%)',
        duration: Math.min(0.5, Math.max(0.14, duration * 0.27)),
        ease: 'power3.out',
        immediateRender: false,
      },
      scene.start + Math.min(middle ? 0.38 : 0.22, duration * 0.36),
    );
  }

  rails.forEach((rail, index) => {
    tl.fromTo(
      rail,
      { scaleX: 0, opacity: 0.25 },
      {
        scaleX: 1,
        opacity: 1,
        duration: Math.min(0.62, Math.max(0.16, duration * 0.35)),
        ease: 'power2.out',
        immediateRender: false,
      },
      scene.start + Math.min(0.14 + index * 0.08, duration * 0.3),
    );
  });

  if (headline && duration > 1.1) {
    tl.to(
      headline,
      {
        y: -8,
        duration: Math.max(0.18, duration * 0.34),
        ease: 'sine.inOut',
        yoyo: true,
        repeat: 1,
      },
      scene.start + Math.min(0.72, duration * 0.48),
    );
  }
}

for (const scene of T.scenes) {
  if (scene.mode === 'image') animateImage(scene);
  else animateInformation(scene);
}

window.__timelines = window.__timelines || {};
window.__timelines['airline-overbooking-v4'] = tl;
