const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');
const sharp = require('sharp');
const {startServer} = require('./server.cjs');
const {prepareChromium} = require('./browser.cjs');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'review/five_worlds');
const W = 1280, H = 720;

(async () => {
  fs.mkdirSync(OUT, {recursive: true});
  const {exe, args} = await prepareChromium(W, H);
  const server = await startServer(ROOT);
  const port = server.address().port;
  const browser = await puppeteer.launch({
    executablePath: exe, args, headless: 'shell',
    defaultViewport: {width: W, height: H, deviceScaleFactor: 1},
    protocolTimeout: 180000,
  });
  try {
    const page = await browser.newPage();
    page.on('console', m => console.log('PAGE:', m.text()));
    page.on('pageerror', e => console.log('PAGE ERROR:', e.message));
    await page.goto(`http://127.0.0.1:${port}/web/index.html`, {waitUntil: 'networkidle0', timeout: 90000});
    await page.waitForFunction('window.ready === true || window.error', {timeout: 90000});
    const err = await page.evaluate(() => window.error || null);
    if (err) throw new Error('Scene init failed: ' + err);
    const names = await page.evaluate(() => window.shotNames);
    const spec = await page.evaluate(() => window.spec);
    console.log('SPEC:', JSON.stringify(spec));
    for (let i = 0; i < names.length; i++) {
      await page.evaluate(j => window.setShot(j), i);
      const t0 = Date.now();
      const data = await page.evaluate(() => window.renderAt(0.5));
      const file = path.join(OUT, `shot_${String(i + 1).padStart(2, '0')}.jpg`);
      fs.writeFileSync(file, Buffer.from(data.split(',')[1], 'base64'));
      console.log(names[i], 'rendered in', Date.now() - t0, 'ms ->', file);
    }
  } finally {
    await browser.close();
    server.close();
  }
  const cells = [];
  for (let i = 0; i < 5; i++) {
    const names = require('./shots.json');
    const label = `${String(i + 1).padStart(2, '0')} ${names[i].name}`;
    const svg = Buffer.from(`<svg width="384" height="28"><rect width="384" height="28" fill="rgba(0,0,0,.72)"/><text x="10" y="19" font-family="sans-serif" font-size="14" fill="white">${label}</text></svg>`);
    const buf = await sharp(path.join(OUT, `shot_${String(i + 1).padStart(2, '0')}.jpg`))
      .resize(384, 216, {fit: 'cover'})
      .composite([{input: svg, top: 0, left: 0}])
      .jpeg({quality: 88}).toBuffer();
    cells.push({input: buf, top: Math.floor(i / 3) * 216, left: (i % 3) * 384});
  }
  await sharp({create: {width: 1152, height: 432, channels: 3, background: '#141414'}})
    .composite(cells).jpeg({quality: 90}).toFile(path.join(OUT, 'preview_contact.jpg'));
  console.log('contact:', path.join(OUT, 'preview_contact.jpg'));
})().catch(e => { console.error(e); process.exit(1); });
