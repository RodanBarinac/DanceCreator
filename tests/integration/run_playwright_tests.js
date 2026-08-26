// Minimal Playwright runner that launches a static HTTP server and checks preview
import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';

const port = 8081;
const root = path.resolve(process.cwd());

function serveOnce(req, res) {
  let p = path.join(root, req.url.split('?')[0]);
  if (req.url === '/') p = path.join(root, 'templates', 'gui_ArbeitsVersion.html');
  fs.readFile(p, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200);
    res.end(data);
  });
}

(async ()=>{
  const server = http.createServer(serveOnce).listen(port);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(`http://localhost:${port}/`);
  // wait for svg to appear
  await page.waitForSelector('#floor-preview svg', { timeout: 5000 });
  const circles = await page.$$eval('#floor-preview svg circle', els => els.length);
  const rects = await page.$$eval('#floor-preview svg rect', els => els.length);
  console.log('circles', circles, 'rects', rects);
  if (circles < 1 || rects < 1) process.exitCode = 2;
  await browser.close();
  server.close();
})();
