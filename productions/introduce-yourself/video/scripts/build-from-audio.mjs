import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(process.cwd());
const JOB_ID = process.env.FACTORY_JOB_ID || 'introduce-yourself';
const TRANSCRIPT = path.join(ROOT, `assets/audio/${JOB_ID}.transcript.json`);
const TEMPLATE = path.join(ROOT, 'template.tpl');

if (!fs.existsSync(TRANSCRIPT)) throw new Error(`Missing ${TRANSCRIPT}`);
if (!fs.existsSync(TEMPLATE)) throw new Error(`Missing ${TEMPLATE}`);

const raw = fs.readFileSync(TRANSCRIPT, 'utf8');
const data = JSON.parse(raw);
const parts = data.parts || [];
const words = data.words || [];

if (data.schema_version !== 2) throw new Error(`Expected TTS transcript schema v2, got ${data.schema_version}`);
if (parts.length !== 9) throw new Error(`Lesson 01 reference expects exactly 9 audio parts, got ${parts.length}`);
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
  throw new Error(`Could not resolve exact word cue for segment ${segmentIndex}: ${phrase} (occurrence ${occurrence})`);
}

const cues = {
  maya: {
    hello: phraseStart(1, "Hi I'm Maya"),
    from: phraseStart(1, "I'm from Jordan"),
    live: phraseStart(1, "I live in Amman"),
    role: phraseStart(1, "I'm a designer"),
    like: phraseStart(1, "I like photography"),
  },
  origin: {
    jordan: phraseStart(2, "I'm from Jordan"),
    egypt: phraseStart(2, "I'm from Egypt"),
    saudi: phraseStart(2, "I'm from Saudi Arabia"),
  },
  contrast: {
    liveAmman: phraseStart(3, "I live in Amman"),
    fromEgypt: phraseStart(3, "I'm from Egypt"),
    liveDubai: phraseStart(3, "I live in Dubai"),
  },
  pronunciation: {
    correct: phraseStart(4, 'live', 1),
    wrong: phraseStart(4, 'live', 2),
    sentence: phraseStart(4, 'I live in Amman'),
  },
  role: {
    designer: phraseStart(5, "I'm a designer"),
    teacher: phraseStart(5, "I'm a teacher"),
    engineer: phraseStart(5, "I'm an engineer"),
    student: phraseStart(5, "I'm a student"),
  },
  interest: {
    photography: phraseStart(6, 'I like photography'),
    reading: phraseStart(6, 'I like reading'),
    football: phraseStart(6, 'I like football'),
    cooking: phraseStart(6, 'I like cooking'),
  },
  omar: {
    hello: phraseStart(7, "Hi I'm Omar"),
    from: phraseStart(7, "I'm from Egypt"),
    live: phraseStart(7, 'I live in Giza'),
    role: phraseStart(7, "I'm a student"),
    like: phraseStart(7, 'I like football'),
    meet: phraseStart(7, 'Nice to meet you'),
  },
  closing: {
    seeYou: phraseStart(8, 'See you there'),
  },
};

const duration = sec(data.duration_ms);
let html = fs.readFileSync(TEMPLATE, 'utf8');
html = html.replaceAll('{{DURATION}}', String(duration));
html = html.replaceAll('{{AUDIO_FILE}}', `${JOB_ID}.wav`);
for (const s of scenes) {
  const n = String(s.index).padStart(2, '0');
  html = html
    .replaceAll(`{{SCENE_${n}_START}}`, String(s.start))
    .replaceAll(`{{SCENE_${n}_DURATION}}`, String(s.duration));
}

fs.writeFileSync(path.join(ROOT, 'index.html'), html);
fs.writeFileSync(
  path.join(ROOT, 'timing-data.js'),
  `window.__V4_TIMING__ = ${JSON.stringify({ duration, scenes, cues, words }, null, 2)};\n`,
);

const finalHolds = scenes.map((s) => Number(Math.max(s.start + 0.2, s.end - 0.65).toFixed(3)));
const safeRisk = (sceneIndex, cue, minVisibleOffset = 0.8) => Number(
  Math.max(cue, scenes[sceneIndex].start + minVisibleOffset).toFixed(3),
);
const riskBeats = [
  safeRisk(1, cues.maya.hello),
  safeRisk(2, cues.origin.saudi),
  safeRisk(3, cues.contrast.liveDubai),
  safeRisk(4, cues.pronunciation.correct),
  safeRisk(4, cues.pronunciation.wrong),
  safeRisk(5, cues.role.engineer),
  safeRisk(6, cues.interest.football),
  safeRisk(7, cues.omar.live),
  safeRisk(8, cues.closing.seeYou),
];

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

console.log(`Built Lesson 01 reference from canonical audio timing: ${duration}s, transcript ${transcriptSha256}`);
