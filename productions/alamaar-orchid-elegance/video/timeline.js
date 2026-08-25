(() => {
  const t = window.__ALAMAAR_TIMING__;
  if (!t || !window.gsap) throw new Error('Missing timing data or GSAP');
  const tl = gsap.timeline({ paused: true, defaults: { ease: 'power2.out' } });
  const scenes = t.scenes;

  gsap.set('.scene', { autoAlpha: 0 });

  function reveal(sceneIndex, setup) {
    const s = scenes[sceneIndex];
    const id = `#scene-${String(sceneIndex + 1).padStart(2, '0')}`;
    tl.set(id, { autoAlpha: 1 }, s.start);
    setup(id, s);
    if (sceneIndex < scenes.length - 1) tl.set(id, { autoAlpha: 0 }, Math.max(s.start, s.end - 0.04));
  }

  reveal(0, (id, s) => {
    tl.fromTo(`${id} .image-hero`, { scale: 1.12, xPercent: 1.5 }, { scale: 1.04, xPercent: 0, duration: Math.max(1.2, s.duration - 0.15), ease: 'none' }, s.start)
      .fromTo(`${id} .eyebrow`, { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: .65 }, s.start + .3)
      .fromTo(`${id} h1`, { autoAlpha: 0, y: 34 }, { autoAlpha: 1, y: 0, duration: .9 }, s.start + .55)
      .fromTo(`${id} .hairline`, { scaleX: 0, transformOrigin: 'left center' }, { scaleX: 1, duration: .8 }, s.start + 1.15);
  });

  reveal(1, (id, s) => {
    tl.fromTo(`${id} .image-interior`, { scale: 1.08 }, { scale: 1.025, duration: Math.max(1.2, s.duration), ease: 'none' }, s.start)
      .fromTo(`${id} .eyebrow`, { autoAlpha: 0, x: -24 }, { autoAlpha: 1, x: 0, duration: .55 }, s.start + .25)
      .fromTo(`${id} h2`, { autoAlpha: 0, y: 40 }, { autoAlpha: 1, y: 0, duration: .8 }, s.start + .45)
      .fromTo(`${id} .product-code`, { autoAlpha: 0, width: '0%' }, { autoAlpha: 1, width: 'auto', duration: .7 }, s.start + .9)
      .fromTo(`${id} p`, { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: .6 }, s.start + 1.15);
  });

  reveal(2, (id, s) => {
    tl.fromTo(`${id} .panel-shot`, { scale: 1.08 }, { scale: 1.01, duration: Math.max(1.2, s.duration), ease: 'none' }, s.start)
      .fromTo(`${id} .material-copy .eyebrow`, { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: .5 }, s.start + .25)
      .fromTo(`${id} .material-copy h2`, { autoAlpha: 0, y: 28 }, { autoAlpha: 1, y: 0, duration: .65 }, s.start + .48)
      .fromTo(`${id} .spec-line`, { autoAlpha: 0 }, { autoAlpha: 1, duration: .5 }, s.start + .82)
      .fromTo(`${id} .benefit-row b`, { autoAlpha: 0, x: 16 }, { autoAlpha: 1, x: 0, duration: .4, stagger: .12 }, s.start + 1.0);
  });

  reveal(3, (id, s) => {
    tl.fromTo(`${id} .texture-fill`, { scale: 5.25, xPercent: -1.5 }, { scale: 4.65, xPercent: 1.0, duration: Math.max(1.2, s.duration), ease: 'none' }, s.start)
      .fromTo(`${id} .spec-wrap .eyebrow`, { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, duration: .5 }, s.start + .25)
      .fromTo(`${id} .spec-wrap h2`, { autoAlpha: 0, y: 28 }, { autoAlpha: 1, y: 0, duration: .65 }, s.start + .45)
      .fromTo(`${id} .numbers > div`, { autoAlpha: 0, y: 22 }, { autoAlpha: 1, y: 0, duration: .5, stagger: .16 }, s.start + .88);
  });

  reveal(4, (id, s) => {
    tl.fromTo(`${id} .image-application`, { scale: 1.07 }, { scale: 1.015, duration: Math.max(1.2, s.duration), ease: 'none' }, s.start)
      .fromTo(`${id} .application-copy .eyebrow`, { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, duration: .5 }, s.start + .25)
      .fromTo(`${id} .application-copy h2`, { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: .65 }, s.start + .45)
      .fromTo(`${id} .applications span`, { autoAlpha: 0, y: 12 }, { autoAlpha: 1, y: 0, duration: .36, stagger: .09 }, s.start + .85);
  });

  reveal(5, (id, s) => {
    tl.fromTo(`${id} .image-close`, { scale: 1.12 }, { scale: 1.05, duration: Math.max(1.2, s.duration), ease: 'none' }, s.start)
      .fromTo(`${id} .close-card .eyebrow`, { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: .45 }, s.start + .2)
      .fromTo(`${id} .code-large`, { autoAlpha: 0 }, { autoAlpha: 1, duration: .5 }, s.start + .4)
      .fromTo(`${id} h2`, { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: .7 }, s.start + .58)
      .fromTo(`${id} .brand-lockup`, { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: .55 }, s.start + .95);
  });

  tl.to({}, { duration: Math.max(0, t.duration - tl.duration()) });
  window.__ALAMAAR_TIMELINE__ = tl;
})();
