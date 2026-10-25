// Exercise the current UI against the real local Flask app and its preview API.
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { createServer } from 'node:net';
import { chromium } from 'playwright';

const root = process.cwd();
const python = process.platform === 'win32'
  ? resolve(root, '.venv', 'Scripts', 'python.exe')
  : resolve(root, '.venv', 'bin', 'python');
const flaskCommand =
  'from GUI_DanceCreator_App import app; app.run(host="127.0.0.1", port=int(__import__("os").environ["DANCECREATOR_TEST_PORT"]), debug=False, use_reloader=False)';

function reservePort() {
  return new Promise((resolvePort, reject) => {
    const reservation = createServer();
    reservation.once('error', reject);
    reservation.listen(0, '127.0.0.1', () => {
      const { port } = reservation.address();
      reservation.close(error => error ? reject(error) : resolvePort(port));
    });
  });
}

const delay = milliseconds => new Promise(resolveDelay => setTimeout(resolveDelay, milliseconds));

function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve(true);
  return new Promise(resolveExit => {
    const onExit = () => {
      clearTimeout(timer);
      resolveExit(true);
    };
    const timer = setTimeout(() => {
      child.removeListener('exit', onExit);
      resolveExit(false);
    }, timeoutMs);
    child.once('exit', onExit);
  });
}

async function stopProcess(child) {
  if (!child || child.pid == null || child.exitCode !== null || child.signalCode !== null) return;
  const gracefulExit = waitForExit(child, 5000);
  try {
    child.kill();
  } catch {
    // An already-exited child may reject a termination request.
  }
  if (await gracefulExit) return;

  const forcedExit = waitForExit(child, 5000);
  try {
    child.kill('SIGKILL');
  } catch {
    // The follow-up wait below reports if the child could not be terminated.
  }
  if (!(await forcedExit) && child.exitCode === null && child.signalCode === null) {
    throw new Error('Flask process did not exit after termination.');
  }
}

let flask;
let browser;
let flaskOutput = '';
let flaskSpawnError = null;

try {
  if (!existsSync(python)) {
    throw new Error(`Required virtualenv Python was not found: ${python}`);
  }

  const port = await reservePort();
  const origin = `http://127.0.0.1:${port}`;
  flask = spawn(python, ['-u', '-c', flaskCommand], {
    cwd: root,
    env: { ...process.env, DANCECREATOR_TEST_PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  flask.on('error', error => { flaskSpawnError = error; });
  flask.stdout.on('data', chunk => { flaskOutput = (flaskOutput + chunk).slice(-8000); });
  flask.stderr.on('data', chunk => { flaskOutput = (flaskOutput + chunk).slice(-8000); });

  const startupDeadline = Date.now() + 30000;
  let ready = false;
  while (Date.now() < startupDeadline) {
    if (flaskSpawnError) throw flaskSpawnError;
    if (flask.exitCode !== null || flask.signalCode !== null) {
      throw new Error(`Flask exited before becoming ready.\n${flaskOutput}`);
    }
    try {
      const response = await fetch(origin);
      if (response.ok) {
        ready = true;
        break;
      }
    } catch {
      // Flask is still importing/starting; retry until the bounded deadline.
    }
    await delay(250);
  }
  if (!ready) throw new Error(`Flask did not become ready.\n${flaskOutput}`);

  browser = await chromium.launch();
  const context = await browser.newContext();
  await context.route('**/*', route => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.origin === origin) return route.continue();
    return route.abort();
  });
  const page = await context.newPage();
  await page.goto(origin, { waitUntil: 'networkidle' });
  await page.locator('#fig-list [data-figure-ref="H1DR"]').waitFor({ timeout: 10000 });
  await page.locator('#fig-list [data-figure-ref="H1DR"]').click();
  await page.waitForFunction(() => {
    const status = document.querySelector('#figure-preview-status');
    return status?.textContent.startsWith('Catalog preview') &&
      document.querySelector('#incoming-floor svg');
  }, null, { timeout: 15000 });

  const rendered = await page.locator('#incoming-floor svg').evaluate(svg => {
    const woman = svg.querySelector('g[data-dancer="1w"]');
    const shape = woman?.querySelector('rect');
    const facingArrow = woman?.querySelector('[data-facing]');
    return {
      circles: svg.querySelectorAll('circle').length,
      womanShapeTransform: shape?.getAttribute('transform') || null,
      womanFacing: facingArrow?.getAttribute('data-facing') || null,
    };
  });
  if (rendered.circles < 1) throw new Error('Incoming preview SVG has no male dancer circle.');
  if (!rendered.womanShapeTransform || !rendered.womanFacing) {
    throw new Error('Incoming preview SVG has no identified woman shape and facing arrow.');
  }
  if (rendered.womanShapeTransform !== `rotate(${rendered.womanFacing})`) {
    throw new Error(
      `Woman shape rotation (${rendered.womanShapeTransform}) does not match facing arrow (${rendered.womanFacing}).`
    );
  }
  if (Number(rendered.womanFacing) === 0) {
    throw new Error('Expected the H1DR woman shape to be visibly rotated.');
  }

  const measureLayout = () => page.evaluate(() => {
    const instructions = document.querySelector('.crips-inspector');
    const floors = document.querySelector('.floor-snapshots');
    const incoming = document.querySelector('.incoming-snapshot');
    const outgoing = document.querySelector('.outgoing-snapshot');
    const box = element => {
      const { top, bottom, width, height } = element.getBoundingClientRect();
      return { top, bottom, width, height };
    };
    return {
      instructions: box(instructions),
      floors: box(floors),
      incoming: box(incoming),
      outgoing: box(outgoing),
      incomingSvg: box(document.querySelector('#incoming-floor svg')),
      outgoingSvg: box(document.querySelector('#outgoing-floor svg')),
      inspectorWidth: document.querySelector('.trace-inspector').clientWidth,
    };
  });
  const assertEqualFloors = (layout, context) => {
    const tolerance = 1;
    const same = (left, right) => Math.abs(left - right) <= tolerance;
    if (!same(layout.incoming.width, layout.floors.width / 2) ||
        !same(layout.outgoing.width, layout.floors.width / 2)) {
      throw new Error(`${context}: dancefloor blocks do not each occupy half the inspector width.`);
    }
    if (!same(layout.incoming.width, layout.outgoing.width) ||
        !same(layout.incoming.height, layout.outgoing.height) ||
        !same(layout.incoming.top, layout.outgoing.top)) {
      throw new Error(`${context}: incoming and outgoing dancefloor blocks are not side by side and equal.`);
    }
    if (!same(layout.incomingSvg.width, layout.outgoingSvg.width) ||
        !same(layout.incomingSvg.height, layout.outgoingSvg.height)) {
      throw new Error(`${context}: incoming and outgoing SVG bounding boxes are not equal.`);
    }
    const incomingRatio = layout.incomingSvg.width / layout.incomingSvg.height;
    const outgoingRatio = layout.outgoingSvg.width / layout.outgoingSvg.height;
    if (Math.abs(incomingRatio - outgoingRatio) > 0.01) {
      throw new Error(`${context}: incoming and outgoing SVG aspect ratios are not equal.`);
    }
  };
  const layout = await measureLayout();
  if (Math.abs(layout.instructions.width - layout.inspectorWidth) > 2) {
    throw new Error('Instructions do not span the full inspector width.');
  }
  if (layout.instructions.bottom > layout.incoming.top ||
      layout.instructions.bottom > layout.outgoing.top) {
    throw new Error('Instructions are not above both dancefloor blocks.');
  }
  if (!(layout.incoming.top < layout.incomingSvg.top &&
        layout.outgoing.top < layout.outgoingSvg.top)) {
    throw new Error('Dancefloor titles are not above their SVGs.');
  }
  assertEqualFloors(layout, 'Initial layout');

  const resizer = await page.locator('.column-resizer[data-resizer-index="1"]').boundingBox();
  const widthBeforeResize = layout.inspectorWidth;
  await page.mouse.move(resizer.x + resizer.width / 2, resizer.y + 20);
  await page.mouse.down();
  await page.mouse.move(resizer.x + resizer.width / 2 + 60, resizer.y + 20);
  await page.mouse.up();
  await page.waitForFunction(previousWidth =>
    Math.abs(document.querySelector('.trace-inspector').clientWidth - previousWidth) > 20,
  widthBeforeResize);
  const resizedLayout = await measureLayout();
  assertEqualFloors(resizedLayout, 'Resized layout');

  const danceNode = page.locator('#dance-tree li[data-node-type="figure"] > button[data-node-id]').first();
  await danceNode.waitFor({ timeout: 10000 });
  await danceNode.click();
  await page.waitForFunction(() =>
    document.querySelector('#figure-preview-status')?.textContent === '' &&
    document.querySelector('#incoming-floor svg') &&
    document.querySelector('#outgoing-floor svg'),
  null, { timeout: 15000 });
  const danceNodeLayout = await measureLayout();
  if (danceNodeLayout.instructions.bottom > danceNodeLayout.incoming.top ||
      danceNodeLayout.instructions.bottom > danceNodeLayout.outgoing.top) {
    throw new Error('Instructions are not above both dance-node dancefloor blocks.');
  }
  assertEqualFloors(danceNodeLayout, 'Dance-node selection after resize');
  console.log(
    `Catalog and resized dance-node previews passed: ${rendered.circles} circle(s), ` +
    `woman ${rendered.womanShapeTransform} aligned with facing arrow.`
  );
} finally {
  if (browser) {
    try {
      await browser.close();
    } catch {
      // Continue to stop Flask even if the browser has already failed.
    }
  }
  await stopProcess(flask);
}
