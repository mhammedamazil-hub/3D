/**
 * Deterministic WebGL frame capture.
 *
 * Each frame calls window.setTime(t), which renders synchronously and calls
 * gl.finish(), then Puppeteer screenshots the preserved WebGL drawing buffer.
 * The generated references are loaded by /web/scene.js as actual backplates.
 */
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');
const {startServer} = require('./server.cjs');
const {prepareChromium} = require('./browser.cjs');

const ROOT = path.join(__dirname, '..');
const W = 1280, H = 720;

function parseArgs() {
  const out = {};
  for (const arg of process.argv.slice(2)) {
    const match = /^--([^=]+)=(.*)$/.exec(arg);
    if (match) out[match[1]] = match[2];
  }
  return out;
}

(async () => {
  const a = parseArgs();
  const start = Number(a.start || 1), end = Number(a.end || 5);
  const frames = Number(a.frames || 300);
  const outRoot = path.resolve(a.out || path.join(__dirname, 'frames'));
  if (!(start >= 1 && end >= start && end <= 5 && frames > 0)) {
    throw new Error(`Invalid range: start=${start} end=${end} frames=${frames}`);
  }
  fs.mkdirSync(outRoot, {recursive: true});
  const {exe, args} = await prepareChromium(W, H);
  const server = await startServer(ROOT);
  const port = server.address().port;
  console.log(`[capture ${start}-${end}] server=${port} exe=${exe} frames/shot=${frames} out=${outRoot}`);

  const browser = await puppeteer.launch({
    executablePath: exe, args, headless: 'shell',
    defaultViewport: {width: W, height: H, deviceScaleFactor: 1},
    protocolTimeout: 300000,
  });
  try {
    const page = await browser.newPage();
    page.on('pageerror', e => console.error(`[capture ${start}-${end}] PAGE ERROR:`, e.message));
    page.on('console', m => { if (m.type() === 'error') console.error(`[capture ${start}-${end}] CONSOLE:`, m.text()); });
    await page.goto(`http://127.0.0.1:${port}/web/index.html`, {waitUntil: 'networkidle0', timeout: 120000});
    await page.waitForFunction('window.ready === true || window.error', {timeout: 120000});
    const err = await page.evaluate(() => window.error || null);
    if (err) throw new Error('Scene init failed: ' + err);
    const names = await page.evaluate(() => window.shotNames);
    for (let shot = start; shot <= end; shot++) {
      await page.evaluate(j => window.setShot(j), shot - 1);
      const dir = path.join(outRoot, `scene_${String(shot).padStart(2, '0')}`);
      fs.mkdirSync(dir, {recursive: true});
      const t0 = Date.now();
      for (let f = 0; f < frames; f++) {
        const t = frames === 1 ? 0 : f / (frames - 1);
        await page.evaluate(v => window.setTime(v), t);
        const file = path.join(dir, `${String(f + 1).padStart(4, '0')}.jpg`);
        await page.screenshot({type: 'jpeg', quality: 90, path: file, captureBeyondViewport: false});
        if (f === 0 || (f + 1) % 50 === 0 || f === frames - 1) {
          const elapsed = Date.now() - t0;
          console.log(`[capture ${start}-${end}] ${names[shot - 1]} frame ${f + 1}/${frames} ${elapsed}ms ${((f + 1) / (elapsed / 1000)).toFixed(1)} fps`);
        }
      }
    }
  } finally {
    await browser.close();
    server.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
