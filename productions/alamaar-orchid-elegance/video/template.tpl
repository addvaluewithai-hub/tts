<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Al Amaar — Orchid Elegance</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div id="stage" data-composition-id="alamaar-orchid-elegance-premium" data-start="0" data-duration="{{DURATION}}" data-fps="30" data-width="1920" data-height="1080">
    <div class="grain"></div>
    <div class="brand-corner">AL AMAAR <span>HPL & WOOD SOLUTIONS</span></div>

    <section id="scene-01" class="clip scene scene-hero" data-start="{{SCENE_01_START}}" data-duration="{{SCENE_01_DURATION}}" data-track-index="0">
      <img class="fullbleed image-hero" src="assets/product/orchid-hero.webp" alt="Orchid Elegance HPL panel in a dark premium setting" />
      <div class="veil"></div>
      <div class="copy hero-copy">
        <div class="eyebrow">AL AMAAR · MATERIAL STORY</div>
        <h1>Some surfaces fill a space.<br><em>Others define it.</em></h1>
        <div class="hairline"></div>
      </div>
    </section>

    <section id="scene-02" class="clip scene scene-product" data-start="{{SCENE_02_START}}" data-duration="{{SCENE_02_DURATION}}" data-track-index="0">
      <img class="fullbleed image-interior" src="assets/product/orchid-interior.webp" alt="Orchid Elegance installed in a refined interior" />
      <div class="gradient-left"></div>
      <div class="copy product-copy">
        <div class="eyebrow">TEXTURE · DEPTH · QUIET CHARACTER</div>
        <h2>ORCHID<br>ELEGANCE</h2>
        <div class="product-code">DG 818 A-208 PR+</div>
        <p>Woven tactile character for premium interiors.</p>
      </div>
    </section>

    <section id="scene-03" class="clip scene scene-material" data-start="{{SCENE_03_START}}" data-duration="{{SCENE_03_DURATION}}" data-track-index="0">
      <div class="material-grid">
        <div class="panel-wrap"><img class="panel-shot" src="assets/product/orchid-panel.webp" alt="Close-up panel of Orchid Elegance" /></div>
        <div class="material-copy">
          <div class="eyebrow">BUILT TO PERFORM</div>
          <h2>Beauty,<br><em>made practical.</em></h2>
          <div class="spec-line"><span>TEXTURED HPL</span><span>INTERIOR</span></div>
          <div class="benefit-row"><b>Scratch resistant</b><b>Easy to clean</b><b>Durable</b><b>Fade resistant</b></div>
        </div>
      </div>
    </section>

    <section id="scene-04" class="clip scene scene-spec" data-start="{{SCENE_04_START}}" data-duration="{{SCENE_04_DURATION}}" data-track-index="0">
      <img class="texture-fill" src="assets/product/orchid-texture.webp" alt="Orchid Elegance surface texture" />
      <div class="spec-veil"></div>
      <div class="spec-wrap">
        <div class="eyebrow">PROJECT-READY FORMATS</div>
        <h2>Made to move<br>from concept to space.</h2>
        <div class="numbers">
          <div><strong>8 × 4</strong><span>SHEET FORMAT</span></div>
          <div><strong>10 × 4</strong><span>SHEET FORMAT</span></div>
          <div><strong>0.8—1.2</strong><span>MM THICKNESS</span></div>
        </div>
      </div>
    </section>

    <section id="scene-05" class="clip scene scene-application" data-start="{{SCENE_05_START}}" data-duration="{{SCENE_05_DURATION}}" data-track-index="0">
      <img class="fullbleed image-application" src="assets/product/orchid-application.webp" alt="Orchid Elegance applied to furniture" />
      <div class="gradient-bottom"></div>
      <div class="application-copy">
        <div class="eyebrow">DESIGNED FOR INTERIORS</div>
        <h2>Material becomes<br><em>atmosphere.</em></h2>
        <div class="applications"><span>Cabinetry</span><span>Wall cladding</span><span>Furniture</span><span>Offices</span><span>Retail</span><span>Hospitality</span></div>
      </div>
    </section>

    <section id="scene-06" class="clip scene scene-close" data-start="{{SCENE_06_START}}" data-duration="{{SCENE_06_DURATION}}" data-track-index="0">
      <img class="fullbleed image-close" src="assets/product/orchid-hero.webp" alt="Orchid Elegance product panel" />
      <div class="close-veil"></div>
      <div class="close-card">
        <div class="eyebrow">ORCHID ELEGANCE</div>
        <div class="code-large">DG 818 A-208 PR+</div>
        <h2>Surfaces that<br><em>shape the space.</em></h2>
        <div class="brand-lockup">AL AMAAR <span>HPL & WOOD SOLUTIONS</span></div>
      </div>
    </section>

    <audio id="alamaar-voiceover" data-start="0" data-duration="{{DURATION}}" data-track-index="50" data-volume="1" src="assets/audio/{{AUDIO_FILE}}"></audio>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script src="timing-data.js"></script>
  <script src="timeline.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    window.__timelines['alamaar-orchid-elegance-premium'] = window.__ALAMAAR_TIMELINE__;
  </script>
</body>
</html>
