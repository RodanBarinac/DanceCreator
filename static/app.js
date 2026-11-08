import { renderDanceFloor } from './Dancefloor_Render.js';
import { TracePlayback, floorForRenderer } from './Trace_Playback.js';

export async function api(path, options = {}, fetchImpl = globalThis.fetch) {
  const response = await fetchImpl(path, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json')
    ? await response.json()
    : await response.text();
  return { status: response.status, body };
}

export function escapeHtml(value) {
  const text = String(value == null ? '' : value);
  return text.replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[character]));
}

export function formatPos(value) {
  if (!Array.isArray(value) || value.length < 2) return '';
  return `(${value[0]}, ${value[1]})`;
}

export function renderSteps(data) {
  const rows = [];
  const starts = Array.isArray(data.StartPos) ? data.StartPos : [];
  const ends = Array.isArray(data.EndPos) ? data.EndPos : [];
  const facings = Array.isArray(data.EndFacing) ? data.EndFacing : [];
  const partners = Array.isArray(data.Partner) ? data.Partner : [];
  const count = Math.max(starts.length, ends.length, facings.length, partners.length);
  for (let index = 0; index < count; index += 1) {
    rows.push(`<tr><td>${index + 1}</td><td>${escapeHtml(formatPos(starts[index]))}</td>` +
      `<td>${escapeHtml(formatPos(ends[index]))}</td><td>${escapeHtml(formatPos(facings[index]))}</td>` +
      `<td>${escapeHtml(formatPos(partners[index]))}</td></tr>`);
  }
  return rows.length
    ? `<table class="figure-table"><thead><tr><th>#</th><th>Start</th><th>End</th>` +
      `<th>Face</th><th>Partner</th></tr></thead><tbody>${rows.join('')}</tbody></table>`
    : '<p class="empty-note">No step data available.</p>';
}

export function renderCrips(lines, selectedDancer = null, errorDancers = []) {
  const crips = Array.isArray(lines) ? lines : [];
  if (!crips.length) return '<p class="empty-note">No crips available.</p>';
  const errors = new Set((Array.isArray(errorDancers) ? errorDancers : []).map(String));
  return `<ol class="figure-crips">${crips.map(line => {
    const dancer = String(line && line.dancer != null ? line.dancer : '');
    const range = Array.isArray(line && line.barRange) && line.barRange.length === 2
      ? `Bars ${line.barRange[0]}-${line.barRange[1]}`
      : 'Bars unknown';
    const selected = dancer !== '' && dancer === selectedDancer;
    const invalid = dancer !== '' && errors.has(dancer);
    return `<li><button type="button" class="crip-line${selected ? ' selected' : ''}${invalid ? ' invalid-preview-marker' : ''}" ` +
      `data-crip-dancer="${escapeHtml(dancer)}" aria-pressed="${selected}">` +
      `<span class="crip-range">${escapeHtml(range)}</span>` +
      `<span class="crip-dancer">${escapeHtml(dancer)}</span>` +
      `<span class="crip-text">${escapeHtml(line && line.text)}</span></button></li>`;
  }).join('')}</ol>`;
}

function renderTreeNode(node, selectedId) {
  if (!node || typeof node !== 'object') return '';
  const id = escapeHtml(node.id || '');
  const selected = node.id === selectedId;
  const group = node.type === 'group';
  const composite = node.type === 'compositeOccurrence';
  const label = group
    ? `${node.kind || 'group'} group`
    : `${node.figureRef || 'Unknown figure'}${composite ? ' (composite)' : ''}`;
  const descendants = group
    ? (node.children || []).map(child => renderTreeNode(child, selectedId)).join('')
    : composite
      ? renderTreeNode(node.root, selectedId)
      : '';
  return `<li role="treeitem" aria-selected="${selected}" data-node-type="${escapeHtml(node.type || '')}">` +
    `<button type="button" class="tree-node${selected ? ' selected' : ''}" data-node-id="${id}">` +
    `${escapeHtml(label)} <span class="node-id">${id}</span></button>` +
    (descendants ? `<ul role="group">${descendants}</ul>` : '') +
    '</li>';
}

export function renderTree(tree, selectedId = null) {
  if (!tree) return '<p class="empty-note">Select a dance to view its tree.</p>';
  return `<ul class="dance-tree" role="tree">${renderTreeNode(tree, selectedId)}</ul>`;
}

export function renderAddonOptions(capabilities, selected = []) {
  if (!capabilities) {
    return '<fieldset disabled><legend>Add-ons</legend>' +
      '<p class="empty-note">Add-on selection is unsupported for this composite.</p></fieldset>';
  }
  const addons = Array.isArray(capabilities.validAddons) ? capabilities.validAddons : [];
  if (!addons.length) {
    return '<fieldset disabled><legend>Add-ons</legend>' +
      '<p class="empty-note">No add-ons are available.</p></fieldset>';
  }
  return `<fieldset class="addon-options"><legend>Add-ons</legend>${addons.map(addon => {
    const name = typeof addon === 'string' ? addon : addon.name;
    if (typeof name !== 'string') return '';
    const checked = selected.includes(name) ? ' checked' : '';
    return `<label><input type="checkbox" name="addon" value="${escapeHtml(name)}"${checked}>` +
      `${escapeHtml(name)}</label>`;
  }).join('')}</fieldset>`;
}

function findNode(node, nodeId) {
  if (!node || typeof node !== 'object') return null;
  if (node.id === nodeId) return node;
  if (node.type === 'group') {
    for (const child of node.children || []) {
      const found = findNode(child, nodeId);
      if (found) return found;
    }
  } else if (node.type === 'compositeOccurrence') {
    return findNode(node.root, nodeId);
  }
  return null;
}

function findParent(group, nodeId) {
  if (!group || group.type !== 'group') return null;
  for (const child of group.children || []) {
    if (child.id === nodeId) return group;
    const found = child.type === 'group'
      ? findParent(child, nodeId)
      : child.type === 'compositeOccurrence'
        ? findParent(child.root, nodeId)
        : null;
    if (found) return found;
  }
  return null;
}

function selectedAddons(documentRef) {
  if (!documentRef) return [];
  return Array.from(documentRef.querySelectorAll('input[name="addon"]:checked'))
    .map(input => input.value);
}

export function createEditor({
  send = api,
  documentRef = globalThis.document,
  confirmIncomplete = message => globalThis.confirm(message)
} = {}) {
  const state = {
    dances: [],
    figures: [],
    danceId: null,
    readModel: null,
    proposal: null,
    selectedNodeId: null,
    selectedFigureRef: null,
    figurePreview: null,
    previewAnchor: [1, 0],
    previewAddons: [],
    nodePreview: null,
    nodePreviewLoading: false,
    previewLoading: false,
    previewError: null,
    selectedCripDancer: null,
    playback: null,
    error: null,
    notice: ''
  };
  let previewRequestSequence = 0;
  let nodePreviewSequence = 0;
  let nodePreviewTimer = null;
  const NODE_PREVIEW_DEBOUNCE_MS = 250;

  function resetNodePreview() {
    if (nodePreviewTimer) clearTimeout(nodePreviewTimer);
    nodePreviewTimer = null;
    nodePreviewSequence += 1;
    state.nodePreview = null;
    state.nodePreviewLoading = false;
    state.previewError = null;
  }

  function reportPreviewError(body) {
    state.previewError = body && body.error
      ? body.error
      : { code: 'preview_failed', message: 'The preview could not be calculated.' };
    reportError(body && body.error ? body : { error: state.previewError });
  }

  function resolveErrorDancers(floor, dancers) {
    const normalized = floorForRenderer(floor);
    const entries = Object.entries(normalized ? normalized.positions : {});
    const names = new Set((Array.isArray(dancers) ? dancers : []).map(String));
    for (const label of Array.from(names)) {
      const match = label.match(/^start position\s+(\d+)$/i);
      if (!match) continue;
      const entry = entries[Number(match[1]) - 1];
      if (entry) names.add(String((entry[1].dancer || {}).name || entry[0]));
    }
    return Array.from(names);
  }

  function samePreviewInput(preview, pending) {
    return Boolean(preview && pending && preview.nodeId === pending.nodeId &&
      preview.model === state.readModel && preview.anchor &&
      Number(preview.anchor[0]) === Number(pending.anchor[0]) &&
      Number(preview.anchor[1]) === Number(pending.anchor[1]) &&
      Array.isArray(preview.addons) && preview.addons.length === pending.addons.length &&
      preview.addons.every(addon => pending.addons.includes(addon)));
  }

  async function loadNodePreview() {
    nodePreviewTimer = null;
    const root = state.readModel && state.readModel.document
      ? state.readModel.document.root
      : null;
    const selected = root && state.selectedNodeId ? findNode(root, state.selectedNodeId) : null;
    if (!selected || selected.type === 'group' || !state.danceId) return null;
    const row = element('anchor-row');
    const col = element('anchor-col');
    const anchor = [Number(row ? row.value : selected.anchor[0]),
      Number(col ? col.value : selected.anchor[1])];
    if (!anchor.every(Number.isFinite)) {
      state.nodePreviewLoading = false;
      reportPreviewError({ error: {
        code: 'invalid_preview_anchor',
        message: 'Preview anchor coordinates must be numbers.'
      } });
      return null;
    }
    const addons = selectedAddons(documentRef);
    const nodeId = selected.id;
    const requestModel = state.readModel;
    const sequence = ++nodePreviewSequence;
    state.previewError = null;
    state.error = null;
    state.nodePreviewLoading = true;
    render();
    const response = await send(
      `/api/dances/${encodeURIComponent(state.danceId)}/nodes/${encodeURIComponent(nodeId)}/preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anchor, addons })
      }
    );
    if (sequence !== nodePreviewSequence || state.selectedNodeId !== nodeId ||
      state.readModel !== requestModel) return null;
    state.nodePreviewLoading = false;
    if (!response || response.status < 200 || response.status >= 300) {
      reportPreviewError(response && response.body);
      return null;
    }
    state.error = null;
    state.previewError = null;
    state.nodePreview = { ...response.body, nodeId, anchor, addons, model: requestModel };
    render();
    return response.body;
  }

  function scheduleNodePreview() {
    if (!state.selectedNodeId) return;
    if (nodePreviewTimer) clearTimeout(nodePreviewTimer);
    nodePreviewTimer = setTimeout(() => {
      loadNodePreview().catch(error => {
        state.nodePreviewLoading = false;
        reportPreviewError({ error: { code: 'preview_failed', message: error.message } });
      });
    }, NODE_PREVIEW_DEBOUNCE_MS);
  }

  function element(id) {
    return documentRef ? documentRef.getElementById(id) : null;
  }

  function reportError(body) {
    state.error = body && body.error
      ? body.error
      : { code: 'request_failed', message: 'The request could not be completed.' };
    render();
  }

  async function request(path, options) {
    const response = await send(path, options);
    if (!response || response.status < 200 || response.status >= 300) {
      reportError(response && response.body);
      return null;
    }
    state.error = null;
    return response.body;
  }

  function renderCatalog() {
    const list = element('fig-list');
    if (!list) return;
    list.innerHTML = state.figures.map(figure => {
      const selected = figure.figureRef === state.selectedFigureRef ? ' selected' : '';
      const kind = figure.version === 3 ? 'composite' :
        (figure.capabilities && figure.capabilities.bars != null
          ? `${figure.capabilities.bars} bars`
          : 'figure');
      return `<li><button type="button" class="catalog-figure${selected}" ` +
        `data-figure-ref="${escapeHtml(figure.figureRef)}">` +
        `${escapeHtml(figure.name)} <span>${escapeHtml(kind)}</span></button></li>`;
    }).join('');
  }

  function renderInspector() {
    const model = state.readModel;
    const root = model && model.document ? model.document.root : null;
    const selected = root ? findNode(root, state.selectedNodeId) : null;
    const figureRef = selected && selected.figureRef
      ? selected.figureRef
      : state.selectedFigureRef;
    const figure = state.figures.find(item => item.figureRef === figureRef);
    const name = element('figure-name');
    const meta = element('figure-meta');
    const addons = element('addon-controls');
    const anchorRow = element('anchor-row');
    const anchorCol = element('anchor-col');
    const trace = selected && model
      ? (model.trace || []).find(item => item.nodeId === selected.id)
      : null;
    const occurrence = selected && selected.type !== 'group';
    const catalogSelection = Boolean(state.selectedFigureRef && !selected);
    const nodePreview = occurrence && state.nodePreview &&
      state.nodePreview.nodeId === selected.id && state.nodePreview.model === model
      ? state.nodePreview
      : null;
    const pendingNodeChange = occurrence ? pendingChange() : null;
    const shownAnchor = occurrence
      ? pendingNodeChange ? pendingNodeChange.anchor : selected.anchor
      : catalogSelection ? state.previewAnchor : null;
    const shownAddons = occurrence
      ? pendingNodeChange ? pendingNodeChange.addons : selected.addons || []
      : catalogSelection ? state.previewAddons : [];
    const nodeInput = occurrence ? {
      nodeId: selected.id,
      anchor: [Number(anchorRow ? anchorRow.value : selected.anchor[0]),
        Number(anchorCol ? anchorCol.value : selected.anchor[1])],
      addons: selectedAddons(documentRef)
    } : null;
    const nodePreviewCurrent = Boolean(nodeInput && nodeInput.anchor.every(Number.isFinite) &&
      samePreviewInput(nodePreview, nodeInput));
    const previewError = (catalogSelection || occurrence) ? state.previewError : null;

    if (name) name.textContent = figure ? figure.name : (selected ? selected.kind || selected.figureRef : 'No selection');
    if (meta) {
      const addonDescriptions = figure && figure.capabilities &&
        Array.isArray(figure.capabilities.validAddons)
        ? figure.capabilities.validAddons
          .filter(addon => addon && shownAddons.includes(addon.name) && addon.description)
          .map(addon => addon.description)
        : [];
      const figureDescription = figure
        ? [figure.description, ...addonDescriptions].filter(Boolean).join('\n')
        : '';
      const details = figure
        ? `${figureDescription}\nFigure reference: ${figure.figureRef}\nVersion: ${figure.version}`
        : selected
          ? `${selected.type}${selected.kind ? ` (${selected.kind})` : ''}\nNode ID: ${selected.id}`
          : 'Choose a catalog figure or a dance-tree node.';
      meta.textContent = details;
    }
    if (addons) {
      addons.innerHTML = occurrence || catalogSelection
        ? renderAddonOptions(
          figure && figure.capabilities,
          occurrence ? shownAddons : state.previewAddons
        )
        : '<p class="empty-note">Select a figure to inspect add-ons.</p>';
    }
    if (anchorRow) {
      anchorRow.value = occurrence ? shownAnchor[0] : state.previewAnchor[0];
      anchorRow.disabled = !occurrence && !catalogSelection;
    }
    if (anchorCol) {
      anchorCol.value = occurrence ? shownAnchor[1] : state.previewAnchor[1];
      anchorCol.disabled = !occurrence && !catalogSelection;
    }
    const traceStatus = element('trace-status');
    const traceHeading = element('trace-heading');
    const incoming = element('incoming-floor');
    const outgoing = element('outgoing-floor');
    const cripsElement = element('figure-crips');
    const crips = catalogSelection
      ? (state.figurePreview && state.figurePreview.crips) || []
      : nodePreview && Array.isArray(nodePreview.crips)
        ? nodePreview.crips
      : selected && selected.type === 'group'
        ? (model.crips || []).filter(line => {
          if (!line || typeof line.nodeId !== 'string' || !line.nodeId) return false;
          const descendant = findNode(selected, line.nodeId);
          return descendant && descendant.type === 'figure';
        })
      : selected && occurrence && trace
        ? (model.crips || []).filter(line => {
          const composite = selected.type === 'compositeOccurrence';
          const barRangeMatches = !Array.isArray(trace.barRange) || (
            Array.isArray(line.barRange) && (composite
              ? line.barRange[0] >= trace.barRange[0] && line.barRange[1] <= trace.barRange[1]
              : line.barRange[0] === trace.barRange[0] && line.barRange[1] === trace.barRange[1])
          );
          return (composite || line.figureRef === (trace.figureRef || selected.figureRef)) &&
            barRangeMatches;
        })
        : [];
    const outgoingFloor = catalogSelection
      ? state.figurePreview && state.figurePreview.outgoingFloor
      : nodePreview && nodePreview.outgoingFloor
        ? nodePreview.outgoingFloor
        : trace && trace.outgoingFloor;
    const incomingFloor = catalogSelection
      ? state.figurePreview && state.figurePreview.incomingFloor
      : trace && trace.incomingFloor;
    const activeDancers = nodePreview ? nodePreview.activeDancers : trace && trace.activeDancers;
    const referenceCoords = [];
    const referenceFloors = [
      !catalogSelection && model && model.trace && model.trace[0] && model.trace[0].incomingFloor,
      incomingFloor, outgoingFloor
    ];
    for (const floor of referenceFloors) {
      const normalized = floorForRenderer(floor);
      if (!normalized) continue;
      for (const position of Object.values(normalized.positions)) {
        const coord = position.coord.map(Number);
        if (coord.length >= 2 && coord.every(Number.isFinite)) referenceCoords.push(coord);
      }
    }
    if (catalogSelection && state.figurePreview && Number.isFinite(state.figurePreview.couples)) {
      referenceCoords.push([1, -1], [state.figurePreview.couples, 1]);
    }
    const referenceBounds = referenceCoords.length ? [
      Math.min(...referenceCoords.map(coord => coord[0])),
      Math.min(-1, ...referenceCoords.map(coord => coord[1])),
      Math.max(...referenceCoords.map(coord => coord[0])),
      Math.max(1, ...referenceCoords.map(coord => coord[1]))
    ] : null;
    const errorDancers = resolveErrorDancers(
      outgoingFloor,
      previewError && previewError.dancers
    );
    if (cripsElement) {
      cripsElement.innerHTML = renderCrips(crips, state.selectedCripDancer, errorDancers);
    }
    if (traceStatus) {
      traceStatus.textContent = trace
        ? `${trace.kind}: ${trace.status}${trace.barRange ? ` (bars ${trace.barRange[0]}–${trace.barRange[1]})` : ''}` +
          (!Array.isArray(activeDancers) ? ' — Active dancers unavailable; showing full floor.' : '')
        : catalogSelection
          ? `Incoming and outgoing floors for ${figure ? figure.name : figureRef}.`
          : 'No execution snapshot for this selection.';
    }
    if (traceHeading) {
      traceHeading.textContent = catalogSelection
        ? `Figure preview: ${figure ? figure.name : figureRef}`
        : 'Execution snapshot';
    }
    const previewStatus = element('figure-preview-status');
    if (previewStatus) {
      previewStatus.textContent = catalogSelection
        ? state.previewLoading
          ? 'Calculating figure preview...'
          : state.figurePreview
            ? `Catalog preview - minimal declared participant set (${state.figurePreview.couples} ` +
              `couple${state.figurePreview.couples === 1 ? '' : 's'}).`
            : 'Figure preview unavailable.'
        : '';
    }
    const outgoingError = element('outgoing-floor-error');
    if (outgoingError) {
      outgoingError.hidden = !previewError;
      outgoingError.textContent = previewError ? previewError.message || 'Preview failed.' : '';
    }
    const renderSnapshot = (target, floor, label, interactive = false, snapshotOptions = {}) => {
      if (!target) return;
      target.replaceChildren();
      target.classList.toggle('invalid-preview', Boolean(snapshotOptions.invalid));
      const normalized = floorForRenderer(floor);
      if (normalized) {
        if (Array.isArray(activeDancers) && !catalogSelection) {
          const active = new Set(activeDancers);
          normalized.positions = Object.fromEntries(Object.entries(normalized.positions)
            .filter(([key, position]) => active.has(String(position.dancer.name || key))));
        }
        const selectedPositions = interactive && state.selectedCripDancer
          ? Object.entries(normalized.positions).reduce((matches, [key, position]) => {
            if ((position.dancer.name || key) === state.selectedCripDancer) {
              matches.push(position.coord);
            }
            return matches;
          }, [])
          : [];
        target.appendChild(renderDanceFloor(normalized, {
          width: 300,
          height: 210,
          contextLabel: label,
          contextType: 'occurrence-snapshot',
          referenceBounds: snapshotOptions.referenceBounds,
          showSetLines: true,
          selectedPositions,
          errorDancers: snapshotOptions.errorDancers || [],
          errorPositions: snapshotOptions.errorPositions || [],
          onDancerSelect: interactive
            ? dancer => {
              state.selectedCripDancer = dancer;
              render();
            }
            : undefined
        }));
      }
    };
    renderSnapshot(
      incoming,
      incomingFloor,
      catalogSelection ? null : 'Incoming dancefloor',
      true,
      {
        referenceBounds
      }
    );
    const outgoingInvalid = Boolean(previewError || state.previewLoading ||
      (occurrence && (state.nodePreviewLoading ||
        ((pendingNodeChange || nodePreview) && !nodePreviewCurrent))));
    renderSnapshot(
      outgoing,
      outgoingFloor,
      catalogSelection ? null : 'Outgoing dancefloor',
      false,
      {
        invalid: outgoingInvalid,
        errorDancers,
        referenceBounds
      }
    );
    const deleteButton = element('delete-node');
    if (deleteButton) deleteButton.disabled = !selected || selected.id === root.id || Boolean(state.proposal);
    updateApplyButton();
  }

  function pendingChange() {
    const root = state.readModel && state.readModel.document
      ? state.readModel.document.root
      : null;
    const selected = root && state.selectedNodeId ? findNode(root, state.selectedNodeId) : null;
    if (!selected || selected.type === 'group' || !Array.isArray(selected.anchor)) return null;
    const row = element('anchor-row');
    const col = element('anchor-col');
    if (!row || !col) return null;
    const anchor = [Number(row.value), Number(col.value)];
    if (!anchor.every(Number.isFinite)) {
      state.nodePreviewLoading = false;
      reportPreviewError({ error: {
        code: 'invalid_preview_anchor',
        message: 'Preview anchor coordinates must be numbers.'
      } });
      return null;
    }
    const addons = selectedAddons(documentRef);
    const current = selected.addons || [];
    const changed = anchor[0] !== Number(selected.anchor[0]) ||
      anchor[1] !== Number(selected.anchor[1]) ||
      addons.length !== current.length ||
      addons.some(addon => !current.includes(addon));
    return changed ? { nodeId: selected.id, anchor, addons } : null;
  }

  function updateApplyButton() {
    const button = element('apply-proposal');
    if (!button) return;
    const pending = pendingChange();
    button.disabled = !pending || !samePreviewInput(state.nodePreview, pending) ||
      state.nodePreviewLoading || Boolean(state.previewError);
  }

  async function applyPending() {
    const pending = pendingChange();
    if (!pending) return null;
    const proposal = await propose({
      type: 'updateOccurrence',
      nodeId: pending.nodeId,
      anchor: pending.anchor,
      addons: pending.addons
    });
    if (!proposal) return null;
    const applied = await applyProposal();
    if (!applied) {
      state.proposal = null;
      render();
    }
    return applied;
  }

  function renderPlayback() {
    const playback = state.playback;
    const step = playback && playback.current;
    const canvas = element('dance-floor-canvas');
    const status = element('floor-status');
    const position = element('playback-position');
    const warning = element('playback-warning');
    const branches = element('branch-floors');
    const previous = element('playback-prev');
    const next = element('playback-next');
    if (previous) previous.disabled = !playback || playback.index <= 0;
    if (next) next.disabled = !playback || playback.index >= playback.steps.length - 1;
    if (position) {
      position.textContent = playback
        ? `${playback.index + 1} / ${playback.steps.length}`
        : '0 / 0';
    }
    if (!canvas || !step) return;

    const record = step.record;
    const contextLabel = step.kind === 'initial'
      ? 'Initial floor'
      : `${record && record.figureRef ? record.figureRef : record && record.kind} ` +
        `${step.kind} ${step.nodeId} - ${step.status}`;
    if (!step.floor) {
      canvas.textContent = 'No valid floor snapshot.';
      if (status) status.textContent = contextLabel;
      if (branches) branches.replaceChildren();
      if (warning) {
        warning.hidden = !(step.status === 'failed' || step.conflict);
        warning.textContent = step.conflict
          ? `Conflict: ${step.conflict.code}. No combined group result exists.`
          : step.status === 'failed'
            ? 'Execution failed and no floor snapshot is available.'
            : '';
      }
      return;
    }
    canvas.replaceChildren(renderDanceFloor(step.floor, {
      width: 640,
      height: 360,
      contextLabel,
      contextType: step.kind,
      selectedNodeId: step.nodeId,
      selectedPositions: record && record.writes ? record.writes : []
    }));
    if (status) {
      status.textContent = step.kind === 'initial'
        ? 'Initial dancefloor state.'
        : `${contextLabel}${step.barRange ? ` (bars ${step.barRange[0]}-${step.barRange[1]})` : ''}`;
    }
    if (warning) {
      warning.hidden = !(step.status === 'failed' || step.conflict);
      warning.textContent = step.conflict
        ? `Conflict: ${step.conflict.code}. Showing the last valid floor; no combined group result exists.`
        : step.status === 'failed'
          ? 'Execution failed. Showing the last valid floor.'
          : '';
    }
    if (branches) {
      branches.replaceChildren();
      step.branches.forEach(branch => {
        const section = documentRef.createElement('section');
        section.className = 'branch-floor';
        const heading = documentRef.createElement('h4');
        heading.textContent = `Isolated branch ${branch.nodeId} - ${branch.status}`;
        const target = documentRef.createElement('div');
        target.className = 'branch-floor-canvas';
        if (branch.floor) {
          target.appendChild(renderDanceFloor(branch.floor, {
            width: 320,
            height: 220,
            contextLabel: `Isolated branch ${branch.nodeId}`,
            contextType: 'parallel-branch',
            selectedNodeId: branch.nodeId,
            selectedPositions: branch.writes
          }));
        }
        section.append(heading, target);
        branches.appendChild(section);
      });
    }
  }

  function render() {
    if (!documentRef) return;
    const catalogSelection = Boolean(state.selectedFigureRef && state.selectedNodeId === null);
    renderCatalog();
    const select = element('dance-select');
    if (select) {
      const selectedId = state.danceId || '';
      select.innerHTML = '<option value="">Select a dance</option>' +
        state.dances.map(dance =>
          `<option value="${escapeHtml(dance.id)}">${escapeHtml(dance.name)}</option>`
        ).join('');
      select.value = selectedId;
    }
    const title = element('dance-title');
    if (title) {
      const metadata = state.readModel && state.readModel.document.metadata;
      title.textContent = metadata ? metadata.name || '' : '';
    }
    const tree = element('dance-tree');
    if (tree) {
      const projection = state.proposal
        ? state.proposal.tree
        : state.readModel && state.readModel.tree;
      tree.innerHTML = renderTree(projection, state.selectedNodeId);
    }
    const model = state.readModel;
    const incomplete = Boolean(model && model.document.status === 'incomplete');
    const draft = element('draft-status');
    if (draft) {
      draft.textContent = catalogSelection
        ? 'Catalog figure'
        : incomplete
          ? 'INCOMPLETE DRAFT'
          : model
            ? 'Complete dance'
            : '';
      draft.classList.toggle('warning', !catalogSelection && incomplete);
    }
    const warning = element('incomplete-warning');
    if (warning) {
      warning.hidden = catalogSelection || !incomplete;
      warning.textContent = !catalogSelection && incomplete
        ? `Unresolved figures: ${(model.document.unresolvedReferences || []).join(', ')}`
        : '';
    }
    const validation = element('validation-panel');
    if (validation) {
      const report = model && model.validation;
      const errors = report && report.errors ? report.errors : [];
      validation.hidden = catalogSelection;
      validation.textContent = !catalogSelection && errors.length
        ? errors.map(issue => `${issue.code}: ${issue.message}`).join('\n')
        : !catalogSelection && report && report.isValid
          ? 'No validation errors.'
          : '';
      validation.classList.toggle('error', !catalogSelection && errors.length > 0);
    }
    const errorPanel = element('error-panel');
    if (errorPanel) {
      errorPanel.hidden = !state.error;
      errorPanel.textContent = state.error
        ? `${state.error.code || 'error'}: ${state.error.message || 'Request failed.'}`
        : '';
    }
    renderPlayback();
    const notice = element('status');
    if (notice) notice.textContent = state.error
      ? 'Action failed'
      : state.notice || (model ? `Revision ${model.revision}` : 'Ready');
    const save = element('save-dance');
    const undo = element('undo-dance');
    const redo = element('redo-dance');
    [save, undo, redo].forEach(button => {
      if (button) button.disabled = !model;
    });
    const insert = element('insert-figure');
    if (insert) insert.disabled = !model || !state.selectedFigureRef || Boolean(state.proposal);
    const series = element('add-series');
    const parallel = element('add-parallel');
    [series, parallel].forEach(button => {
      if (button) button.disabled = !model || Boolean(state.proposal);
    });
    ['move-up', 'move-down'].forEach(id => {
      const button = element(id);
      if (button) button.disabled = !model || !state.selectedNodeId || Boolean(state.proposal);
    });
    renderInspector();
  }

  async function loadCatalog() {
    const body = await request('/api/figures');
    if (!body) return;
    state.figures = body.figures || [];
    render();
  }

  async function loadFigurePreview() {
    if (!state.selectedFigureRef) return null;
    const figureRef = state.selectedFigureRef;
    const sequence = ++previewRequestSequence;
    const rowInput = element('anchor-row');
    const columnInput = element('anchor-col');
    const row = Number(rowInput ? rowInput.value : state.previewAnchor[0]);
    const column = Number(columnInput ? columnInput.value : state.previewAnchor[1]);
    if (!Number.isFinite(row) || !Number.isFinite(column)) {
      state.previewLoading = false;
      state.error = {
        code: 'invalid_preview_anchor',
        message: 'Preview anchor coordinates must be numbers.'
      };
      state.previewError = state.error;
      render();
      return null;
    }
    state.previewAnchor = [row, column];
    state.previewError = null;
    state.error = null;
    state.previewLoading = true;
    render();
    let body;
    try {
      const response = await send(`/api/figures/${encodeURIComponent(figureRef)}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          anchor: state.previewAnchor,
          addons: state.previewAddons
        })
      });
      if (sequence !== previewRequestSequence || state.selectedFigureRef !== figureRef) return null;
      if (!response || response.status < 200 || response.status >= 300) {
        state.previewLoading = false;
        reportPreviewError(response && response.body);
        return null;
      }
      state.error = null;
      body = response.body;
    } catch (error) {
      if (sequence === previewRequestSequence) {
        state.previewLoading = false;
        reportPreviewError({ error: { code: 'preview_failed', message: error.message } });
      }
      return null;
    }
    if (sequence !== previewRequestSequence) return null;
    state.previewLoading = false;
    if (!body || state.selectedFigureRef !== figureRef) {
      state.previewError = state.error || {
        code: 'preview_failed', message: 'The preview could not be calculated.'
      };
      render();
      return null;
    }
    state.previewError = null;
    state.figurePreview = body;
    render();
    return body;
  }

  async function loadDances() {
    const body = await request('/api/dances');
    if (!body) return;
    state.dances = body.dances || [];
    render();
    if (state.dances.length && !state.danceId) {
      await loadDance(state.dances[0].id);
    }
  }

  async function loadDance(danceId) {
    const body = await request(`/api/dances/${encodeURIComponent(danceId)}`);
    if (!body) return;
    state.danceId = danceId;
    state.readModel = body;
    resetNodePreview();
    state.selectedCripDancer = null;
    state.proposal = null;
    state.previewError = null;
    state.selectedNodeId = body.document.root.id;
    state.playback = new TracePlayback(body);
    state.playback.selectNode(state.selectedNodeId);
    state.notice = '';
    render();
  }

  async function propose(command) {
    if (!state.danceId || !state.readModel) return null;
    const body = await request(`/api/dances/${encodeURIComponent(state.danceId)}/proposals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        baseRevision: state.readModel.document.revision,
        command
      })
    });
    if (!body) return null;
    state.proposal = body.proposal;
    return state.proposal;
  }

  async function applyProposal() {
    if (!state.proposal || !state.readModel) return null;
    const body = await request(`/api/dances/${encodeURIComponent(state.danceId)}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        baseRevision: state.readModel.document.revision,
        proposalId: state.proposal.proposalId
      })
    });
    if (!body) return null;
    state.readModel = body;
    resetNodePreview();
    state.proposal = null;
    state.playback = new TracePlayback(body);
    state.playback.selectNode(state.selectedNodeId);
    state.notice = 'Changes applied.';
    render();
    return body;
  }

  async function historyAction(action) {
    if (!state.danceId || !state.readModel) return null;
    const body = await request(
      `/api/dances/${encodeURIComponent(state.danceId)}/${action}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseRevision: state.readModel.document.revision })
      }
    );
    if (!body) return null;
    state.readModel = body;
    resetNodePreview();
    state.proposal = null;
    state.playback = new TracePlayback(body);
    state.playback.selectNode(state.selectedNodeId);
    state.notice = action === 'undo' ? 'Undo complete.' : 'Redo complete.';
    render();
    return body;
  }

  async function save() {
    if (!state.danceId || !state.readModel) return null;
    const saveDocument = async confirmed => request(
      `/api/dances/${encodeURIComponent(state.danceId)}/save`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseRevision: state.readModel.document.revision,
          document: state.readModel.document,
          ...(confirmed ? { confirmIncomplete: true } : {})
        })
      }
    );
    let body = await saveDocument(false);
    if (!body && state.error && state.error.code === 'incomplete_confirmation_required') {
      if (!confirmIncomplete('Save this dance as an incomplete draft?')) return null;
      body = await saveDocument(true);
    }
    if (!body) return null;
    state.readModel = body;
    resetNodePreview();
    state.proposal = null;
    state.playback = new TracePlayback(body);
    state.playback.selectNode(state.selectedNodeId);
    state.notice = 'Dance saved.';
    render();
    return body;
  }

  function wire() {
    if (!documentRef) return;
    const bind = (id, handler) => {
      const button = element(id);
      if (!button) return;
      button.addEventListener('click', async () => {
        try {
          await handler();
        } catch (error) {
          reportError({ error: { code: 'request_failed', message: error.message } });
        }
      });
    };
    const cripsElement = element('figure-crips');
    if (cripsElement) {
      cripsElement.addEventListener('click', event => {
        const line = event.target.closest('[data-crip-dancer]');
        if (!line || !cripsElement.contains(line)) return;
        state.selectedCripDancer = line.dataset.cripDancer;
        render();
      });
    }
    const tree = element('dance-tree');
    if (tree) {
      tree.addEventListener('click', event => {
        const button = event.target.closest('[data-node-id]');
        if (!button) return;
        state.selectedNodeId = button.dataset.nodeId;
        state.proposal = null;
        state.selectedFigureRef = null;
        state.figurePreview = null;
        state.selectedCripDancer = null;
        state.error = null;
        state.notice = '';
        const selectedNode = state.readModel && state.readModel.document
          ? findNode(state.readModel.document.root, state.selectedNodeId)
          : null;
        if (selectedNode && selectedNode.type !== 'group') {
          const row = element('anchor-row');
          const column = element('anchor-col');
          if (row) row.value = selectedNode.anchor[0];
          if (column) column.value = selectedNode.anchor[1];
          const selected = new Set(selectedNode.addons || []);
          if (documentRef) documentRef.querySelectorAll('input[name="addon"]').forEach(input => {
            input.checked = selected.has(input.value);
          });
        }
        resetNodePreview();
        previewRequestSequence += 1;
        if (state.playback) state.playback.selectNode(state.selectedNodeId);
        render();
      });
    }
    const catalog = element('fig-list');
    if (catalog) {
      catalog.addEventListener('click', async event => {
        const button = event.target.closest('[data-figure-ref]');
        if (!button) return;
        state.selectedFigureRef = button.dataset.figureRef;
        state.selectedNodeId = null;
        state.selectedCripDancer = null;
        state.proposal = null;
        state.error = null;
        state.previewError = null;
        state.notice = '';
        state.previewAnchor = [1, 0];
        state.previewAddons = [];
        state.figurePreview = null;
        state.previewLoading = false;
        resetNodePreview();
        render();
        try {
          await loadFigurePreview();
        } catch (error) {
          reportError({ error: { code: 'preview_failed', message: error.message } });
        }
      });
    }
    const previewAnchorChanged = async () => {
      if (!state.selectedFigureRef || state.selectedNodeId) return;
      try {
        await loadFigurePreview();
      } catch (error) {
        reportError({ error: { code: 'preview_failed', message: error.message } });
      }
    };
    ['anchor-row', 'anchor-col'].forEach(id => {
      const input = element(id);
      if (input) input.addEventListener('change', previewAnchorChanged);
    });
    const addonControls = element('addon-controls');
    if (addonControls) addonControls.addEventListener('change', async event => {
      if (!state.selectedFigureRef || state.selectedNodeId) return;
      if (!event.target.matches('input[name="addon"]')) return;
      state.previewAddons = selectedAddons(documentRef);
      try {
        await loadFigurePreview();
      } catch (error) {
        reportError({ error: { code: 'preview_failed', message: error.message } });
      }
    });
    const danceSelect = element('dance-select');
    if (danceSelect) danceSelect.addEventListener('change', event => {
      if (event.target.value) loadDance(event.target.value);
    });
    ['anchor-row', 'anchor-col'].forEach(id => {
      const input = element(id);
      if (input) input.addEventListener('input', () => {
        updateApplyButton();
        scheduleNodePreview();
      });
    });
    if (addonControls) addonControls.addEventListener('change', () => {
      updateApplyButton();
      scheduleNodePreview();
    });
    bind('apply-proposal', applyPending);
    bind('undo-dance', () => historyAction('undo'));
    bind('redo-dance', () => historyAction('redo'));
    bind('save-dance', save);
    bind('playback-prev', () => {
      const step = state.playback && state.playback.previous();
      state.selectedNodeId = step && step.nodeId;
      render();
    });
    bind('playback-next', () => {
      const step = state.playback && state.playback.next();
      state.selectedNodeId = step && step.nodeId;
      render();
    });
    bind('insert-figure', () => {
      const root = state.readModel.document.root;
      const selected = findNode(root, state.selectedNodeId);
      const parent = selected && selected.type === 'group' ? selected : root;
      const anchor = [Number(element('anchor-row').value), Number(element('anchor-col').value)];
      return propose({
        type: 'insertOccurrence',
        parentGroupId: parent.id,
        figureRef: state.selectedFigureRef,
        index: (parent.children || []).length,
        anchor,
        addons: []
      });
    });
    ['series', 'parallel'].forEach(kind => bind(`add-${kind}`, () => {
      const root = state.readModel.document.root;
      const selected = findNode(root, state.selectedNodeId);
      const parent = selected && selected.type === 'group' ? selected : root;
      return propose({
        type: 'createGroup',
        parentGroupId: parent.id,
        kind,
        index: (parent.children || []).length
      });
    }));
    bind('delete-node', () => propose({
      type: 'deleteNode',
      nodeId: state.selectedNodeId
    }));
    ['move-up', 'move-down'].forEach(direction => bind(direction, () => {
      const root = state.readModel.document.root;
      const parent = findParent(root, state.selectedNodeId);
      if (!parent) return null;
      const index = parent.children.findIndex(child => child.id === state.selectedNodeId);
      const offset = direction === 'move-up' ? -1 : 1;
      const nextIndex = Math.max(0, Math.min(parent.children.length - 1, index + offset));
      return propose({ type: 'reorderNode', nodeId: state.selectedNodeId, index: nextIndex });
    }));
    const filter = element('catalog-search');
    if (filter) filter.addEventListener('input', () => {
      const query = filter.value.trim().toLowerCase();
      documentRef.querySelectorAll('#fig-list [data-figure-ref]').forEach(button => {
        button.closest('li').hidden = !button.textContent.toLowerCase().includes(query);
      });
    });
    wireColumnResizers();
  }

  function wireColumnResizers() {
    const workspace = documentRef.querySelector('.workspace');
    if (!workspace) return;
    const separators = Array.from(workspace.querySelectorAll('.column-resizer'));
    if (separators.length !== 2) return;

    const minimums = [190, 320, 320];
    const currentWidths = () => {
      const tracks = documentRef.defaultView
        ? documentRef.defaultView.getComputedStyle(workspace).gridTemplateColumns
          .trim().split(/\s+/).map(value => Number.parseFloat(value))
        : [];
      if (tracks.length === 5 && tracks.every(Number.isFinite)) {
        return [tracks[0], tracks[2], tracks[4]];
      }
      const available = Math.max(
        minimums.reduce((sum, width) => sum + width, 0),
        workspace.getBoundingClientRect().width - 56
      );
      const flexible = available - minimums.reduce((sum, width) => sum + width, 0);
      return minimums.map((width, index) =>
        width + flexible * [0.2, 0.4, 0.4][index]
      );
    };
    const setWidths = widths => {
      workspace.style.setProperty('--catalog-width', `${widths[0]}px`);
      workspace.style.setProperty('--inspector-width', `${widths[1]}px`);
      workspace.style.setProperty('--dance-width', `${widths[2]}px`);
      separators.forEach((separator, index) => {
        separator.setAttribute('aria-valuemin', String(minimums[index]));
        separator.setAttribute(
          'aria-valuemax',
          String(widths[index] + widths[index + 1] - minimums[index + 1])
        );
        separator.setAttribute('aria-valuenow', String(Math.round(widths[index])));
      });
    };
    const adjustedWidths = (widths, index, delta) => {
      const bounded = Math.max(
        minimums[index] - widths[index],
        Math.min(widths[index + 1] - minimums[index + 1], delta)
      );
      const next = [...widths];
      next[index] += bounded;
      next[index + 1] -= bounded;
      return next;
    };

    let drag = null;
    separators.forEach((separator, index) => {
      separator.addEventListener('pointerdown', event => {
        drag = { index, startX: event.clientX, widths: currentWidths() };
        separator.classList.add('resizing');
        if (separator.setPointerCapture && Number.isInteger(event.pointerId)) {
          separator.setPointerCapture(event.pointerId);
        }
        event.preventDefault();
      });
      separator.addEventListener('keydown', event => {
        if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
        const step = event.shiftKey ? 40 : 10;
        const delta = event.key === 'ArrowRight' ? step : -step;
        setWidths(adjustedWidths(currentWidths(), index, delta));
        event.preventDefault();
      });
    });

    documentRef.addEventListener('pointermove', event => {
      if (!drag) return;
      setWidths(adjustedWidths(
        drag.widths,
        drag.index,
        event.clientX - drag.startX
      ));
    });
    const stopDragging = () => {
      if (!drag) return;
      separators[drag.index].classList.remove('resizing');
      drag = null;
    };
    documentRef.addEventListener('pointerup', stopDragging);
    documentRef.addEventListener('pointercancel', stopDragging);
    separators.forEach((separator, index) => {
      separator.setAttribute('aria-valuemin', String(minimums[index]));
      separator.setAttribute('aria-valuenow', String(Math.round(currentWidths()[index])));
    });
  }

  return {
    state,
    render,
    wire,
    loadCatalog,
    loadDances,
    loadDance,
    propose,
    applyProposal,
    applyPending,
    undo: () => historyAction('undo'),
    redo: () => historyAction('redo'),
    save
  };
}

if (
  typeof document !== 'undefined' &&
  document.querySelector('[data-dance-creator-app]')
) {
  const editor = createEditor();
  window.danceCreatorEditor = editor;
  const start = async () => {
    editor.wire();
    await Promise.all([editor.loadCatalog(), editor.loadDances()]);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
}
