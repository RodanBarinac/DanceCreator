// Exercise the current UI against the real local Flask app and its preview API.
import { spawn } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { createServer } from 'node:net';
import { chromium } from 'playwright';

const root = process.cwd();
const python = process.platform === 'win32'
  ? resolve(root, '.venv', 'Scripts', 'python.exe')
  : resolve(root, '.venv', 'bin', 'python');
const flaskCommand =
  'import os; import GUI_DanceCreator_App as module; module.FIGURES_DIR=os.environ["DANCECREATOR_TEST_FIGURES"]; module.DANCES_DIR=os.environ["DANCECREATOR_TEST_DANCES"]; module.app.run(host="127.0.0.1", port=int(os.environ["DANCECREATOR_TEST_PORT"]), debug=False, use_reloader=False)';

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
let fixtureRoot;
let flaskOutput = '';
let flaskSpawnError = null;

try {
  if (!existsSync(python)) {
    throw new Error(`Required virtualenv Python was not found: ${python}`);
  }

  const port = await reservePort();
  const origin = `http://127.0.0.1:${port}`;
  fixtureRoot = mkdtempSync(join(tmpdir(), 'dancecreator-composite-preview-'));
  const fixtureFigures = join(fixtureRoot, 'Figures');
  const fixtureDances = join(fixtureRoot, 'Dances');
  mkdirSync(fixtureFigures, { recursive: true });
  mkdirSync(fixtureDances, { recursive: true });
  cpSync(resolve(root, 'data', 'Figures'), fixtureFigures, { recursive: true });
  cpSync(resolve(root, 'data', 'Dances'), fixtureDances, { recursive: true });
  writeFileSync(join(fixtureFigures, 'Browser Composite.json'), JSON.stringify({
    Name: 'Browser Composite',
    Desc: 'A one-couple turn used for composite preview integration.',
    Formation: 'turn',
    Version: 3,
    FigureList: ['s', [[[1, 0], '1cLT']]],
  }, null, 2));
  writeFileSync(join(fixtureDances, 'Browser Composite Preview.json'), JSON.stringify({
    Name: 'Browser Composite Preview',
    Desc: 'An isolated composite node preview fixture.',
    shape: '3/4',
    Version: 3,
    FigureList: ['s', [[[0, 0], 'Browser Composite']]],
  }, null, 2));
  flask = spawn(python, ['-u', '-c', flaskCommand], {
    cwd: root,
    env: {
      ...process.env,
      DANCECREATOR_TEST_PORT: String(port),
      DANCECREATOR_TEST_FIGURES: fixtureFigures,
      DANCECREATOR_TEST_DANCES: fixtureDances,
    },
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
  await page.setViewportSize({ width: 980, height: 720 });
  await page.goto(origin, { waitUntil: 'networkidle' });
  await page.locator('#fig-list [data-figure-ref="H1DR"]').waitFor({ timeout: 10000 });
  await page.locator('#fig-list [data-figure-ref="H1DR"]').click();
  await page.waitForFunction(() => {
    const status = document.querySelector('#figure-preview-status');
    return status?.textContent.startsWith('Catalog preview') &&
      document.querySelector('#incoming-floor svg');
  }, null, { timeout: 15000 });
  const h1drDescription = await page.locator('#figure-meta').textContent();
  if (!h1drDescription.includes('Half Diagonal Reel on the first diagonal') ||
      h1drDescription.includes('End in lines across') ||
      h1drDescription.includes('End facing 2 corner')) {
    throw new Error('H1DR description does not show only its base description initially.');
  }
  await page.locator('#addon-controls input[name="addon"][value="ELA"]').check();
  await page.waitForFunction(() =>
    document.querySelector('#figure-meta')?.textContent.includes('End in lines across'),
  null, { timeout: 15000 });
  await page.waitForFunction(() =>
    Array.from(document.querySelectorAll('#figure-crips .crip-text'))
      .some(line => line.textContent.includes('to end in between 3c')),
  null, { timeout: 15000 });
  const acrossCrips = await page.locator('#figure-crips .crip-text').allTextContents();
  if (!acrossCrips.some(text => text.includes('to end in between 3c')) ||
      !acrossCrips.some(text => text.includes('to end in between 1c'))) {
    throw new Error('H1DR ELA crips do not describe both line-ending positions.');
  }
  await page.locator('#addon-controls input[name="addon"][value="ELA"]').uncheck();
  await page.waitForFunction(() =>
    !document.querySelector('#figure-meta')?.textContent.includes('End in lines across'),
  null, { timeout: 15000 });
  await page.locator('#addon-controls input[name="addon"][value="E2c"]').check();
  await page.waitForFunction(() =>
    document.querySelector('#figure-meta')?.textContent.includes('End facing 2 corner'),
  null, { timeout: 15000 });
  if ((await page.locator('#figure-meta').textContent()).includes('End in lines across')) {
    throw new Error('Unchecking ELA left its description in the H1DR inspector.');
  }
  await page.waitForFunction(() =>
    Array.from(document.querySelectorAll('#figure-crips .crip-text'))
      .some(line => line.textContent.includes('face 3m')),
  null, { timeout: 15000 });
  const cornerCrips = await page.locator('#figure-crips .crip-text').allTextContents();
  if (!cornerCrips.some(text => text.includes('face 3m')) ||
      !cornerCrips.some(text => text.includes('face 1w'))) {
    throw new Error('H1DR E2c crips do not use the add-on end-facing targets.');
  }

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

  await page.locator('#fig-list [data-figure-ref="1DR"]').click();
  await page.waitForFunction(() =>
    document.querySelector('#figure-preview-status')?.textContent.includes('minimal declared participant set') &&
    document.querySelector('#incoming-floor svg'),
  null, { timeout: 15000 });
  const diagonalPreview = await page.locator('#incoming-floor svg').evaluate(svg =>
    Array.from(svg.querySelectorAll('[data-dancer]'), dancer => ({
      name: dancer.getAttribute('data-dancer'),
      position: dancer.getAttribute('data-position'),
    })).sort((a, b) => a.name.localeCompare(b.name)),
  );
  if (JSON.stringify(diagonalPreview.map(dancer => dancer.name)) !==
      JSON.stringify(['1m', '1w', '2m', '3w'])) {
    throw new Error(`1DR did not render its declared diagonal participants: ${JSON.stringify(diagonalPreview)}`);
  }
  if (!diagonalPreview.some(dancer => dancer.position.includes('.5'))) {
    throw new Error('1DR preview lost its diagonal fractional positions.');
  }

  const heading = await page.evaluate(() => {
    const status = document.querySelector('#draft-status').getBoundingClientRect();
    const apply = document.querySelector('#apply-proposal').getBoundingClientRect();
    return {
      statusRight: status.right,
      statusLeft: status.left,
      applyRight: apply.right,
      applyLeft: apply.left,
      statusTop: status.top,
      statusBottom: status.bottom,
      applyTop: apply.top,
      applyBottom: apply.bottom,
    };
  });
  if (heading.statusLeft < heading.applyRight &&
      heading.statusRight > heading.applyLeft &&
      heading.statusTop < heading.applyBottom &&
      heading.statusBottom > heading.applyTop) {
    throw new Error('Apply button overlaps the inspector status label.');
  }

  await page.locator('#fig-list [data-figure-ref="1cLT"]').click();
  await page.waitForFunction(() =>
    document.querySelector('#figure-preview-status')?.textContent.startsWith('Catalog preview') &&
    document.querySelector('#figure-crips .crip-text'),
  null, { timeout: 15000 });
  const originalInstructions = await page.locator('#figure-crips .crip-text').allTextContents();
  if (originalInstructions.some(text => !text.includes('ends in own place'))) {
    throw new Error('1cLT preview did not start with its default ending instructions.');
  }
  await page.locator('#addon-controls input[name="addon"][value="E1c"]').check();
  await page.waitForFunction(() =>
    Array.from(document.querySelectorAll('#figure-crips .crip-text'))
      .some(line => line.textContent.includes('ends facing')),
  null, { timeout: 15000 });
  const addonInstructions = await page.locator('#figure-crips .crip-text').allTextContents();
  if (addonInstructions.length !== originalInstructions.length ||
      addonInstructions.some(text => !text.includes('ends facing'))) {
    throw new Error('E1c preview instructions did not update for every dancer.');
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
  await page.selectOption('#dance-select', { label: 'Marries Wedding' });
  await page.waitForFunction(() => {
    const model = window.danceCreatorEditor?.state.readModel;
    return model?.document?.metadata?.name === 'Marries Wedding' &&
      model.trace.some(record => record.kind === 'parallel' &&
        JSON.stringify(record.barRange) === '[21,24]');
  }, null, { timeout: 15000 });
  const parallelGroup = await page.evaluate(() => {
    const model = window.danceCreatorEditor.state.readModel;
    const group = model.trace.find(record =>
      record.kind === 'parallel' && JSON.stringify(record.barRange) === '[21,24]');
    const descendants = new Set(model.trace.filter(record =>
      record.kind === 'figure' && record.path.includes(group.nodeId)).map(record => record.nodeId));
    return { id: group.nodeId, lines: model.crips.filter(line => descendants.has(line.nodeId)) };
  });
  if (!parallelGroup.lines.some(line => line.figureRef === 'H2DR')) {
    throw new Error('Expected H2DR instructions in the bars 21-24 parallel group.');
  }
  await page.locator(`#dance-tree [data-node-id="${parallelGroup.id}"]`).click();
  const groupInstructions = await page.locator('#figure-crips .crip-text').allTextContents();
  if (JSON.stringify(groupInstructions) !== JSON.stringify(parallelGroup.lines.map(line => line.text))) {
    throw new Error(`Parallel group instructions differ from its descendant trace: ${JSON.stringify(groupInstructions)}`);
  }
  const h1drNode = await page.evaluate(() => {
    function find(node) {
      if (node.type === 'figure' && node.figureRef === 'H1DR' && node.addons.includes('E2c')) {
        return node.id;
      }
      if (node.type === 'compositeOccurrence') return find(node.root);
      for (const child of node.children || []) {
        const found = find(child);
        if (found) return found;
      }
      return null;
    }
    return find(window.danceCreatorEditor.state.readModel.document.root);
  });
  if (!h1drNode) throw new Error('Expected H1DR with E2c in Marries Wedding.');
  await page.locator(`#dance-tree [data-node-id="${h1drNode}"]`).click();
  if (!(await page.locator('#addon-controls input[value="E2c"]').isChecked()) ||
      !(await page.locator('#figure-meta').textContent()).includes('End facing 2 corner') ||
      !(await page.locator('#apply-proposal').isDisabled())) {
    throw new Error('H1DR selection did not immediately show its actual E2c add-on.');
  }
  const cast = page.locator('#dance-tree li[data-node-type="figure"] > button')
    .filter({ hasText: '1cCast1p' }).first();
  await cast.waitFor({ timeout: 15000 });
  await cast.click();
  const castView = await page.evaluate(() => {
    const snapshot = id => {
      const svg = document.querySelector(`#${id} svg`);
      return {
        dancers: Array.from(svg.querySelectorAll('[data-dancer]'), dancer => ({
          name: dancer.getAttribute('data-dancer'),
          position: dancer.getAttribute('data-position'),
        })).sort((a, b) => a.name.localeCompare(b.name)),
        lines: Array.from(svg.querySelectorAll('[data-set-line]'), line => line.outerHTML),
      };
    };
    return { incoming: snapshot('incoming-floor'), outgoing: snapshot('outgoing-floor') };
  });
  const expectedNames = ['1m', '1w'];
  for (const snapshot of [castView.incoming, castView.outgoing]) {
    if (JSON.stringify(snapshot.dancers.map(dancer => dancer.name)) !== JSON.stringify(expectedNames)) {
      throw new Error(`Cast inspector did not show only the first couple: ${JSON.stringify(snapshot)}`);
    }
    if (snapshot.lines.length !== 2 || snapshot.lines.some(line => !line.includes('stroke-dasharray'))) {
      throw new Error('Cast inspector is missing the dotted set lines.');
    }
  }
  if (castView.incoming.dancers[0].position !== '1,-1' ||
      castView.outgoing.dancers[0].position !== '2,-1' ||
      JSON.stringify(castView.incoming.lines) !== JSON.stringify(castView.outgoing.lines)) {
    throw new Error(`Cast inspector did not preserve the shared frame and movement: ${JSON.stringify(castView)}`);
  }

  await page.selectOption('#dance-select', { label: 'Browser Composite Preview' });
  const compositeNode = page.locator(
    '#dance-tree li[data-node-type="compositeOccurrence"] > button[data-node-id]',
  ).first();
  await compositeNode.waitFor({ timeout: 15000 });
  await compositeNode.click();
  await page.locator('#anchor-row').fill('1');
  await page.waitForFunction(() => {
    const apply = document.querySelector('#apply-proposal');
    return apply && !apply.disabled && document.querySelector('#outgoing-floor svg');
  }, null, { timeout: 15000 });
  const revisionBeforeCompositeEdit = await page.evaluate(
    () => window.danceCreatorEditor.state.readModel.document.revision,
  );
  await page.locator('#apply-proposal').click();
  await page.waitForFunction(revision => {
    const editor = window.danceCreatorEditor;
    return editor.state.readModel.document.revision === revision + 1 &&
      document.querySelector('#anchor-row')?.value === '1' &&
      document.querySelector('#outgoing-floor svg');
  }, revisionBeforeCompositeEdit, { timeout: 15000 });
  await page.locator('#anchor-row').fill('99');
  await page.waitForFunction(() =>
    document.querySelector('#outgoing-floor-error')?.textContent.trim().length > 0,
  null, { timeout: 15000 });
  await page.locator('#anchor-row').fill('1');
  await page.waitForFunction(() =>
    !document.querySelector('#outgoing-floor-error')?.textContent &&
    document.querySelector('#outgoing-floor svg'),
  null, { timeout: 15000 });
  console.log(
    `Inspector layout, 1DR diagonal catalog preview, composite-node edits/errors, and resized previews passed: ` +
    `${rendered.circles} circle(s), woman ${rendered.womanShapeTransform} aligned with facing arrow.`
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
  if (fixtureRoot && existsSync(fixtureRoot)) rmSync(fixtureRoot, { recursive: true, force: true });
}
