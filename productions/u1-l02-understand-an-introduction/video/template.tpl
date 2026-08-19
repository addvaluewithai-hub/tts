<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>U1-L02 · Understand an Introduction</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div id="stage"
    data-composition-id="u1-l02-understand-an-introduction"
    data-start="0"
    data-duration="{{DURATION}}"
    data-fps="30"
    data-width="1920"
    data-height="1080">

    <div id="scene-01" class="clip scene s1" data-start="{{SCENE_01_START}}" data-duration="{{SCENE_01_DURATION}}" data-track-index="0">
      <div class="topline"><span>U1 · LESSON 02</span><b>LISTEN FOR MEANING</b></div>
      <div class="scene-grid intro-grid">
        <section class="copy-block">
          <div class="eyebrow">VOICE MESSAGE</div>
          <h1 class="ar">اسمع عشان <em>تفهم</em>،<br>مش عشان تترجم.</h1>
          <p class="ar sub">أول سؤال في دماغك بسيط جدًا:</p>
          <div class="who-question" data-cue="listen.who"><span>1</span><strong>مين الشخص؟</strong></div>
        </section>
        <section class="voice-card" data-cue="listen.model">
          <div class="voice-head"><div class="avatar alex">A</div><div><small>NEW STUDY GROUP MEMBER</small><strong>Voice message</strong></div><span class="duration-pill">▶</span></div>
          <div class="waveform" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
          <div class="voice-line en">Hi, I'm Alex. I'm from Canada.<br>I live in Cairo. I'm an engineer.</div>
          <div class="listen-note">اسمع مرة كاملة قبل ما تجمع التفاصيل.</div>
        </section>
      </div>
    </div>

    <div id="scene-02" class="clip scene s2" data-start="{{SCENE_02_START}}" data-duration="{{SCENE_02_DURATION}}" data-track-index="0">
      <div class="topline"><span>STEP 01</span><b>WHO IS THE PERSON?</b></div>
      <div class="identity-layout">
        <div class="big-who">WHO<span>?</span></div>
        <div class="identity-card" data-cue="alex.name">
          <div class="avatar alex large">A</div>
          <small>PERSON</small>
          <strong class="en">Alex</strong>
          <p class="ar">الاسم هو أول معلومة نثبتها.</p>
        </div>
        <div class="signal-stack">
          <div class="signal active" data-cue="alex.name"><small>NAME SIGNAL</small><b class="en">I'm Alex.</b></div>
          <div class="signal" data-cue="alex.from"><small>ORIGIN SIGNAL</small><b class="en">I'm from Canada.</b></div>
          <div class="signal" data-cue="alex.lives"><small>HOME SIGNAL</small><b class="en">I live in Cairo.</b></div>
        </div>
      </div>
    </div>

    <div id="scene-03" class="clip scene s3" data-start="{{SCENE_03_START}}" data-duration="{{SCENE_03_DURATION}}" data-track-index="0">
      <div class="topline"><span>STEP 02</span><b>CAPTURE THE FACTS</b></div>
      <div class="profile-summary">
        <div class="profile-title"><div class="avatar alex">A</div><div><small>PROFILE CAPTURED</small><strong>ALEX</strong></div></div>
        <div class="fact-grid">
          <div class="fact filled"><small>PERSON</small><b class="en">Alex</b></div>
          <div class="fact filled"><small>FROM</small><b class="en">Canada</b></div>
          <div class="fact filled"><small>LIVES</small><b class="en">Cairo</b></div>
          <div class="fact role" data-cue="facts.role"><small>ROLE</small><b class="en">Engineer</b></div>
        </div>
      </div>
      <div class="translation-rule"><span class="cross">×</span><p class="ar">مش لازم تترجم الرسالة كلمة كلمة.</p><strong>4 facts are enough.</strong></div>
      <div class="me-lane" data-cue="facts.firstPerson"><small>ABOUT ME</small><b class="en">I'm from Canada.</b><span class="owner-dot">I</span></div>
    </div>

    <div id="scene-04" class="clip scene s4" data-start="{{SCENE_04_START}}" data-duration="{{SCENE_04_DURATION}}" data-track-index="0">
      <div class="topline"><span>STEP 03</span><b>WHO OWNS THE FACT?</b></div>
      <div class="ownership-board">
        <section class="owner-lane me">
          <div class="lane-head"><span>I</span><div><small>SPEAKER</small><strong>about myself</strong></div></div>
          <div class="quote en">I'm from Canada.</div>
          <div class="arrow-down">↓</div>
          <div class="owner-card"><small>FACT BELONGS TO</small><b>THE SPEAKER</b></div>
        </section>
        <div class="versus">≠</div>
        <section class="owner-lane omar" data-cue="omar.model">
          <div class="lane-head"><span>HE</span><div><small>INTRODUCED PERSON</small><strong>Omar</strong></div></div>
          <div class="quote en identity" data-cue="omar.identity">This is Omar.</div>
          <div class="omar-facts">
            <div data-cue="omar.from"><small>FROM</small><b class="en">He's from Egypt.</b></div>
            <div data-cue="omar.lives"><small>LIVES</small><b class="en">He lives in Giza.</b></div>
            <div><small>ROLE</small><b class="en">He's a student.</b></div>
          </div>
          <div class="owner-card"><small>FACTS BELONG TO</small><b>OMAR</b></div>
        </section>
      </div>
    </div>

    <div id="scene-05" class="clip scene s5" data-start="{{SCENE_05_START}}" data-duration="{{SCENE_05_DURATION}}" data-track-index="0">
      <div class="topline"><span>ONE MORE EXAMPLE</span><b>HE / SHE POINT TO THE PERSON</b></div>
      <div class="pronoun-layout">
        <div class="pronoun-card muted"><span>HE</span><small>Omar</small></div>
        <div class="pronoun-card she" data-cue="layla.model"><span>SHE</span><small>Layla</small></div>
        <div class="layla-card">
          <div class="avatar layla">L</div>
          <small>INTRODUCED PERSON</small>
          <b class="en">This is Layla.</b>
          <div class="teacher-fact" data-cue="layla.teacher"><span>ROLE</span><strong class="en">She's a teacher.</strong></div>
        </div>
      </div>
      <div class="summary-rule" data-cue="layla.summary"><span>✓</span><p class="ar">خلي الضمير يساعدك تعرف المعلومة عن مين.</p></div>
    </div>

    <div id="scene-06" class="clip scene s6" data-start="{{SCENE_06_START}}" data-duration="{{SCENE_06_DURATION}}" data-track-index="0">
      <div class="topline"><span>READY FOR LISTENING</span><b>YOUR 3-STEP STRATEGY</b></div>
      <div class="strategy-title"><small>DON'T CHASE EVERY WORD</small><h1 class="ar">اسمع على <em>ثلاث خطوات</em></h1></div>
      <div class="strategy-steps">
        <div class="strategy-step"><span>1</span><small>WHO?</small><b class="ar">مين الشخص؟</b></div>
        <div class="strategy-step"><span>2</span><small>FACTS</small><b class="ar">معلومتين أو ثلاثة</b></div>
        <div class="strategy-step"><span>3</span><small>PRONOUN</small><b class="ar">المعلومة عن مين؟</b></div>
      </div>
      <div class="practice-cta" data-cue="close.practice"><small>NEXT</small><p class="ar">بعد الفيديو هتسمع أصوات جديدة من غير نص مكتوب.</p></div>
      <div class="meaning-cta" data-cue="close.meaning"><strong class="ar">ركّز على المعنى</strong><span>→</span><b>SEE YOU IN PRACTICE</b></div>
    </div>

    <audio id="lesson-voiceover" data-start="0" data-duration="{{DURATION}}" data-track-index="50" data-volume="1" src="assets/audio/{{AUDIO_FILE}}"></audio>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script src="timing-data.js"></script>
  <script src="timeline.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    window.__timelines['u1-l02-understand-an-introduction'] = window.__U1L02_TIMELINE__;
  </script>
</body>
</html>
