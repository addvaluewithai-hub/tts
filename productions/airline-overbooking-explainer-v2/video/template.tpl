<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Why Airlines Sell More Tickets Than Seats</title>
  <style>
    /* HyperFrames needs every named family declared deterministically. */
    @font-face {
      font-family: "Aptos";
      src: local("Aptos");
      font-style: normal;
      font-weight: 100 900;
      font-display: swap;
    }
  </style>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div id="stage"
    data-composition-id="airline-overbooking-v3"
    data-start="0"
    data-duration="{{DURATION}}"
    data-fps="30"
    data-width="1920"
    data-height="1080">

    {{SCENES_HTML}}

    <audio
      id="voiceover"
      data-start="0"
      data-duration="{{DURATION}}"
      data-track-index="50"
      data-volume="1"
      src="assets/audio/{{AUDIO_FILE}}"></audio>
  </div>

  <script>
    /* Static HyperFrames contract. timeline.js replaces this placeholder with
       the real paused GSAP timeline after it is constructed. */
    window.__timelines = window.__timelines || {};
    window.__timelines['airline-overbooking-v3'] = null;
  </script>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script src="timing-data.js"></script>
  <script src="timeline.js"></script>
</body>
</html>