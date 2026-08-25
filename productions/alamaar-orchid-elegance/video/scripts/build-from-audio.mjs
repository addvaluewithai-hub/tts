import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(process.cwd());
const JOB_ID = process.env.FACTORY_JOB_ID || 'alamaar-orchid-elegance';
const TRANSCRIPT = path.join(ROOT, `assets/audio/${JOB_ID}.transcript.json`);
const TEMPLATE = path.join(ROOT, 'template.tpl');

if (!fs.existsSync(TRANSCRIPT)) throw new Error(`Missing ${TRANSCRIPT}`);
if (!fs.existsSync(TEMPLATE)) throw new Error(`Missing ${TEMPLATE}`);

const raw = fs.readFileSync(TRANSCRIPT, 'utf8');
const data = JSON.parse(raw);
const words = data.words || [];
if (data.schema_version !== 2) throw new Error(`Expected transcript schema v2, got ${data.schema_version}`);
if (!Number.isFinite(data.duration_ms) || data.duration_ms <= 0) throw new Error('Invalid duration_ms');

const sec = (ms) => Number((ms / 1000).toFixed(3));
function norm(value) {
  return String(value || '').normalize('NFKD').toLowerCase().match(/[\p{L}\p{N}]+/gu)?.join('') || '';
}
function phraseStart(phrase, occurrence = 0) {
  const target = norm(phrase);
  let seen = 0;
  for (let i = 0; i < words.length; i += 1) {
    let acc = '';
    for (let j = i; j < words.length; j += 1) {
      acc += norm(words[j].text);
      if (acc === target) {
        if (seen === occurrence) return sec(words[i].start_ms);
        seen += 1;
        break;
      }
      if (acc.length > target.length) break;
    }
  }
  throw new Error(`Could not resolve cue: ${phrase}`);
}

const duration = sec(data.duration_ms);
const cues = {
  product: phraseStart('Orchid Elegance by Al Amaar'),
  tactile: phraseStart('woven tactile character'),
  built: phraseStart('Built as premium HPL'),
  available: phraseStart('Available in eight-by-four'),
  applications: phraseStart('For cabinetry wall cladding'),
  close: phraseStart('Al Amaar Surfaces that shape the space'),
};

const starts = [0, cues.product, cues.built, cues.available, cues.applications, cues.close];
const scenes = starts.map((start, index) => {
  const end = index === starts.length - 1 ? duration : starts[index + 1];
  return { index: index + 1, start, end: Number(end.toFixed(3)), duration: Number((end - start).toFixed(3)) };
});

let html = fs.readFileSync(TEMPLATE, 'utf8');
html = html.replaceAll('{{DURATION}}', String(duration)).replaceAll('{{AUDIO_FILE}}', `${JOB_ID}.wav`);
for (const s of scenes) {
  const n = String(s.index).padStart(2, '0');
  html = html.replaceAll(`{{SCENE_${n}_START}}`, String(s.start)).replaceAll(`{{SCENE_${n}_DURATION}}`, String(s.duration));
}
fs.writeFileSync(path.join(ROOT, 'index.html'), html);
fs.writeFileSync(path.join(ROOT, 'timing-data.js'), `window.__ALAMAAR_TIMING__ = ${JSON.stringify({duration, scenes, cues, words}, null, 2)};\n`);

const finalHolds = scenes.map((s) => Number(Math.max(s.start + 0.35, s.end - 0.55).toFixed(3)));
const riskBeats = scenes.map((s) => Number(Math.min(s.end - 0.35, s.start + Math.max(0.8, Math.min(1.8, s.duration * 0.35))).toFixed(3)));
const transcriptSha256 = crypto.createHash('sha256').update(raw).digest('hex');
fs.writeFileSync(path.join(ROOT, 'build-meta.json'), JSON.stringify({schema: 2, duration, transcript_sha256: transcriptSha256, scenes, cues, finalHolds, riskBeats}, null, 2));
console.log(`Built ${JOB_ID}: ${duration}s, ${scenes.length} scenes, transcript ${transcriptSha256}`);
