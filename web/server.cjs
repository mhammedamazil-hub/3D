const fs = require('fs');
const path = require('path');
const http = require('http');

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.wasm': 'application/wasm', '.map': 'application/json; charset=utf-8',
};

/** Minimal static server for the Three.js scene and its reference textures. */
function startServer(root) {
  const server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
    const rel = pathname === '/' ? '/web/index.html' : pathname;
    const file = path.resolve(root, '.' + rel);
    if (!file.startsWith(root + path.sep)) {
      res.writeHead(403); res.end('forbidden'); return;
    }
    fs.stat(file, (err, st) => {
      if (err || !st.isFile()) { res.writeHead(404); res.end('not found'); return; }
      res.writeHead(200, {'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream'});
      if (req.method === 'HEAD') { res.end(); return; }
      fs.createReadStream(file).pipe(res);
    });
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}

module.exports = {startServer};
