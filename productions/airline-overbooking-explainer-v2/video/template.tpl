<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Why Airlines Sell More Tickets Than Seats</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div id="stage"
    data-composition-id="airline-overbooking-v2"
    data-start="0"
    data-duration="{{DURATION}}"
    data-fps="30"
    data-width="1920"
    data-height="1080">

    <div id="scene-01" class="clip scene s1" data-start="{{SCENE_01_START}}" data-duration="{{SCENE_01_DURATION}}" data-track-index="0">
      <img class="shot img-a" src="assets/images/01.png" alt="" />
      <img class="shot img-b" src="assets/images/02.png" alt="" />
      <div class="shade"></div>
      <div class="seat-count"><strong>180</strong><span>SEATS</span></div>
      <div class="ticket-count"><strong>185</strong><span>TICKETS</span></div>
      <div class="ticket-stack" aria-hidden="true"><i>181</i><i>182</i><i>183</i><i>184</i><i>185</i></div>
      <div class="punch kindergarten">No, nobody failed kindergarten.</div>
      <div class="zero-card"><small>AFTER DEPARTURE</small><b>$0</b><span>EMPTY SEAT VALUE</span></div>
    </div>

    <div id="scene-02" class="clip scene s2" data-start="{{SCENE_02_START}}" data-duration="{{SCENE_02_DURATION}}" data-track-index="0">
      <img class="shot img-a" src="assets/images/03.png" alt="" />
      <img class="shot img-b" src="assets/images/04.png" alt="" />
      <div class="shade"></div>
      <div class="eyebrow">REVENUE FORECAST</div>
      <div class="forecast-line"><span>185 BOOKINGS</span><b>→</b><span>~5 NO-SHOWS</span><b>→</b><span>180 HUMANS</span></div>
      <div class="prob-dots" aria-hidden="true"></div>
      <div class="punch promotion">The spreadsheet gets a tiny promotion.</div>
    </div>

    <div id="scene-03" class="clip scene s3" data-start="{{SCENE_03_START}}" data-duration="{{SCENE_03_DURATION}}" data-track-index="0">
      <img class="shot img-a" src="assets/images/04.png" alt="" />
      <img class="shot img-b" src="assets/images/05.png" alt="" />
      <div class="shade strong"></div>
      <div class="eyebrow">LET'S RUN THE SAME 185 BOOKINGS</div>
      <div class="sim sim-seven"><small>7 NO-SHOWS</small><strong>178 / 180</strong><span>2 empty seats</span></div>
      <div class="sim sim-five"><small>5 NO-SHOWS</small><strong>180 / 180</strong><span>math looks genius</span></div>
      <div class="sim sim-zero"><small>0 NO-SHOWS</small><strong>185 / 180</strong><span>uh-oh</span></div>
      <div class="punch statistical">statistical error has entered the chat.</div>
      <div class="auction-label">A calm announcement now sounds like an auction.</div>
    </div>

    <div id="scene-04" class="clip scene s4" data-start="{{SCENE_04_START}}" data-duration="{{SCENE_04_DURATION}}" data-track-index="0">
      <img class="shot img-a" src="assets/images/06.png" alt="" />
      <img class="shot img-b" src="assets/images/07.png" alt="" />
      <div class="shade"></div>
      <div class="eyebrow">PRESSURE-RELEASE VALVE</div>
      <div class="volunteer-title">WHO WANTS A LATER FLIGHT?</div>
      <div class="offer"><small>OFFER</small><strong>$200</strong></div>
      <div class="offer offer-two"><small>OFFER</small><strong>$400</strong></div>
      <div class="us-note">U.S.: seek volunteers before involuntary denied boarding due to oversales.</div>
      <div class="punch destination">Suddenly somebody remembers<br>they never liked this destination anyway.</div>
    </div>

    <div id="scene-05" class="clip scene s5" data-start="{{SCENE_05_START}}" data-duration="{{SCENE_05_DURATION}}" data-track-index="0">
      <img class="shot half left-img" src="assets/images/08.png" alt="" />
      <img class="shot half right-img" src="assets/images/09.png" alt="" />
      <div class="shade split"></div>
      <div class="eyebrow">THE REAL OPTIMIZATION</div>
      <div class="cost cost-one"><small>COST ONE</small><strong>EMPTY SEAT</strong><span>leaves → value disappears</span></div>
      <div class="cost cost-two"><small>COST TWO</small><strong>TOO MANY PEOPLE</strong><span>airline pays to fix it</span></div>
      <div class="balance"><i></i><b></b><i></i></div>
      <div class="goal">Not “sell as many as possible.”<br><strong>Sell just enough extra.</strong></div>
    </div>

    <div id="scene-06" class="clip scene s6" data-start="{{SCENE_06_START}}" data-duration="{{SCENE_06_DURATION}}" data-track-index="0">
      <img class="shot img-a" src="assets/images/10.png" alt="" />
      <div class="shade"></div>
      <div class="eyebrow">THE NUMBER CHANGES WITH THE FLIGHT</div>
      <div class="route-card business"><small>MONDAY · 7:00 AM</small><strong>BUSINESS ROUTE</strong></div>
      <div class="route-card holiday"><small>HOLIDAY WEEKEND</small><strong>LEISURE FLIGHT</strong></div>
      <div class="data-row"><span>DEMAND</span><span>BOOKING BEHAVIOR</span><span>CANCELLATIONS</span><span>NO-SHOW HISTORY</span></div>
      <div class="rule-card"><strong>FORECAST ≠ RULE</strong><span>Some airlines don't oversell at all.</span></div>
    </div>

    <div id="scene-07" class="clip scene s7" data-start="{{SCENE_07_START}}" data-duration="{{SCENE_07_DURATION}}" data-track-index="0">
      <img class="shot img-a" src="assets/images/11.png" alt="" />
      <img class="shot img-b" src="assets/images/12.png" alt="" />
      <div class="shade"></div>
      <div class="weird">Airlines aren't really selling chairs.</div>
      <div class="probability">They're managing <strong>probabilities</strong> around chairs.</div>
      <div class="seat22"><small>YOUR SEAT</small><strong>22A</strong></div>
      <div class="question">How many booked humans<br>will actually appear at the gate?</div>
      <div class="final-line">They didn't forget to count.<br><strong>They counted the people they expect not to show up.</strong></div>
    </div>

    <audio id="voiceover" data-start="0" data-duration="{{DURATION}}" data-track-index="50" data-volume="1" src="assets/audio/{{AUDIO_FILE}}"></audio>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script src="timing-data.js"></script>
  <script src="timeline.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    window.__timelines['airline-overbooking-v2'] = window.__AIRLINE_TIMELINE__;
  </script>
</body>
</html>
