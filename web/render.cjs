/**
 * Fastest route for this sandbox: two local headless-WebGL capture workers,
 * then local H.264 encoding. No CI queue and no Blender/Cycles rebuild.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {spawn} = require('child_process');
const sharp = require('sharp');
const ffmpeg = require('@ffmpeg-installer/ffmpeg');

const ROOT = path.join(__dirname, '..');
const SHOTS = require('./shots.json');
const FRAME_ROOT = path.join(__dirname, 'frames');
const OUTPUT = path.join(ROOT, 'output');
const REVIEW = path.join(ROOT, 'review/five_worlds');
const DOCS = path.join(ROOT, 'docs');
const FPS = 30, FRAMES = 300, DURATION = 10, W = 1280, H = 720;

function run(command, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {cwd: ROOT, stdio: opts.inherit ? 'inherit' : ['ignore', 'ignore', 'pipe'], ...opts.spawnOptions});
    let err = '';
    if (!opts.inherit && child.stderr) child.stderr.on('data', d => { err += d.toString(); });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolve() : reject(new Error(`${command} exited ${code}: ${err.slice(-4000)}`)));
  });
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function assertFrames() {
  for (const shot of SHOTS) {
    const dir = path.join(FRAME_ROOT, `scene_${String(shot.index).padStart(2, '0')}`);
    const files = fs.readdirSync(dir).filter(f => /^\d{4}\.jpg$/.test(f)).sort();
    if (files.length !== FRAMES) throw new Error(`${dir}: expected ${FRAMES} JPEG frames, found ${files.length}`);
    for (let f = 0; f < FRAMES; f++) {
      const expected = `${String(f + 1).padStart(4, '0')}.jpg`;
      if (files[f] !== expected) throw new Error(`${dir}: missing ${expected}`);
      const size = fs.statSync(path.join(dir, expected)).size;
      if (size < 15000) throw new Error(`${dir}/${expected} is only ${size} bytes`);
    }
    console.log(`[frames] scene ${shot.index}: ${FRAMES} frames OK`);
  }
}

async function encodeShot(shot) {
  const dir = path.join(FRAME_ROOT, `scene_${String(shot.index).padStart(2, '0')}`);
  const out = path.join(ROOT, shot.mp4);
  const args = [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-framerate', String(FPS), '-start_number', '1',
    '-i', path.join(dir, '%04d.jpg'),
    '-frames:v', String(FRAMES), '-an',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
    '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-movflags', '+faststart',
    '-metadata', `title=Five Worlds - ${shot.name}`,
    '-metadata', `comment=Generated reference used as backplate: ${shot.reference}`,
    out,
  ];
  const t0 = Date.now();
  await run(ffmpeg.path, args);
  console.log(`[encode] ${shot.name}: ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
  return out;
}

async function pool(items, limit, fn) {
  const results = new Array(items.length);
  let cursor = 0;
  await Promise.all(Array.from({length: limit}, async () => {
    while (true) {
      const i = cursor++;
      if (i >= items.length) return;
      results[i] = await fn(items[i], i);
    }
  }));
  return results;
}

async function makeCombined(files) {
  const out = path.join(OUTPUT, 'FiveWorlds_AllScenes_720p30_50s.mp4');
  const list = path.join(REVIEW, 'concat.txt');
  // Concat demuxer resolves relative entries against the list file's directory,
  // so use absolute paths here.
  fs.writeFileSync(list, files.map(f => `file '${path.resolve(f).replace(/'/g, "'\\''")}'`).join('\n') + '\n');
  await run(ffmpeg.path, [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-f', 'concat', '-safe', '0', '-i', list,
    '-c', 'copy', '-movflags', '+faststart', out,
  ]);
  console.log('[encode] combined montage ->', out);
  return out;
}

async function makeVideoContact(files) {
  fs.mkdirSync(REVIEW, {recursive: true});
  const cells = [];
  for (let i = 0; i < SHOTS.length; i++) {
    const frame = path.join(REVIEW, `final_frame_${String(i + 1).padStart(2, '0')}.jpg`);
    await run(ffmpeg.path, ['-hide_banner', '-loglevel', 'error', '-y', '-ss', '5', '-i', files[i], '-frames:v', '1', '-q:v', '2', frame]);
    const label = `${String(i + 1).padStart(2, '0')} ${SHOTS[i].name}`;
    const svg = Buffer.from(`<svg width="480" height="32"><rect width="480" height="32" fill="rgba(0,0,0,.74)"/><text x="12" y="22" font-family="sans-serif" font-size="17" fill="white">${label}</text></svg>`);
    const buf = await sharp(frame).resize(480, 270, {fit: 'cover'})
      .composite([{input: svg, top: 0, left: 0}]).jpeg({quality: 88}).toBuffer();
    cells.push({input: buf, top: Math.floor(i / 3) * 270, left: (i % 3) * 480});
  }
  const out = path.join(ROOT, 'assets/references/v6/00_five_worlds_video_contact.jpg');
  await sharp({create: {width: 1440, height: 540, channels: 3, background: '#111111'}})
    .composite(cells).jpeg({quality: 90}).toFile(out);
  console.log('[contact] ->', out);
  return out;
}

async function main() {
  fs.mkdirSync(OUTPUT, {recursive: true});
  fs.mkdirSync(REVIEW, {recursive: true});
  fs.mkdirSync(DOCS, {recursive: true});
  const encodeOnly = process.argv.includes('--encode-only');
  const metaPath = path.join(FRAME_ROOT, 'capture_meta.json');
  const started = Date.now();
  let captureSeconds = 0, totalSeconds = 0, captureMeta = {};
  if (!encodeOnly) {
    console.log('[render] launching two local WebGL capture workers (scenes 1-3 and 4-5)');
    await Promise.all([
      run(process.execPath, ['capture.cjs', '--start=1', '--end=3', `--frames=${FRAMES}`], {inherit: true, spawnOptions: {cwd: __dirname}}),
      run(process.execPath, ['capture.cjs', '--start=4', '--end=5', `--frames=${FRAMES}`], {inherit: true, spawnOptions: {cwd: __dirname}}),
    ]);
    captureSeconds = (Date.now() - started) / 1000;
    captureMeta = {
      captured_at_utc: new Date().toISOString(),
      workers: 2, frames_per_scene: FRAMES,
      capture_wall_clock_seconds: Number(captureSeconds.toFixed(2)),
    };
    fs.writeFileSync(metaPath, JSON.stringify(captureMeta, null, 2) + '\n');
  } else {
    if (!fs.existsSync(metaPath)) throw new Error(`--encode-only needs ${metaPath}`);
    captureMeta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    captureSeconds = Number(captureMeta.capture_wall_clock_seconds || 0);
    console.log(`[render] encode-only: reusing ${FRAMES} captured frames per scene`);
  }
  assertFrames();
  const files = await pool(SHOTS, 2, encodeShot);
  const combined = await makeCombined(files);
  const contact = await makeVideoContact(files);
  if (!encodeOnly) {
    totalSeconds = (Date.now() - started) / 1000;
    captureMeta.total_wall_clock_seconds = Number(totalSeconds.toFixed(2));
    fs.writeFileSync(metaPath, JSON.stringify(captureMeta, null, 2) + '\n');
  } else {
    totalSeconds = Number(captureMeta.total_wall_clock_seconds || (captureSeconds + (Date.now() - started) / 1000));
  }

  const scenes = SHOTS.map((shot, i) => ({
    index: shot.index, name: shot.name, slug: shot.slug,
    reference: shot.reference, reference_original: shot.reference_original,
    reference_sha256: sha256(path.join(ROOT, shot.reference)),
    motion: shot.motion,
    mp4: shot.mp4,
    bytes: fs.statSync(files[i]).size,
    sha256: sha256(files[i]),
    frames: FRAMES, fps: FPS, duration_seconds: DURATION,
  }));
  const receipt = {
    revision: 'five-worlds-v1-reference-driven-webgl',
    generated_at_utc: new Date().toISOString(),
    route: {
      selected: 'in-sandbox Three.js/WebGL + Puppeteer screenshot capture + local ffmpeg',
      why_fastest: 'No GitHub Actions queue; no Blender/Python environment rebuild; 1500 deterministic 720p WebGL frames render and encode locally on two workers.',
      alternatives: {
        github_actions: 'Rejected: prior 15-shard CPU render took roughly 78 minutes.',
        blender_in_sandbox: 'Rejected: Blender Python environment was absent after workspace refresh; Cycles is CPU-only and slower.',
      },
    },
    spec: {width: W, height: H, fps: FPS, frames_per_scene: FRAMES, duration_seconds: DURATION, scenes: 5, total_duration_seconds: 50, codec: 'H.264 / yuv420p', encoder: 'libx264 CRF 19'},
    toolchain: {
      node: process.version,
      three: require('./package.json').dependencies.three,
      puppeteer_core: require('./package.json').dependencies['puppeteer-core'],
      chromium: require('./package.json').dependencies['@sparticuz/chromium'],
      sharp: require('./package.json').dependencies.sharp,
      ffmpeg: ffmpeg.version,
    },
    capture: {workers: 2, wall_clock_seconds: Number(captureSeconds.toFixed(2)), total_wall_clock_seconds: Number(totalSeconds.toFixed(2)), frame_root: 'web/frames (ignored, regenerable)', method: 'window.setTime(t) + gl.finish() + Puppeteer JPEG screenshot'},
    reference_usage: 'Each 1280x720 generated reference is loaded as the actual Three.js backplate texture and again as a rippled reflection plane; references are also shimmered with a scene-specific UV shader.',
    contact_sheet: path.relative(ROOT, contact),
    combined_mp4: path.relative(ROOT, combined),
    combined_bytes: fs.statSync(combined).size,
    combined_sha256: sha256(combined),
    scenes,
  };
  const receiptPath = path.join(DOCS, 'FIVE_WORLDS_RECEIPT.json');
  fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n');
  console.log('[receipt] ->', receiptPath);
  console.log(`[done] ${totalSeconds.toFixed(1)}s total, ${scenes.length} x ${DURATION}s MP4s + 50s montage`);
}

main().catch(e => { console.error(e); process.exit(1); });
