const path = require('path');
const chromiumMod = require('@sparticuz/chromium');
const Chromium = chromiumMod.default;

/** Inflate the headless Chromium runtime and its non-Lambda libraries. */
async function prepareChromium(width = 1280, height = 720) {
  const binDir = path.join(__dirname, 'node_modules/@sparticuz/chromium/bin');
  await Chromium.executablePath(binDir);
  // AL2023 NSS/NSPR and SwiftShader are not auto-detected outside AWS Lambda.
  await chromiumMod.inflate(path.join(binDir, 'al2023.tar.br'));
  await chromiumMod.inflate(path.join(binDir, 'swiftshader.tar.br'));
  chromiumMod.setupLambdaEnvironment('/tmp/al2023/lib');
  const exe = await Chromium.executablePath();
  const args = Chromium.args.filter(a => !a.startsWith('--headless'));
  args.push('--disable-dev-shm-usage', `--window-size=${width},${height}`);
  return {exe, args};
}

module.exports = {prepareChromium};
