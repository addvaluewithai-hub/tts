import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(process.cwd());
const JOB_ID = process.env.FACTORY_JOB_ID || 'airline-overbooking-explainer-v2';
const TRANSCRIPT = path.join(ROOT, `assets/audio/${JOB_ID}.transcript.json`);
const TEMPLATE = path.join(ROOT, 'template.tpl');

if (!fs.existsSync(TRANSCRIPT)) throw new Error(`Missing ${TRANSCRIPT}`);
if (!fs.existsSync(TEMPLATE)) throw new Error(`Missing ${TEMPLATE}`);

const raw = fs.readFileSync(TRANSCRIPT, 'utf8');
const data = JSON.parse(raw);
const parts = data.parts || [];
const words = data.words || [];
if (data.schema_version !== 2) throw new Error(`Expected transcript schema v2, got ${data.schema_version}`);
if (parts.length !== 7) throw new Error(`Airline V2 expects 7 audio parts, got ${parts.length}`);
if (!Number.isFinite(data.duration_ms) || data.duration_ms <= 0) throw new Error('Invalid duration_ms');

const sec = (ms) => Number((ms / 1000).toFixed(3));
const scenes = parts.map((p, i) => ({
  index: i + 1,
  file: p.file,
  start: sec(p.start_ms),
  end: sec(p.end_ms),
  duration: sec(p.end_ms - p.start_ms),
}));

function norm(value) {
  return String(value || '')
    .normalize('NFKD')
    .toLowerCase()
    .match(/[\p{L}\p{N}]+/gu)?.join('') || '';
}

function phraseStart(segmentIndex, phrase, fallbackOffset = 0.8) {
  const target = norm(phrase);
  const segmentWords = words.filter((w) => Number(w.segment_index) === segmentIndex);
  for (let i = 0; i < segmentWords.length; i += 1) {
    let acc = '';
    for (let j = i; j < segmentWords.length; j += 1) {
      acc += norm(segmentWords[j].text);
      if (acc === target) return sec(segmentWords[i].start_ms);
      if (acc.length > target.length) break;
    }
  }
  const fallback = Number((scenes[segmentIndex - 1].start + fallbackOffset).toFixed(3));
  console.warn(`Cue fallback for segment ${segmentIndex}: ${phrase} -> ${fallback}s`);
  return fallback;
}

const cues = {
  hook: {
    seats: phraseStart(1, 'Your plane has 180 seats', 0.25),
    tickets: phraseStart(1, 'The airline sells 185 tickets', 1.9),
    kindergarten: phraseStart(1, 'No nobody failed kindergarten', 3.9),
    zero: phraseStart(1, 'it becomes worth exactly zero', Math.max(1, scenes[0].duration - 3.2)),
  },
  forecast: {
    model: phraseStart(2, "forecast how many booked passengers probably won't board", 1.0),
    five: phraseStart(2, 'expects about five no-shows', 5.0),
    humans: phraseStart(2, '180 actual humans', 8.0),
    promotion: phraseStart(2, 'The spreadsheet gets a tiny promotion', Math.max(1, scenes[1].duration - 2.8)),
  },
  simulation: {
    seven: phraseStart(3, 'If seven people vanish', 1.5),
    five: phraseStart(3, 'If exactly five disappear', 4.5),
    nobody: phraseStart(3, 'if nobody disappears', 7.5),
    auction: phraseStart(3, 'starts sounding like an auction', Math.max(1, scenes[2].duration - 3.2)),
  },
  volunteers: {
    ask: phraseStart(4, 'ask for volunteers', 0.8),
    us: phraseStart(4, 'In the United States', 4.3),
    two: phraseStart(4, 'two hundred dollars', 9.0),
    four: phraseStart(4, 'four hundred', 10.5),
    destination: phraseStart(4, 'never liked this destination anyway', Math.max(1, scenes[3].duration - 3.0)),
  },
  tradeoff: {
    twoCosts: phraseStart(5, 'balancing two costs', 1.2),
    one: phraseStart(5, 'Cost one', 3.0),
    two: phraseStart(5, 'Cost two', 6.0),
    goal: phraseStart(5, 'The goal is not', 9.0),
  },
  routes: {
    monday: phraseStart(6, 'A Monday morning business route', 1.4),
    holiday: phraseStart(6, 'holiday flight', 4.0),
    some: phraseStart(6, "Some airlines don't oversell at all", Math.max(1, scenes[5].duration - 4.2)),
    rule: phraseStart(6, 'The system is a forecast not a rule', Math.max(1, scenes[5].duration - 2.5)),
  },
  close: {
    weird: phraseStart(7, 'So the weird truth is this', 0.4),
    seat: phraseStart(7, 'Your 22A', 4.5),
    forgot: phraseStart(7, "Airlines don't overbook because they forgot to count", 8.5),
    counted: phraseStart(7, 'they counted everyone', Math.max(1, scenes[6].duration - 4.2)),
  },
};

const duration = sec(data.duration_ms);
let html = fs.readFileSync(TEMPLATE, 'utf8');
html = html.replaceAll('{{DURATION}}', String(duration));
html = html.replaceAll('{{AUDIO_FILE}}', `${JOB_ID}.wav`);
for (const scene of scenes) {
  const n = String(scene.index).padStart(2, '0');
  html = html
    .replaceAll(`{{SCENE_${n}_START}}`, String(scene.start))
    .replaceAll(`{{SCENE_${n}_DURATION}}`, String(scene.duration));
}
fs.writeFileSync(path.join(ROOT, 'index.html'), html);
fs.writeFileSync(
  path.join(ROOT, 'timing-data.js'),
  `window.__AIRLINE_TIMING__ = ${JSON.stringify({ duration, scenes, cues, words }, null, 2)};\n`,
);

const finalHolds = scenes.map((s) => Number(Math.max(s.start + 0.35, s.end - 0.7).toFixed(3)));
const riskBeats = [
  cues.hook.kindergarten,
  cues.hook.zero,
  cues.forecast.promotion,
  cues.simulation.nobody,
  cues.simulation.auction,
  cues.volunteers.four,
  cues.volunteers.destination,
  cues.tradeoff.one,
  cues.tradeoff.two,
  cues.routes.rule,
  cues.close.seat,
  cues.close.counted,
].map((v) => Number(v.toFixed(3)));

const transcriptSha256 = crypto.createHash('sha256').update(raw).digest('hex');
const meta = {
  schema: 2,
  duration,
  transcript_sha256: transcriptSha256,
  scenes,
  cues,
  finalHolds,
  riskBeats,
};
fs.writeFileSync(path.join(ROOT, 'build-meta.json'), JSON.stringify(meta, null, 2));
console.log(`Built airline overbooking V2: ${duration}s, transcript ${transcriptSha256}`);
