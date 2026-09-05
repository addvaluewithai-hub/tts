import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(process.cwd());
const JOB_ID = process.env.FACTORY_JOB_ID || 'airline-overbooking-explainer-v2';
const TRANSCRIPT = path.join(ROOT, `assets/audio/${JOB_ID}.transcript.json`);
const TEMPLATE = path.join(ROOT, 'template.tpl');
const INFO_SCENES = path.join(ROOT, 'info-scenes.json');
const VISUALS = path.resolve(ROOT, `../../../input/${JOB_ID}/visuals.json`);

for (const required of [TRANSCRIPT, TEMPLATE, INFO_SCENES, VISUALS]) {
  if (!fs.existsSync(required)) throw new Error(`Missing required V3 source: ${required}`);
}

const rawTranscript = fs.readFileSync(TRANSCRIPT, 'utf8');
const transcript = JSON.parse(rawTranscript);
const visualPlan = JSON.parse(fs.readFileSync(VISUALS, 'utf8'));
const infoPlan = JSON.parse(fs.readFileSync(INFO_SCENES, 'utf8'));
const words = transcript.words || [];

if (transcript.schema_version !== 2) {
  throw new Error(`Expected transcript schema v2, got ${transcript.schema_version}`);
}
if (!Number.isFinite(transcript.duration_ms) || transcript.duration_ms <= 0) {
  throw new Error('Invalid transcript duration_ms');
}
if (!Array.isArray(words) || words.length < 50) {
  throw new Error('V3 requires complete word-level timing; transcript.words is missing/incomplete');
}
if (!Array.isArray(visualPlan.requests) || visualPlan.requests.length < 30) {
  throw new Error(`V3 requires at least 30 generated-image shots, got ${visualPlan.requests?.length || 0}`);
}
if (!Array.isArray(infoPlan.scenes) || !infoPlan.scenes.length) {
  throw new Error('Missing separate HTML information scene plan');
}

const sec = (ms) => Number((ms / 1000).toFixed(3));
const duration = sec(transcript.duration_ms);

function norm(value) {
  return String(value || '')
    .normalize('NFKD')
    .toLowerCase()
    .match(/[\p{L}\p{N}]+/gu)?.join('') || '';
}

function matchingStarts(phrase, segmentOneBased = null) {
  const target = norm(phrase);
  if (!target) throw new Error(`Empty anchor phrase: ${phrase}`);
  const candidates = words
    .map((word, index) => ({ ...word, __index: index }))
    .filter((word) => segmentOneBased == null || Number(word.segment_index) === segmentOneBased - 1);

  const matches = [];
  for (let i = 0; i < candidates.length; i += 1) {
    let acc = '';
    for (let j = i; j < candidates.length; j += 1) {
      // Never bridge across audio parts when globally matching.
      if (Number(candidates[j].segment_index) !== Number(candidates[i].segment_index)) break;
      acc += norm(candidates[j].text);
      if (acc === target) {
        matches.push(sec(candidates[i].start_ms));
        break;
      }
      if (acc.length > target.length) break;
    }
  }
  return matches;
}

function resolveAnchor(anchor, segmentOneBased = null) {
  const matches = matchingStarts(anchor, segmentOneBased);
  if (matches.length !== 1) {
    throw new Error(
      `Anchor must resolve exactly once: ${JSON.stringify(anchor)} ` +
      `(segment=${segmentOneBased ?? 'any'}, matches=${JSON.stringify(matches)})`,
    );
  }
  return matches[0];
}

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

const imageScenes = visualPlan.requests.map((request, index) => {
  if (!request.anchor) throw new Error(`Image request ${request.id || index + 1} is missing anchor`);
  return {
    id: request.id || `img${String(index + 1).padStart(2, '0')}`,
    mode: 'image',
    anchor: request.anchor,
    start: resolveAnchor(request.anchor),
    asset: `assets/images/${String(index + 1).padStart(2, '0')}.png`,
    motion: ['push-left', 'push-right', 'push-up', 'push-down'][index % 4],
    sourceIndex: index + 1,
  };
});

const informationScenes = infoPlan.scenes.map((scene) => ({
  ...scene,
  mode: scene.mode || 'text',
  start: resolveAnchor(scene.anchor, Number(scene.segment)),
}));

const scenes = [...imageScenes, ...informationScenes]
  .sort((a, b) => a.start - b.start || (a.mode === 'image' ? -1 : 1))
  .map((scene, index, sorted) => {
    const end = index + 1 < sorted.length ? sorted[index + 1].start : duration;
    const sceneDuration = Number((end - scene.start).toFixed(3));
    if (sceneDuration < 0.12) {
      throw new Error(`Scene ${scene.id} is too short after exact anchor resolution: ${sceneDuration}s`);
    }
    return {
      ...scene,
      index: index + 1,
      domId: `scene-${String(index + 1).padStart(2, '0')}`,
      end: Number(end.toFixed(3)),
      duration: sceneDuration,
    };
  });

function patternMarkup() {
  return '<div class="pattern-layer" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>';
}

function infoMarkup(scene) {
  const middle = scene.middle
    ? `<div class="info-middle">${esc(scene.middle)}</div>`
    : '';
  return `
    ${patternMarkup()}
    <div class="info-content variant-${esc(scene.variant || 'default')}">
      <div class="info-headline">${esc(scene.headline || '')}</div>
      ${middle}
      <div class="info-subline">${esc(scene.subline || '')}</div>
    </div>`;
}

function sceneMarkup(scene) {
  const common = `id="${scene.domId}" class="clip scene ${scene.mode}-scene pattern-${esc(scene.pattern || 'none')}" data-start="${scene.start}" data-duration="${scene.duration}" data-track-index="0" data-scene-mode="${scene.mode}"`;
  if (scene.mode === 'image') {
    return `<div ${common}>
      <div class="image-shell ${esc(scene.motion)}"><img src="${esc(scene.asset)}" alt="" /></div>
    </div>`;
  }
  return `<div ${common}>${infoMarkup(scene)}</div>`;
}

const sceneHtml = scenes.map(sceneMarkup).join('\n');
let html = fs.readFileSync(TEMPLATE, 'utf8');
html = html
  .replaceAll('{{DURATION}}', String(duration))
  .replaceAll('{{AUDIO_FILE}}', `${JOB_ID}.wav`)
  .replaceAll('{{SCENES_HTML}}', sceneHtml);
fs.writeFileSync(path.join(ROOT, 'index.html'), html);

const timingPayload = {
  schema: 3,
  compositionId: 'airline-overbooking-v3',
  duration,
  scenes,
  words,
};
fs.writeFileSync(
  path.join(ROOT, 'timing-data.js'),
  `window.__AIRLINE_TIMING__ = ${JSON.stringify(timingPayload, null, 2)};\n`,
);

const riskScenes = scenes.filter((scene) => scene.mode !== 'image');
const imageCheckpoints = scenes.filter((scene) => scene.mode === 'image' && scene.sourceIndex % 3 === 1);
const finalHolds = [...riskScenes, ...imageCheckpoints]
  .sort((a, b) => a.start - b.start)
  .map((scene) => Number(Math.min(scene.end - 0.08, scene.start + Math.max(0.12, scene.duration * 0.62)).toFixed(3)));
const riskBeats = riskScenes.map((scene) => Number((scene.start + Math.min(0.2, scene.duration * 0.15)).toFixed(3)));

const transcriptSha256 = crypto.createHash('sha256').update(rawTranscript).digest('hex');
const meta = {
  schema: 3,
  duration,
  transcript_sha256: transcriptSha256,
  timing_source: 'word-level-transcript-required',
  generated_image_count: imageScenes.length,
  information_scene_count: informationScenes.length,
  scenes: scenes.map(({ words: ignored, ...scene }) => scene),
  finalHolds,
  riskBeats,
};
fs.writeFileSync(path.join(ROOT, 'build-meta.json'), JSON.stringify(meta, null, 2));

console.log(
  `Built airline overbooking V3: ${duration}s, ${imageScenes.length} images + ` +
  `${informationScenes.length} separate HTML scenes, transcript ${transcriptSha256}`,
);
