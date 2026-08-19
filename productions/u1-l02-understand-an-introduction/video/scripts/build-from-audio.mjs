import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(process.cwd());
const JOB_ID = process.env.FACTORY_JOB_ID || 'u1-l02-understand-an-introduction';
const TRANSCRIPT = path.join(ROOT, `assets/audio/${JOB_ID}.transcript.json`);
const TEMPLATE = path.join(ROOT, 'template.tpl');

if (!fs.existsSync(TRANSCRIPT)) throw new Error(`Missing ${TRANSCRIPT}`);
if (!fs.existsSync(TEMPLATE)) throw new Error(`Missing ${TEMPLATE}`);

const raw = fs.readFileSync(TRANSCRIPT, 'utf8');
const data = JSON.parse(raw);
const parts = data.parts || [];
const words = data.words || [];

if (data.schema_version !== 2) throw new Error(`Expected transcript schema v2, got ${data.schema_version}`);
if (parts.length !== 6) throw new Error(`U1-L02 expects 6 authored audio parts, got ${parts.length}`);
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

function phraseStart(segmentIndex, phrase, occurrence = 0) {
  const target = norm(phrase);
  const segmentWords = words.filter((w) => Number(w.segment_index) === segmentIndex);
  let seen = 0;
  for (let i = 0; i < segmentWords.length; i += 1) {
    let acc = '';
    for (let j = i; j < segmentWords.length; j += 1) {
      acc += norm(segmentWords[j].text);
      if (acc === target) {
        if (seen === occurrence) return sec(segmentWords[i].start_ms);
        seen += 1;
        break;
      }
      if (acc.length > target.length) break;
    }
  }
  throw new Error(`Could not resolve word cue in segment ${segmentIndex}: ${phrase} (occurrence ${occurrence})`);
}

const cues = {
  listen: {
    model: phraseStart(0, "Hi I'm Alex"),
    who: phraseStart(0, 'مين الشخص'),
  },
  alex: {
    name: phraseStart(1, "I'm Alex"),
    from: phraseStart(1, "I'm from Canada"),
    lives: phraseStart(1, 'I live in Cairo'),
  },
  facts: {
    role: phraseStart(2, "I'm an engineer"),
    alex: phraseStart(2, 'Alex'),
    canada: phraseStart(2, 'Canada'),
    cairo: phraseStart(2, 'Cairo'),
    engineer: phraseStart(2, 'engineer'),
    firstPerson: phraseStart(2, "I'm from Canada"),
  },
  omar: {
    model: phraseStart(3, 'This is Omar'),
    identity: phraseStart(3, 'This is Omar', 1),
    from: phraseStart(3, "He's from Egypt", 1),
    lives: phraseStart(3, 'He lives in Giza', 1),
    finalName: phraseStart(3, 'Omar', 3),
  },
  layla: {
    model: phraseStart(4, 'This is Layla'),
    teacher: phraseStart(4, "She's a teacher"),
    summary: phraseStart(4, 'الخلاصة بسيطة'),
  },
  close: {
    practice: phraseStart(5, 'بعد الفيديو'),
    meaning: phraseStart(5, 'ركز على المعنى'),
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
  `window.__U1L02_TIMING__ = ${JSON.stringify({ duration, scenes, cues, words }, null, 2)};\n`,
);

const finalHolds = scenes.map((s) => Number(Math.max(s.start + 0.25, s.end - 0.7).toFixed(3)));
const safeRisk = (sceneIndex, cue, offset = 0.8) => Number(
  Math.max(cue, scenes[sceneIndex].start + offset).toFixed(3),
);
const riskBeats = [
  safeRisk(0, cues.listen.model),
  safeRisk(0, cues.listen.who),
  safeRisk(1, cues.alex.name),
  safeRisk(1, cues.alex.lives),
  safeRisk(2, cues.facts.engineer),
  safeRisk(2, cues.facts.firstPerson),
  safeRisk(3, cues.omar.identity),
  safeRisk(3, cues.omar.lives),
  safeRisk(4, cues.layla.teacher),
  safeRisk(4, cues.layla.summary),
  safeRisk(5, cues.close.meaning),
];

const transcriptSha256 = crypto.createHash('sha256').update(raw).digest('hex');
const meta = {
  schema: 2,
  job: JOB_ID,
  duration,
  transcript_sha256: transcriptSha256,
  scenes,
  cues,
  finalHolds,
  riskBeats,
};
fs.writeFileSync(path.join(ROOT, 'build-meta.json'), JSON.stringify(meta, null, 2));
console.log(`Built U1-L02 from canonical audio timing: ${duration}s, transcript ${transcriptSha256}`);
