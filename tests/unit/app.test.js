import {
  createEditor,
  escapeHtml,
  formatPos,
  renderAddonOptions,
  renderCrips,
  renderSteps,
  renderTree,
} from '../../static/app.js';
import { jest } from '@jest/globals';

describe('app.js utility functions', () => {
  
  test('escapeHtml escapes HTML special characters', () => {
    expect(escapeHtml('<script>')).toBe('&lt;script&gt;');
    expect(escapeHtml('"quoted"')).toBe('&quot;quoted&quot;');
    expect(escapeHtml("it's")).toBe('it&#39;s');
    expect(escapeHtml('a&b')).toBe('a&amp;b');
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml(undefined)).toBe('');
    expect(escapeHtml('safe')).toBe('safe');
  });

  test('formatPos formats position array', () => {
    expect(formatPos([1, 2])).toBe('(1, 2)');
    expect(formatPos([10, 20])).toBe('(10, 20)');
    expect(formatPos(null)).toBe('');
    expect(formatPos([])).toBe('');
    expect(formatPos([1])).toBe('');
    expect(formatPos('not array')).toBe('');
  });

  test('renderSteps generates HTML table from figure step data', () => {
    const data = {
      StartPos: [[1,1], [1,2]],
      EndPos: [[1,3], [1,4]],
      EndFacing: [[0, 1], [1, 0]],
      Partner: [[1,2], [1,3]]
    };
    const result = renderSteps(data);
    expect(result).toContain('<table class="figure-table">');
    expect(result).toContain('<th>#</th>');
    expect(result).toContain('(1, 1)');
    expect(result).toContain('(0, 1)');
    expect(result).toContain('(1, 0)');
  });

  test('renderCrips renders structured dancer lines and marks the selected dancer', () => {
    const lines = [
      { figureRef: 'Step', dancer: '1m', barRange: [1, 2], text: 'Turn right' },
      { figureRef: 'Step', dancer: '1w', barRange: [1, 2], text: '<Cast down>' },
    ];
    const result = renderCrips(lines, '1w');

    expect(result).toContain('<ol class="figure-crips">');
    expect(result).toContain('data-crip-dancer="1m"');
    expect(result).toContain('Bars 1-2');
    expect(result).toContain('1m');
    expect(result).toContain('Turn right');
    expect(result).toContain('aria-pressed="true"');
    expect(result).toContain('&lt;Cast down&gt;');
    expect(result).not.toContain('CriptDesc');
  });

  test('renderCrips handles an empty structured line list', () => {
    expect(renderCrips([])).toContain('No crips available');
  });

  test('renderCrips marks affected instructions and renders the dancer name only once', () => {
    const html = renderCrips([
      { dancer: 'Ann', barRange: [1, 1], text: 'Turns left.', figureRef: 'Step' },
    ], null, ['Ann']);
    const line = document.createElement('div');
    line.innerHTML = html;
    const button = line.querySelector('.crip-line');

    expect(button.classList.contains('invalid-preview-marker')).toBe(true);
    expect(button.querySelectorAll('.crip-dancer')).toHaveLength(1);
    expect(button.querySelector('.crip-dancer').textContent).toBe('Ann');
    expect(button.querySelector('.crip-text').textContent).toBe('Turns left.');
    expect(button.querySelector('.crip-text').textContent).not.toContain('Ann');
  });

  test('renderTree preserves canonical IDs for groups, occurrences, and composites', () => {
    const tree = {
      type: 'group',
      id: 'root-id',
      kind: 'series',
      children: [
        { type: 'figure', id: 'occurrence-id', figureRef: 'Step', anchor: [1, 1], addons: [] },
        {
          type: 'compositeOccurrence',
          id: 'composite-id',
          figureRef: 'Reel',
          anchor: [0, 0],
          addons: [],
          root: {
            type: 'group',
            id: 'embedded-root',
            kind: 'series',
            children: [],
          },
        },
      ],
    };

    const html = renderTree(tree, 'occurrence-id');

    expect(html).toContain('data-node-id="root-id"');
    expect(html).toContain('data-node-id="occurrence-id"');
    expect(html).toContain('data-node-id="composite-id"');
    expect(html).toContain('data-node-id="embedded-root"');
    expect(html).toContain('selected');
  });

  test('renderAddonOptions exposes only engine capabilities and disables composites', () => {
    const controls = renderAddonOptions(
      { validAddons: [{ name: 'Turn', description: 'Rotate' }] },
      ['Turn'],
    );
    const composite = renderAddonOptions(null, []);

    expect(controls).toContain('value="Turn"');
    expect(controls).toContain('checked');
    expect(controls).not.toContain('Invented');
    expect(composite).toContain('disabled');
    expect(composite).toContain('unsupported');
  });

  test('createEditor supports one-step apply and revisioned undo/redo', async () => {
    const initial = {
      document: { revision: 0, incomplete: false, root: { id: 'root-id' } },
      tree: { id: 'root-id' },
      trace: [],
      validation: { isValid: true, errors: [] },
    };
    const applied = {
      ...initial,
      document: { ...initial.document, revision: 1 },
    };
    const undone = {
      ...initial,
      document: { ...initial.document, revision: 2 },
    };
    const redone = {
      ...initial,
      document: { ...initial.document, revision: 3 },
    };
    const calls = [];
    const send = async (path, options = {}) => {
      calls.push({ path, options });
      if (path === '/api/dances/dance-id') return { status: 200, body: initial };
      if (path.endsWith('/proposals')) {
        return { status: 200, body: { proposal: { proposalId: 'proposal-id', tree: { id: 'candidate' } } } };
      }
      if (path.endsWith('/apply')) return { status: 200, body: applied };
      if (path.endsWith('/undo')) return { status: 200, body: undone };
      if (path.endsWith('/redo')) return { status: 200, body: redone };
      throw new Error(`Unexpected request: ${path}`);
    };
    const editor = createEditor({ send, documentRef: null });
    const command = { type: 'updateAnchor', nodeId: 'occurrence-id', anchor: [2, 1] };

    await editor.loadDance('dance-id');
    await editor.propose(command);
    expect(editor.state.readModel.document.revision).toBe(0);
    expect(editor.state.proposal.proposalId).toBe('proposal-id');
    expect(editor.cancelProposal).toBeUndefined();
    expect(calls.filter(call => call.path.endsWith('/apply'))).toHaveLength(0);

    await editor.propose(command);
    await editor.applyProposal();
    expect(editor.state.readModel.document.revision).toBe(1);
    await editor.undo();
    await editor.redo();
    expect(editor.state.readModel.document.revision).toBe(3);
    expect(calls.filter(call => call.path.endsWith('/undo'))[0].options.method).toBe('POST');
    expect(calls.filter(call => call.path.endsWith('/redo'))[0].options.method).toBe('POST');
  });

  test('editor projection keeps incomplete warnings and capability-backed controls visible', async () => {
    document.body.innerHTML = `
      <p id="status"></p><ul id="fig-list"></ul><select id="dance-select"></select>
      <h3 id="dance-title"></h3><div id="dance-tree"></div><div id="draft-status"></div>
      <p id="incomplete-warning"></p><h3 id="figure-name"></h3><div id="figure-meta"></div>
      <div id="addon-controls"></div><input id="anchor-row"><input id="anchor-col">
      <p id="trace-status"></p><pre id="incoming-floor"></pre><pre id="outgoing-floor"></pre>
      <button id="delete-node"></button><button id="apply-proposal"></button>
      <button id="apply-proposal"></button><pre id="validation-panel"></pre>
      <p id="error-panel"></p><button id="save-dance"></button>
      <button id="undo-dance"></button><button id="redo-dance"></button>
      <button id="insert-figure"></button><button id="add-series"></button>
      <button id="add-parallel"></button>
    `;
    const occurrence = {
      type: 'figure',
      id: 'stable-occurrence',
      figureRef: 'Step',
      anchor: [1, 1],
      addons: ['Turn'],
    };
    const readModel = {
      document: {
        revision: 0,
        status: 'incomplete',
        incomplete: true,
        unresolvedReferences: ['Missing'],
        metadata: { name: 'Draft' },
        root: { type: 'group', id: 'root-id', kind: 'series', children: [occurrence] },
      },
      tree: {
        type: 'group',
        id: 'root-id',
        kind: 'series',
        children: [occurrence],
      },
      trace: [],
      validation: { isValid: false, errors: [{ code: 'reference_not_found', message: 'Missing' }] },
    };
    const send = async path => {
      if (path === '/api/figures') {
        return {
          status: 200,
          body: { figures: [{
            figureRef: 'Step',
            name: 'Step',
            version: 2,
            capabilities: {
              validAddons: [{ name: 'Turn' }],
              bars: 1,
            },
          }] },
        };
      }
      if (path === '/api/dances/draft-id') return { status: 200, body: readModel };
      throw new Error(`Unexpected request: ${path}`);
    };
    const editor = createEditor({ send, documentRef: document });

    await editor.loadCatalog();
    await editor.loadDance('draft-id');
    editor.state.selectedNodeId = 'stable-occurrence';
    editor.render();

    expect(document.getElementById('draft-status').textContent).toBe('INCOMPLETE DRAFT');
    expect(document.getElementById('incomplete-warning').textContent).toContain('Missing');
    expect(document.querySelector('#dance-tree [data-node-id="stable-occurrence"]')).not.toBeNull();
    expect(document.querySelector('#addon-controls input[value="Turn"]')).not.toBeNull();
  });

  test('catalog figures render anchored incoming and outgoing active-dancer diagrams', async () => {
    document.body.innerHTML = `
      <ul id="fig-list"></ul><h3 id="figure-name"></h3><div id="figure-meta"></div>
      <pre id="validation-panel"></pre><p id="error-panel"></p>
      <h3 id="trace-heading"></h3><p id="trace-status"></p>
      <select id="dance-select"></select><h3 id="dance-title"></h3><div id="dance-tree"></div>
      <div id="draft-status"></div><p id="incomplete-warning"></p>
      <button id="save-dance"></button><button id="undo-dance"></button><button id="redo-dance"></button>
      <button id="insert-figure"></button><button id="add-series"></button>
      <button id="add-parallel"></button><button id="move-up"></button><button id="move-down"></button>
      <div id="addon-controls"></div><input id="anchor-row" value="1"><input id="anchor-col" value="1">
      <button id="apply-proposal"></button>
      <div id="incoming-floor"></div><div id="outgoing-floor"></div>
      <div id="figure-preview-status"></div>
    `;
    const floor = anchor => ({
      '1m': {
        position: [anchor[0], anchor[1] - 1],
        dancer: { name: '1m', gender: 'male' },
        facing: [anchor[0], anchor[1] + 1],
      },
      '1w': {
        position: [anchor[0], anchor[1] + 1],
        dancer: { name: '1w', gender: 'female' },
        facing: [anchor[0], anchor[1] - 1],
      },
    });
    const previewCalls = [];
    const failedDance = {
      document: {
        revision: 0,
        status: 'complete',
        metadata: { name: 'Conflict dance' },
        root: { type: 'group', id: 'parallel', kind: 'parallel', children: [] },
      },
      tree: { type: 'group', id: 'parallel', kind: 'parallel', children: [] },
      trace: [],
      validation: {
        isValid: false,
        errors: [{ code: 'parallel_conflict', message: 'Tree execution has a conflict.' }],
      },
      execution: { status: 'failed', lastValidFloor: floor },
    };
    const send = async (path, options = {}) => {
      if (path === '/api/figures/Step/preview') {
        const request = JSON.parse(options.body);
        previewCalls.push(request);
        const anchoredFloor = floor(request.anchor);
        return {
          status: 200,
          body: {
            couples: 1,
            incomingFloor: anchoredFloor,
            outgoingFloor: anchoredFloor,
          },
        };
      }
      if (path === '/api/figures') {
        return {
          status: 200,
          body: { figures: [{
            figureRef: 'Step',
            name: 'Step',
            description: 'A step',
            version: 2,
            capabilities: {
              bars: 1,
              validAddons: [{ name: 'Shift', description: 'Shift start and end positions' }],
            },
          }] },
        };
      }
      if (path === '/api/dances/dance-id') {
        return { status: 200, body: failedDance };
      }
      throw new Error(`Unexpected request: ${path}`);
    };
    const editor = createEditor({ send, documentRef: document });

    editor.wire();
    await editor.loadDance('dance-id');
    expect(document.getElementById('validation-panel').hidden).toBe(false);
    expect(document.getElementById('validation-panel').textContent)
      .toContain('Tree execution has a conflict.');
    await editor.loadCatalog();
    document.querySelector('[data-figure-ref="Step"]').click();
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(document.querySelector('#incoming-floor svg')).not.toBeNull();
    expect(document.querySelector('#outgoing-floor svg')).not.toBeNull();
    expect(document.querySelector('#incoming-floor svg').textContent)
      .not.toContain('Incoming catalog preview');
    expect(document.querySelector('#outgoing-floor svg').textContent)
      .not.toContain('Outgoing catalog preview');
    expect(document.querySelector('#addon-controls input[value="Shift"]')).not.toBeNull();
    expect(document.getElementById('apply-proposal').disabled).toBe(true);
    expect(document.getElementById('validation-panel').hidden).toBe(true);
    expect(document.getElementById('validation-panel').textContent).toBe('');
    expect(document.getElementById('error-panel').hidden).toBe(true);
    expect(document.getElementById('trace-heading').textContent).toContain('Step');
    expect(document.getElementById('figure-preview-status').textContent)
      .toContain('minimal declared participant set');

    document.getElementById('anchor-row').value = '2';
    document.getElementById('anchor-row').dispatchEvent(new Event('change', { bubbles: true }));
    document.querySelector('#addon-controls input[value="Shift"]').checked = true;
    document.querySelector('#addon-controls input[value="Shift"]')
      .dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(previewCalls.at(-1)).toEqual({ anchor: [2, 0], addons: ['Shift'] });

    const initialPosition = document.querySelector(
      '#incoming-floor [data-dancer="1m"]'
    ).getAttribute('transform');
    document.getElementById('anchor-col').value = '-1';
    document.getElementById('anchor-col').dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(previewCalls.at(-1)).toEqual({ anchor: [2, -1], addons: ['Shift'] });
    const mensLinePosition = document.querySelector(
      '#incoming-floor [data-dancer="1m"]'
    ).getAttribute('transform');
    document.getElementById('anchor-col').value = '1';
    document.getElementById('anchor-col').dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(previewCalls.at(-1)).toEqual({ anchor: [2, 1], addons: ['Shift'] });
    const ladiesLinePosition = document.querySelector(
      '#incoming-floor [data-dancer="1m"]'
    ).getAttribute('transform');
    expect(mensLinePosition).not.toBe(initialPosition);
    expect(ladiesLinePosition).not.toBe(mensLinePosition);
  });

  test('failed catalog preview preserves and marks the last valid outgoing floor', async () => {
    document.body.innerHTML = `
      <ul id="fig-list"></ul><h3 id="figure-name"></h3><div id="figure-meta"></div>
      <h3 id="trace-heading"></h3><p id="trace-status"></p><p id="figure-preview-status"></p>
      <div id="addon-controls"></div><input id="anchor-row" value="1"><input id="anchor-col" value="0">
      <div id="figure-crips"></div><div id="incoming-floor"></div>
      <p id="outgoing-floor-error" hidden></p><div id="outgoing-floor"></div>
      <button id="apply-proposal"></button><p id="error-panel"></p>
    `;
    const floor = name => ({
      [name]: { position: [1, 1], dancer: { name, gender: 'male' }, facing: [1, 3] },
    });
    let previewCount = 0;
    const send = async (path, options = {}) => {
      if (path === '/api/figures') {
        return { status: 200, body: { figures: [{
          figureRef: 'Step', name: 'Step', capabilities: { validAddons: [] },
        }] } };
      }
      if (path === '/api/figures/Step/preview') {
        previewCount += 1;
        if (previewCount === 1) {
          return { status: 200, body: {
            incomingFloor: floor('Incoming'), outgoingFloor: floor('LastValid'),
            crips: [{ dancer: 'LastValid', barRange: [1, 1], text: 'Step instruction.' }],
          } };
        }
        return { status: 409, body: { error: {
          code: 'addon_conflict', message: 'Catalog preview conflict.', dancers: ['LastValid'],
        } } };
      }
      throw new Error(`Unexpected request: ${path}`);
    };
    const editor = createEditor({ send, documentRef: document });
    editor.wire();
    await editor.loadCatalog();
    document.querySelector('[data-figure-ref="Step"]').click();
    await new Promise(resolve => setTimeout(resolve, 0));
    document.getElementById('anchor-row').value = '2';
    document.getElementById('anchor-row').dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(document.getElementById('outgoing-floor-error').hidden).toBe(false);
    expect(document.getElementById('outgoing-floor-error').textContent).toContain('Catalog preview conflict.');
    expect(document.getElementById('outgoing-floor').classList.contains('invalid-preview')).toBe(true);
    expect(document.querySelector('#outgoing-floor [data-dancer="LastValid"]')
      .classList.contains('invalid-preview-marker')).toBe(true);
    expect(document.querySelector('#figure-crips .crip-line').classList.contains('invalid-preview-marker')).toBe(true);
    expect(document.getElementById('outgoing-floor').textContent).toContain('LastValid');
    expect(editor.state.figurePreview.outgoingFloor).toEqual(floor('LastValid'));
  });

  test('catalog crips lines select incoming-floor dancers and floor clicks select lines', async () => {
    document.body.innerHTML = `
      <ul id="fig-list"></ul><h3 id="figure-name"></h3><div id="figure-meta"></div>
      <h3 id="trace-heading"></h3><p id="trace-status"></p>
      <div id="addon-controls"></div><input id="anchor-row"><input id="anchor-col">
      <div id="incoming-floor"></div><div id="outgoing-floor"></div><div id="figure-crips"></div>
    `;
    const floor = {
      '1m': { position: [1, 1], dancer: { name: '1m', gender: 'male' }, facing: [1, 3] },
      '1w': { position: [1, 2], dancer: { name: '1w', gender: 'female' }, facing: [1, 0] },
    };
    const send = async path => {
      if (path === '/api/figures') return { status: 200, body: { figures: [{ figureRef: 'Step', name: 'Step' }] } };
      if (path === '/api/figures/Step/preview') return { status: 200, body: {
        incomingFloor: floor,
        outgoingFloor: floor,
        crips: [
          { figureRef: 'Step', dancer: '1m', barRange: [1, 2], text: 'Turns right.' },
          { figureRef: 'Step', dancer: '1w', barRange: [1, 2], text: 'Turns left.' },
        ],
      } };
      throw new Error(`Unexpected request: ${path}`);
    };
    const editor = createEditor({ send, documentRef: document });
    editor.wire();
    await editor.loadCatalog();
    document.querySelector('[data-figure-ref="Step"]').click();
    await new Promise(resolve => setTimeout(resolve, 0));

    const line = document.querySelector('#figure-crips [data-crip-dancer="1w"]');
    expect(line).not.toBeNull();
    line.click();
    expect(document.querySelector('#incoming-floor [data-dancer="1w"]').getAttribute('data-selected')).toBe('true');
    expect(document.querySelector('#figure-crips [data-crip-dancer="1w"]').getAttribute('aria-pressed')).toBe('true');

    document.querySelector('#incoming-floor [data-dancer="1m"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(document.querySelector('#figure-crips [data-crip-dancer="1m"]').getAttribute('aria-pressed')).toBe('true');
    expect(document.querySelector('#incoming-floor [data-dancer="1m"]').getAttribute('data-selected')).toBe('true');
  });

  test('dance occurrence displays only its crips on the traced incoming floor', async () => {
    document.body.innerHTML = `
      <div id="dance-tree"></div><h3 id="figure-name"></h3><div id="figure-meta"></div>
      <div id="addon-controls"></div><input id="anchor-row"><input id="anchor-col">
      <p id="trace-status"></p><div id="incoming-floor"></div><div id="outgoing-floor"></div>
      <div id="figure-crips"></div><div id="dance-floor-canvas"></div>
    `;
    const node = { type: 'figure', id: 'step-node', figureRef: 'Step', anchor: [1, 0], addons: [] };
    const root = { type: 'group', id: 'root-node', kind: 'series', children: [node] };
    const incomingFloor = {
      '1m': { position: [1, 1], dancer: { name: '1m', gender: 'male' }, facing: [1, 3] },
    };
    const readModel = {
      document: { root, status: 'complete', metadata: { name: 'Dance' } },
      tree: root,
      trace: [{
        nodeId: 'step-node', kind: 'figure', figureRef: 'Step', status: 'completed',
        barRange: [3, 4], incomingFloor, outgoingFloor: incomingFloor, writes: [],
      }],
      crips: [
        { figureRef: 'Step', dancer: '1m', barRange: [1, 2], text: 'Earlier step.' },
        { figureRef: 'Step', dancer: '1m', barRange: [3, 4], text: 'Selected step.' },
      ],
      validation: { isValid: true, errors: [] },
    };
    const editor = createEditor({ send: async () => ({ status: 200, body: readModel }), documentRef: document });
    editor.wire();
    await editor.loadDance('dance-id');
    document.querySelector('#dance-tree [data-node-id="step-node"]').click();

    expect(document.querySelector('#figure-crips').textContent).toContain('Selected step.');
    expect(document.querySelector('#figure-crips').textContent).not.toContain('Earlier step.');
    expect(document.querySelector('#incoming-floor [data-dancer="1m"]')).not.toBeNull();
    expect(document.querySelector('#outgoing-floor svg').textContent).not.toContain('Outgoing dancefloor');
    expect(document.querySelector('#outgoing-floor svg').getAttribute('aria-label')).toBe('Outgoing dancefloor');
  });

  test('inspector filters by active identity and shares full-set frame across snapshots', async () => {
    document.body.innerHTML = `
      <div id="dance-tree"></div><div id="figure-meta"></div><div id="addon-controls"></div>
      <input id="anchor-row"><input id="anchor-col"><p id="trace-status"></p>
      <div id="incoming-floor"></div><div id="outgoing-floor"></div><div id="dance-floor-canvas"></div>`;
    const node = { type: 'figure', id: 'cast', figureRef: 'Cast', anchor: [1, 0], addons: [] };
    const root = { type: 'group', id: 'root', kind: 'series', children: [node] };
    const floor = (row, side = -1) => ({
      a: { position: [row, side], dancer: { name: '1m', gender: 'male' } },
      b: { position: [4, 1], dancer: { name: '4w', gender: 'female' } },
    });
    const trace = { nodeId: 'cast', kind: 'figure', status: 'completed',
      incomingFloor: floor(1), outgoingFloor: floor(2.5, 2), activeDancers: ['1m'] };
    const readModel = { document: { root, metadata: { name: 'Dance' } }, tree: root,
      trace: [trace], crips: [], validation: { isValid: true, errors: [] } };
    const editor = createEditor({ send: async () => ({ status: 200, body: readModel }), documentRef: document });
    editor.wire();
    await editor.loadDance('dance-id');
    document.querySelector('#dance-tree [data-node-id="cast"]').click();
    expect(document.querySelector('#incoming-floor [data-dancer="4w"]')).toBeNull();
    expect(document.querySelector('#outgoing-floor [data-dancer="4w"]')).toBeNull();
    expect(document.querySelector('#outgoing-floor [data-dancer="1m"]').getAttribute('data-position')).toBe('2.5,2');
    const incoming = document.querySelector('#incoming-floor svg');
    const outgoing = document.querySelector('#outgoing-floor svg');
    const lines = svg => [...svg.querySelectorAll('line[data-set-line]')].map(line => line.outerHTML);
    expect(lines(incoming)).toHaveLength(2);
    expect(lines(incoming)).toEqual(lines(outgoing));
    expect(incoming.textContent).toContain('4');
    expect(outgoing.textContent).toContain('4');

    editor.state.nodePreview = {
      nodeId: 'cast', model: editor.state.readModel, anchor: [1, 0], addons: [],
      activeDancers: ['4w'], outgoingFloor: floor(2.5, 2),
    };
    editor.render();
    expect(document.querySelector('#incoming-floor [data-dancer="1m"]')).toBeNull();
    expect(document.querySelector('#incoming-floor [data-dancer="4w"]')).not.toBeNull();
    expect(document.querySelector('#outgoing-floor [data-dancer="4w"]')).not.toBeNull();

    delete editor.state.nodePreview.activeDancers;
    editor.render();
    expect(document.querySelector('#incoming-floor [data-dancer="1m"]')).not.toBeNull();
    expect(document.querySelector('#incoming-floor [data-dancer="4w"]')).not.toBeNull();
  });

  test('composite dance node displays child crips within its traced bar range', async () => {
    document.body.innerHTML = `
      <div id="dance-tree"></div><div id="figure-meta"></div><div id="addon-controls"></div>
      <input id="anchor-row"><input id="anchor-col"><p id="trace-status"></p>
      <div id="incoming-floor"></div><div id="outgoing-floor"></div>
      <div id="figure-crips"></div><div id="dance-floor-canvas"></div>
    `;
    const child = { type: 'figure', id: 'child-step', figureRef: 'Step', anchor: [0, 0], addons: [] };
    const composite = {
      type: 'compositeOccurrence', id: 'reel-node', figureRef: 'Reel', anchor: [1, 0], addons: [],
      root: { type: 'group', id: 'reel-root', kind: 'series', children: [child] },
    };
    const root = { type: 'group', id: 'root', kind: 'series', children: [composite] };
    const floor = { '1m': { position: [1, 1], dancer: { name: '1m', gender: 'male' } } };
    const readModel = {
      document: { root, status: 'complete', metadata: { name: 'Dance' } },
      tree: root,
      trace: [
        { nodeId: 'reel-node', kind: 'composite', figureRef: 'Reel', status: 'completed', barRange: [1, 4], incomingFloor: floor, outgoingFloor: floor },
        { nodeId: 'child-step', kind: 'figure', figureRef: 'Step', status: 'completed', barRange: [1, 2], incomingFloor: floor, outgoingFloor: floor },
      ],
      crips: [
        { figureRef: 'Step', dancer: '1m', barRange: [1, 2], text: 'Child instruction.' },
        { figureRef: 'Other', dancer: '1m', barRange: [5, 6], text: 'Outside instruction.' },
      ],
      validation: { isValid: true, errors: [] },
    };
    const editor = createEditor({ send: async () => ({ status: 200, body: readModel }), documentRef: document });
    editor.wire();
    await editor.loadDance('dance-id');
    document.querySelector('#dance-tree [data-node-id="reel-node"]').click();

    expect(document.querySelector('#figure-crips').textContent).toContain('Child instruction.');
    expect(document.querySelector('#figure-crips').textContent).not.toContain('Outside instruction.');
  });

  test('group crips include only descendant occurrences, including nested composites', async () => {
    document.body.innerHTML = `
      <div id="dance-tree"></div><div id="figure-meta"></div><div id="addon-controls"></div>
      <input id="anchor-row"><input id="anchor-col"><p id="trace-status"></p>
      <div id="incoming-floor"></div><div id="outgoing-floor"></div>
      <div id="figure-crips"></div><div id="dance-floor-canvas"></div>`;
    const leaf = id => ({ type: 'figure', id, figureRef: 'Step', anchor: [1, 0], addons: [] });
    const composite = { type: 'compositeOccurrence', id: 'comp', figureRef: 'Composite',
      anchor: [0, 0], addons: [], root: { type: 'group', id: 'embedded', kind: 'series',
        children: [leaf('nested')] } };
    const group = { type: 'group', id: 'selected-group', kind: 'parallel',
      children: [leaf('selected'), composite] };
    const empty = { type: 'group', id: 'empty', kind: 'series', children: [] };
    const root = { type: 'group', id: 'root', kind: 'parallel',
      children: [group, leaf('sibling'), empty] };
    const floor = { a: { position: [1, 1], dancer: { name: '1m', gender: 'male' } } };
    const model = { document: { root, metadata: { name: 'Dance' } }, tree: root,
      trace: [{ nodeId: 'selected-group', kind: 'parallel', status: 'completed',
        barRange: [21, 24], incomingFloor: floor, outgoingFloor: floor }],
      crips: [
        { nodeId: 'selected', figureRef: 'Step', dancer: '1m', barRange: [21, 24], text: 'Selected instruction.' },
        { nodeId: 'nested', figureRef: 'Step', dancer: '1m', barRange: [21, 24], text: 'Nested instruction.' },
        { nodeId: 'sibling', figureRef: 'Step', dancer: '1m', barRange: [21, 24], text: 'Sibling instruction.' },
        { figureRef: 'Step', dancer: '1m', barRange: [21, 24], text: 'Unidentified instruction.' },
      ], validation: { isValid: true, errors: [] } };
    const editor = createEditor({ send: async () => ({ status: 200, body: model }), documentRef: document });
    editor.wire();
    await editor.loadDance('dance-id');
    document.querySelector('#dance-tree [data-node-id="selected-group"]').click();

    const text = document.querySelector('#figure-crips').textContent;
    expect(text).toContain('Selected instruction.');
    expect(text).toContain('Nested instruction.');
    expect(text).not.toContain('Sibling instruction.');
    expect(text).not.toContain('Unidentified instruction.');

    document.querySelector('#dance-tree [data-node-id="embedded"]').click();
    const nestedText = document.querySelector('#figure-crips').textContent;
    expect(nestedText).toContain('Nested instruction.');
    expect(nestedText).not.toContain('Selected instruction.');
    expect(nestedText).not.toContain('Sibling instruction.');

    document.querySelector('#dance-tree [data-node-id="empty"]').click();
    expect(document.querySelector('#figure-crips').textContent).toContain('No crips available.');
  });

  test('group and composite snapshots use the descendant participant union', async () => {
    document.body.innerHTML = `
      <div id="dance-tree"></div><div id="figure-meta"></div><div id="addon-controls"></div>
      <input id="anchor-row"><input id="anchor-col"><p id="trace-status"></p>
      <div id="incoming-floor"></div><div id="outgoing-floor"></div>`;
    const composite = { type: 'compositeOccurrence', id: 'comp', figureRef: 'Comp',
      anchor: [1, 0], addons: [], root: { type: 'group', id: 'embedded', kind: 'series', children: [] } };
    const group = { type: 'group', id: 'parallel', kind: 'parallel', children: [composite] };
    const root = { type: 'group', id: 'root', kind: 'series', children: [group] };
    const floor = Object.fromEntries(['1m', '2m', '3m'].map((name, i) =>
      [name, { position: [i + 1, -1], dancer: { name, gender: 'male' } }]));
    const records = ['parallel', 'comp'].map(nodeId => ({
      nodeId, kind: nodeId === 'parallel' ? 'parallel' : 'composite', status: 'completed',
      incomingFloor: floor, outgoingFloor: floor, activeDancers: ['1m', '3m'],
    }));
    const model = { document: { root, metadata: { name: 'Dance' } }, tree: root,
      trace: records, crips: [], validation: { isValid: true, errors: [] } };
    const editor = createEditor({ send: async () => ({ status: 200, body: model }), documentRef: document });
    editor.wire();
    await editor.loadDance('dance-id');
    for (const id of ['parallel', 'comp']) {
      document.querySelector(`#dance-tree [data-node-id="${id}"]`).click();
      expect([...document.querySelectorAll('#incoming-floor [data-dancer]')]
        .map(token => token.getAttribute('data-dancer'))).toEqual(['1m', '3m']);
      expect(document.querySelector('#outgoing-floor [data-dancer="2m"]')).toBeNull();
    }
  });

  test('save confirms an incomplete transition before retrying', async () => {
    const readModel = {
      document: {
        revision: 0,
        status: 'incomplete',
        unresolvedReferences: ['Missing'],
      },
      tree: {},
      trace: [],
      validation: { isValid: false, errors: [] },
    };
    const calls = [];
    const send = async (path, options) => {
      calls.push({ path, options: options && JSON.parse(options.body) });
      if (calls.length === 1) {
        return {
          status: 409,
          body: { error: { code: 'incomplete_confirmation_required', message: 'Confirm draft.' } },
        };
      }
      return { status: 200, body: { ...readModel, revision: 1 } };
    };
    const confirm = jest.fn(() => true);
    const editor = createEditor({ send, documentRef: null, confirmIncomplete: confirm });
    editor.state.danceId = 'draft-id';
    editor.state.readModel = readModel;

    const saved = await editor.save();

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(calls[1].options.confirmIncomplete).toBe(true);
    expect(saved.revision).toBe(1);
  });

  test('failed parallel selection shows last valid floor and isolated branch renderings', async () => {
    document.body.innerHTML = `
      <p id="status"></p><ul id="fig-list"></ul><select id="dance-select"></select>
      <h3 id="dance-title"></h3><div id="dance-tree"></div><div id="draft-status"></div>
      <p id="incomplete-warning"></p><h3 id="figure-name"></h3><div id="figure-meta"></div>
      <div id="addon-controls"></div><input id="anchor-row"><input id="anchor-col">
      <p id="trace-status"></p>
      <div class="incoming-snapshot"><h4>Incoming dancefloor</h4><div id="incoming-floor"></div></div>
      <div class="outgoing-snapshot"><h4>Outgoing dancefloor</h4><div id="outgoing-floor"></div></div>
      <button id="delete-node"></button><button id="apply-proposal"></button>
      <pre id="validation-panel"></pre>
      <p id="error-panel"></p><button id="save-dance"></button>
      <button id="undo-dance"></button><button id="redo-dance"></button>
      <button id="insert-figure"></button><button id="add-series"></button>
      <button id="add-parallel"></button><button id="move-up"></button><button id="move-down"></button>
      <button id="playback-prev"></button>
      <button id="playback-next"></button>
      <span id="playback-position"></span><p id="playback-warning"></p>
      <p id="floor-status"></p><div id="dance-floor-canvas"></div><div id="branch-floors"></div>
    `;
    const incomingFloor = {
      '1m': {
        position: [1, 1],
        dancer: { name: '1m', gender: 'male' },
        facing: [1, 3],
      },
    };
    const lastValidFloor = {
      '1m': {
        position: [2.5, 3.25],
        dancer: { name: '1m', gender: 'male' },
        facing: [1, 3],
      },
    };
    const tree = {
      type: 'group',
      id: 'parallel',
      kind: 'parallel',
      children: [],
    };
    const readModel = {
      document: {
        revision: 0,
        status: 'complete',
        metadata: { name: 'Conflict dance' },
        root: tree,
      },
      tree,
      trace: [{
        nodeId: 'parallel',
        kind: 'parallel',
        status: 'failed',
        incomingFloor,
        outgoingFloor: null,
        writes: [],
        conflict: { code: 'parallel_write_conflict' },
        branches: [
          { nodeId: 'left', status: 'completed', outgoingFloor: incomingFloor, writes: [[1, 1]] },
          { nodeId: 'right', status: 'completed', outgoingFloor: incomingFloor, writes: [[1, 1]] },
        ],
      }],
      validation: {
        isValid: false,
        errors: [{ code: 'parallel_conflict', message: 'Tree execution has a conflict.' }],
      },
      execution: { status: 'failed', lastValidFloor },
      validation: { isValid: false, errors: [] },
    };
    const send = async () => ({ status: 200, body: readModel });
    const editor = createEditor({ send, documentRef: document });

    await editor.loadDance('conflict-id');

    expect(document.getElementById('playback-warning').textContent).toContain('last valid floor');
    expect(document.querySelector('#incoming-floor svg')).not.toBeNull();
    expect(document.querySelector('.incoming-snapshot').textContent.match(/Incoming dancefloor/g)).toHaveLength(1);
    expect(document.querySelector('#incoming-floor svg').getAttribute('aria-label')).toBe('Incoming dancefloor');
    expect(document.querySelector('.outgoing-snapshot').textContent.match(/Outgoing dancefloor/g)).toHaveLength(1);
    expect(document.querySelector('#dance-floor-canvas svg [data-context="group"]')).not.toBeNull();
    expect(document.querySelector('#dance-floor-canvas [data-position="2.5,3.25"]')).not.toBeNull();
    expect(document.querySelector('#dance-floor-canvas [data-position="1,1"]')).toBeNull();
    expect(document.querySelectorAll('#dance-floor-canvas line[data-set-line]')).toHaveLength(2);
    expect(document.querySelectorAll('#branch-floors .branch-floor')).toHaveLength(2);
    for (const branch of document.querySelectorAll('#branch-floors .branch-floor')) {
      expect(branch.textContent.match(/Isolated branch/g)).toHaveLength(1);
      expect(branch.querySelector('svg').getAttribute('aria-label')).toContain('Isolated branch');
      expect(branch.querySelectorAll('line[data-set-line]')).toHaveLength(2);
    }
  });

  test('workspace columns resize by pointer and keyboard without crossing minimum widths', () => {
    document.body.innerHTML = `
      <main class="workspace">
        <section id="catalog-panel"></section>
        <div class="column-resizer" role="separator" data-resizer-index="0" tabindex="0"></div>
        <section id="editor-panel"></section>
        <div class="column-resizer" role="separator" data-resizer-index="1" tabindex="0"></div>
        <section id="dance-panel"></section>
      </main>
    `;
    const workspace = document.querySelector('.workspace');
    workspace.getBoundingClientRect = () => ({ width: 1200 });
    document.defaultView.getComputedStyle = () => {
      const catalog = workspace.style.getPropertyValue('--catalog-width') || '220px';
      const inspector = workspace.style.getPropertyValue('--inspector-width') || '440px';
      const dance = workspace.style.getPropertyValue('--dance-width') || '500px';
      return { gridTemplateColumns: `${catalog} 8px ${inspector} 8px ${dance}` };
    };
    const editor = createEditor({ send: async () => null, documentRef: document });

    editor.wire();

    const firstDivider = document.querySelector('[data-resizer-index="0"]');
    firstDivider.dispatchEvent(new MouseEvent('pointerdown', {
      clientX: 220,
      bubbles: true,
    }));
    document.dispatchEvent(new MouseEvent('pointermove', {
      clientX: 300,
      bubbles: true,
    }));
    document.dispatchEvent(new MouseEvent('pointerup', { bubbles: true }));

    expect(workspace.style.getPropertyValue('--catalog-width')).toBe('300px');
    expect(firstDivider.getAttribute('aria-valuenow')).toBe('300');

    firstDivider.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      bubbles: true,
    }));
    expect(workspace.style.getPropertyValue('--catalog-width')).toBe('290px');

    firstDivider.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      shiftKey: true,
      bubbles: true,
    }));
    firstDivider.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      shiftKey: true,
      bubbles: true,
    }));
    firstDivider.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      shiftKey: true,
      bubbles: true,
    }));
    firstDivider.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      shiftKey: true,
      bubbles: true,
    }));
    expect(workspace.style.getPropertyValue('--catalog-width')).toBe('190px');
  });

  describe('single Apply button', () => {
    test('tree and playback selections initialize each occurrence with its own add-ons', async () => {
      document.body.innerHTML = `
        <div id="dance-tree"></div><div id="figure-meta"></div><div id="addon-controls"></div>
        <input id="anchor-row"><input id="anchor-col"><button id="apply-proposal"></button>
        <button id="playback-prev"></button><button id="playback-next"></button>
        <div id="incoming-floor"></div><div id="outgoing-floor"></div>`;
      const a = { type: 'figure', id: 'a', figureRef: 'First', anchor: [1, 0], addons: ['FirstAddon'] };
      const b = { type: 'figure', id: 'b', figureRef: 'H1DR', anchor: [2, 0], addons: ['E2c'] };
      const root = { type: 'group', id: 'root', kind: 'series', children: [a, b] };
      const floor = { p: { position: [1, -1], dancer: { name: '1m', gender: 'male' } } };
      const trace = [root, a, b].map(node => ({
        nodeId: node.id, kind: node.kind || 'figure', figureRef: node.figureRef,
        status: 'completed', incomingFloor: floor, outgoingFloor: floor, writes: [],
        barRange: [1, 4],
      }));
      const model = { document: { root, metadata: { name: 'Dance' } }, tree: root,
        trace, crips: [], validation: { isValid: true, errors: [] } };
      const send = async path => path === '/api/figures'
        ? { status: 200, body: { figures: [
          { figureRef: 'First', name: 'First', capabilities: {
            validAddons: [{ name: 'FirstAddon', description: 'First description' }] } },
          { figureRef: 'H1DR', name: 'H1DR', capabilities: {
            validAddons: [{ name: 'E2c', description: 'End facing 2 corner' }] } },
        ] } }
        : { status: 200, body: model };
      const editor = createEditor({ send, documentRef: document });
      editor.wire();
      await editor.loadCatalog();
      await editor.loadDance('dance');
      document.querySelector('[data-node-id="a"]').click();
      document.querySelector('[data-node-id="b"]').click();

      expect(document.querySelector('#addon-controls input[value="E2c"]').checked).toBe(true);
      expect(document.querySelector('#figure-meta').textContent).toContain('End facing 2 corner');
      expect(document.querySelector('#anchor-row').value).toBe('2');
      expect(document.querySelector('#apply-proposal').disabled).toBe(true);

      document.querySelector('[data-node-id="a"]').click();
      document.querySelector('#playback-next').click();
      expect(editor.state.selectedNodeId).toBe('b');
      expect(document.querySelector('#addon-controls input[value="E2c"]').checked).toBe(true);
      expect(document.querySelector('#figure-meta').textContent).toContain('End facing 2 corner');
      expect(document.querySelector('#anchor-row').value).toBe('2');
      expect(document.querySelector('#apply-proposal').disabled).toBe(true);
    });

    const setup = async () => {
      document.body.innerHTML = `
        <ul id="fig-list"></ul><select id="dance-select"></select>
        <h3 id="dance-title"></h3><div id="dance-tree"></div><div id="draft-status"></div>
        <p id="incomplete-warning"></p><h3 id="figure-name"></h3><div id="figure-meta"></div>
        <div id="addon-controls"></div><input id="anchor-row"><input id="anchor-col">
        <button id="apply-proposal" disabled></button>
        <pre id="validation-panel"></pre><p id="error-panel"></p>
        <div id="incoming-floor"></div><div id="outgoing-floor"></div>
      `;
      const occurrence = (id, anchor) => ({
        type: 'figure', id, figureRef: 'Step', anchor, addons: [],
      });
      const children = [occurrence('a', [1, 0]), occurrence('b', [2, 1])];
      const root = { type: 'group', id: 'root', kind: 'series', children };
      const model = revision => ({
        document: { revision, status: 'complete', metadata: { name: 'D' }, root },
        tree: root, trace: [], validation: { isValid: true, errors: [] },
      });
      const calls = [];
      const send = async (path, options = {}) => {
        calls.push({ path, body: options.body && JSON.parse(options.body) });
        if (path === '/api/figures') {
          return { status: 200, body: { figures: [{
            figureRef: 'Step', name: 'Step', version: 2,
            capabilities: { validAddons: [{ name: 'Turn' }], bars: 1 },
          }] } };
        }
        if (path === '/api/figures/Step/preview') {
          return { status: 200, body: { incomingFloor: {}, outgoingFloor: {} } };
        }
        if (path === '/api/dances/d') return { status: 200, body: model(0) };
        if (path === '/api/dances/d/nodes/a/preview') {
          return { status: 200, body: { outgoingFloor: {}, crips: [] } };
        }
        if (path.endsWith('/proposals')) {
          return { status: 200, body: { proposal: { proposalId: 'p1', tree: root } } };
        }
        if (path.endsWith('/apply')) return { status: 200, body: model(1) };
        throw new Error(`Unexpected request: ${path}`);
      };
      const editor = createEditor({ send, documentRef: document });
      editor.wire();
      await editor.loadCatalog();
      await editor.loadDance('d');
      return { editor, calls };
    };
    const select = id => {
      document.querySelector(`[data-node-id="${id}"]`).click();
    };

    test('template has exactly one apply button and no propose/cancel buttons', async () => {
      const fs = await import('node:fs');
      const html = fs.readFileSync(new URL('../../templates/index.html', import.meta.url), 'utf8');
      expect(html.match(/id="apply-proposal"/g)).toHaveLength(1);
      ['propose-anchor', 'propose-addons', 'cancel-proposal'].forEach(id => {
        expect(html).not.toContain(`id="${id}"`);
      });
    });

    test('is disabled for catalog figures', async () => {
      await setup();
      document.querySelector('[data-figure-ref="Step"]').click();
      await new Promise(resolve => setTimeout(resolve, 0));
      expect(document.getElementById('apply-proposal').disabled).toBe(true);
    });

    test('is enabled only with a pending change and applies in one step', async () => {
      const { calls } = await setup();
      select('a');
      const button = document.getElementById('apply-proposal');
      expect(button.disabled).toBe(true);
      const row = document.getElementById('anchor-row');
      row.value = '3';
      row.dispatchEvent(new Event('input', { bubbles: true }));
      expect(button.disabled).toBe(true);
      row.value = '1';
      row.dispatchEvent(new Event('input', { bubbles: true }));
      expect(button.disabled).toBe(true);
      row.value = '3';
      row.dispatchEvent(new Event('input', { bubbles: true }));
      const addon = document.querySelector('#addon-controls input[value="Turn"]');
      addon.checked = true;
      addon.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 270));
      expect(button.disabled).toBe(false);

      button.click();
      await new Promise(resolve => setTimeout(resolve, 0));

      const paths = calls.map(call => call.path).filter(path =>
        path.endsWith('/proposals') || path.endsWith('/apply'));
      expect(paths).toEqual(['/api/dances/d/proposals', '/api/dances/d/apply']);
      const proposal = calls.find(call => call.path.endsWith('/proposals')).body;
      expect(proposal.command).toMatchObject({ nodeId: 'a', anchor: [3, 0], addons: ['Turn'] });
      expect(button.disabled).toBe(true);
    });

    test('selecting another figure silently discards pending changes', async () => {
      const { editor, calls } = await setup();
      select('a');
      const row = document.getElementById('anchor-row');
      row.value = '5';
      row.dispatchEvent(new Event('input', { bubbles: true }));
      expect(document.getElementById('apply-proposal').disabled).toBe(true);

      select('b');

      expect(document.getElementById('anchor-row').value).toBe('2');
      expect(document.getElementById('apply-proposal').disabled).toBe(true);
      expect(editor.state.proposal).toBeNull();
      expect(calls.some(call => call.path.endsWith('/proposals'))).toBe(false);
    });
  });

  describe('dance node preview', () => {
    const floor = name => ({ k: { coord: [1, 2], dancer: { name }, facing: 0 } });
    const crip = text => [{ dancer: 'Ann', barRange: [1, 1], text, figureRef: 'Step' }];
    let previews;
    let pending;
    const setup = async () => {
      jest.useFakeTimers();
      previews = [];
      pending = [];
      document.body.innerHTML = `
        <ul id="fig-list"></ul><select id="dance-select"></select>
        <h3 id="dance-title"></h3><div id="dance-tree"></div><div id="draft-status"></div>
        <h3 id="figure-name"></h3><div id="figure-meta"></div>
        <div id="addon-controls"></div><input id="anchor-row"><input id="anchor-col">
        <button id="apply-proposal"></button><p id="error-panel"></p>
        <div id="figure-crips"></div>
        <div id="incoming-floor"></div><p id="outgoing-floor-error" hidden></p>
        <div id="outgoing-floor"></div>
      `;
      const root = {
        type: 'group', id: 'root', kind: 'series',
        children: [{ type: 'figure', id: 'n1', figureRef: 'Step', anchor: [1, 0], addons: [] }],
      };
      const model = {
        document: { revision: 0, status: 'complete', metadata: { name: 'D' }, root },
        tree: root,
        trace: [{
          nodeId: 'n1', kind: 'figure', status: 'ok', barRange: [1, 1],
          incomingFloor: floor('In'), outgoingFloor: floor('Out'),
        }],
        crips: crip('original'),
        validation: { isValid: true, errors: [] },
      };
      const send = async (path, options = {}) => {
        if (path === '/api/figures') {
          return { status: 200, body: { figures: [{
            figureRef: 'Step', name: 'Step', version: 2,
            capabilities: { validAddons: [{ name: 'Turn' }], bars: 1 },
          }] } };
        }
        if (path === '/api/dances/d') return { status: 200, body: model };
        if (path === '/api/dances/d/nodes/n1/preview') {
          const body = JSON.parse(options.body);
          previews.push(body);
          return new Promise(resolve => pending.push(resolve));
        }
        throw new Error(`Unexpected request: ${path}`);
      };
      const editor = createEditor({ send, documentRef: document });
      editor.wire();
      await editor.loadCatalog();
      await editor.loadDance('d');
      document.querySelector('[data-node-id="n1"]').click();
      return editor;
    };
    const respond = (index, outName, text) => pending[index]({
      status: 200,
      body: {
        danceId: 'd', nodeId: 'n1', figureRef: 'Step',
        incomingFloor: floor('In'), outgoingFloor: floor(outName), crips: crip(text),
      },
    });
    const edit = value => {
      const row = document.getElementById('anchor-row');
      row.value = value;
      row.dispatchEvent(new Event('input', { bubbles: true }));
    };
    const flush = async () => { for (let i = 0; i < 5; i += 1) await Promise.resolve(); };
    afterEach(() => jest.useRealTimers());

    test('shows the incoming floor from the trace on selection', async () => {
      await setup();
      expect(document.getElementById('incoming-floor').children.length).toBe(1);
      expect(previews).toHaveLength(0);
    });

    test('debounces input changes into one preview request', async () => {
      await setup();
      edit('2');
      jest.advanceTimersByTime(200);
      edit('3');
      jest.advanceTimersByTime(200);
      expect(previews).toHaveLength(0);
      jest.advanceTimersByTime(60);
      expect(previews).toEqual([{ anchor: [3, 0], addons: [] }]);
    });

    test('add-on changes also trigger a preview', async () => {
      await setup();
      const addon = document.querySelector('#addon-controls input[value="Turn"]');
      addon.checked = true;
      addon.dispatchEvent(new Event('change', { bubbles: true }));
      jest.advanceTimersByTime(260);
      expect(previews).toEqual([{ anchor: [1, 0], addons: ['Turn'] }]);
    });

    test('updates outgoing floor and crips from the response', async () => {
      const editor = await setup();
      edit('2');
      jest.advanceTimersByTime(260);
      respond(0, 'NewOut', 'updated crip');
      await flush();
      expect(document.getElementById('figure-crips').textContent).toContain('updated crip');
      expect(document.getElementById('outgoing-floor').textContent).toContain('NewOut');
      expect(editor.state.nodePreview.outgoingFloor).toEqual(floor('NewOut'));
    });

    test('failed node preview disables Apply, dims the last result and marks affected dancers and instructions', async () => {
      await setup();
      edit('2');
      jest.advanceTimersByTime(260);
      respond(0, 'LastValid', 'last valid instruction');
      await flush();

      edit('3');
      jest.advanceTimersByTime(260);
      pending[1]({
        status: 409,
        body: { error: {
          code: 'addon_conflict',
          message: 'Conflicting add-ons.',
          dancers: ['Ann', 'start position 1'],
        } },
      });
      await flush();

      const outgoing = document.querySelector('#outgoing-floor svg');
      expect(document.getElementById('apply-proposal').disabled).toBe(true);
      expect(document.getElementById('outgoing-floor-error').hidden).toBe(false);
      expect(document.getElementById('outgoing-floor-error').textContent)
        .toContain('Conflicting add-ons.');
      expect(document.getElementById('outgoing-floor').classList.contains('invalid-preview')).toBe(true);
      expect(outgoing.querySelector('[data-dancer="LastValid"]')
        .classList.contains('invalid-preview-marker')).toBe(true);
      expect(document.querySelector('#figure-crips .crip-line').classList.contains('invalid-preview-marker')).toBe(true);
      expect(document.getElementById('outgoing-floor').textContent).toContain('LastValid');
    });

    test('a successful node preview recovers the floor, markers, banner and Apply', async () => {
      await setup();
      edit('2');
      jest.advanceTimersByTime(260);
      pending[0]({
        status: 409,
        body: { error: { code: 'addon_conflict', message: 'Conflicting add-ons.', dancers: ['Ann'] } },
      });
      await flush();
      expect(document.getElementById('apply-proposal').disabled).toBe(true);

      edit('3');
      jest.advanceTimersByTime(260);
      respond(1, 'Recovered', 'recovered instruction');
      await flush();

      expect(document.getElementById('outgoing-floor-error').hidden).toBe(true);
      expect(document.getElementById('outgoing-floor').classList.contains('invalid-preview')).toBe(false);
      expect(document.querySelector('#outgoing-floor [data-dancer="Recovered"]')
        .classList.contains('invalid-preview-marker')).toBe(false);
      expect(document.querySelector('#figure-crips .crip-line').classList.contains('invalid-preview-marker')).toBe(false);
      expect(document.getElementById('apply-proposal').disabled).toBe(false);
    });

    test('ignores stale responses: latest request wins', async () => {
      await setup();
      edit('2');
      jest.advanceTimersByTime(260);
      edit('3');
      jest.advanceTimersByTime(260);
      expect(previews).toHaveLength(2);
      respond(1, 'Latest', 'latest crip');
      await flush();
      respond(0, 'Stale', 'stale crip');
      await flush();
      const crips = document.getElementById('figure-crips').textContent;
      expect(crips).toContain('latest crip');
      expect(crips).not.toContain('stale crip');
      expect(document.getElementById('outgoing-floor').textContent).not.toContain('Stale');
    });
  });
});
