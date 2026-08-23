// Minimal frontend to interact with backend API

let currentFigureSummary = null;
let currentDanceName = null;
let currentDanceCouples = 3;

async function api(path, opts) {
 const res = await fetch(path, opts);
 const contentType = res.headers.get('content-type') || '';
 let body = null;
 if (contentType.includes('application/json')) body = await res.json();
 else body = await res.text();
 return { status: res.status, body };
}

function escapeHtml(value) {
 const text = String(value == null ? '' : value);
 return text.replace(/[&<>"']/g, ch => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
 }[ch]));
}

function formatPos(value) {
 if (!Array.isArray(value) || value.length < 2) return '';
 return `(${value[0]}, ${value[1]})`;
}

function normalizeAnchor(anchor) {
 if (!Array.isArray(anchor) || anchor.length < 2) return [1, 1];
 var row = parseInt(anchor[0], 10);
 var col = parseInt(anchor[1], 10);
 if (!isFinite(row) || row < 1) row = 1;
 if (!isFinite(col) || col < 1) col = 1;
 return [row, col];
}

function getCanvasOptions(anchorOverride, addonsOverride) {
 var rowInput = document.getElementById('anchor-row');
 var colInput = document.getElementById('anchor-col');
 var parsedRow = rowInput ? parseInt(rowInput.value || '1', 10) : 1;
 var parsedCol = colInput ? parseInt(colInput.value || '1', 10) : 1;
 var anchor = normalizeAnchor(anchorOverride || [parsedRow, parsedCol]);
 var addons = addonsOverride;
 if (typeof addons === 'undefined') {
  addons = {};
  var addonInput = document.getElementById('addons-json');
  if (addonInput) {
   try { addons = JSON.parse(addonInput.value || '{}'); } catch (e) { addons = {}; }
  }
 }
 return { anchor: anchor, addons: addons };
}

function renderFloorCanvas(floor) {
 var canvas = document.getElementById('dance-floor-canvas');
 var status = document.getElementById('floor-status');
 if (!canvas) return;

 if (!floor) {
  canvas.innerHTML = '<text x="16" y="24" class="empty-note">No floor data.</text>';
  if (status) status.textContent = 'No floor loaded';
  return;
 }

 var couples = parseInt(floor.couples || currentDanceCouples || 3, 10);
 if (!isFinite(couples) || couples < 1) couples = 3;
 currentDanceCouples = couples;

 var cellW = 120;
 var cellH = 60;
 var pad = 18;
 var cols = 3;
 var width = pad * 2 + cols * cellW;
 var height = pad * 2 + couples * cellH + 24;
 canvas.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
 canvas.setAttribute('width', '100%');
 canvas.setAttribute('height', Math.max(180, height));

 var svg = [];
 svg.push('<rect x="0" y="0" width="' + width + '" height="' + height + '" fill="#ffffff" stroke="#ddd"/>');
 svg.push('<text x="' + pad + '" y="14" font-size="11" fill="#666">Floor: ' + escapeHtml(floor.name || '') + ' | Bar ' + escapeHtml(floor.tick || 0) + '</text>');
 svg.push('<text x="' + (pad + 10) + '" y="' + (pad + 24) + '" font-size="10" fill="#666">Men</text>');
 svg.push('<text x="' + (pad + cellW + 10) + '" y="' + (pad + 24) + '" font-size="10" fill="#666">Between</text>');
 svg.push('<text x="' + (pad + cellW * 2 + 10) + '" y="' + (pad + 24) + '" font-size="10" fill="#666">Lady</text>');

 for (var r = 1; r <= couples; r += 1) {
  var rowY = pad + 24 + (r - 1) * cellH;
  svg.push('<text x="' + (pad - 4) + '" y="' + (rowY + 36) + '" font-size="10" text-anchor="end" fill="#666">' + r + '</text>');
  for (var c = 1; c <= cols; c += 1) {
   var x = pad + (c - 1) * cellW;
   svg.push('<rect x="' + x + '" y="' + rowY + '" width="' + cellW + '" height="' + cellH + '" fill="#fafafa" stroke="#ddd"/>');
  }
 }

 var positions = floor.positions || {};
 Object.keys(positions).forEach(function (key) {
  var item = positions[key] || {};
  var coord = Array.isArray(item.coord) ? item.coord : null;
  if (!coord || coord.length < 2) return;
  var row = parseInt(coord[0], 10);
  var col = parseInt(coord[1], 10);
  if (!isFinite(row) || !isFinite(col)) return;
  var posX = pad + (col - 1) * cellW + cellW / 2;
  var posY = pad + 24 + (row - 1) * cellH + cellH / 2;
  var dancer = item.dancer || {};
  var label = dancer.name || key;
  svg.push('<circle cx="' + posX + '" cy="' + posY + '" r="16" fill="#e3f2fd" stroke="#1565c0" stroke-width="2"/>');
  svg.push('<text x="' + posX + '" y="' + (posY + 4) + '" text-anchor="middle" font-size="10" fill="#0d47a1">' + escapeHtml(label) + '</text>');
 });

 canvas.innerHTML = svg.join('');
 if (status) status.textContent = 'Loaded floor: ' + (floor.name || '') + ' (bar ' + (floor.tick || 0) + ')';
}

async function renderFigureOnCanvas(figureName, options) {
 options = options || {};
 var body = {
  figure: figureName,
  anchor: options.anchor || [1, 1],
  addons: options.addons || {},
  couples: options.couples || currentDanceCouples || 3,
  dance_name: options.dance_name || currentDanceName || 'preview'
 };
 var res = await api('/api/dancefloor/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body)
 });
 if (res.status === 200) {
  renderFloorCanvas(res.body.floor);
  return res.body.floor;
 }
 if (res.status === 409) {
  showConflict(res.body);
  return null;
 }
 alert('Execution failed: ' + (res.body && res.body.error));
 return null;
}

function renderSteps(data) {
 const rows = [];
 const starts = Array.isArray(data.StartPos) ? data.StartPos : [];
 const ends = Array.isArray(data.EndPos) ? data.EndPos : [];
 const facings = Array.isArray(data.Faceing) ? data.Faceing : Array.isArray(data.Facing) ? data.Facing : [];
 const partners = Array.isArray(data.Partner) ? data.Partner : [];
 const count = Math.max(starts.length, ends.length, facings.length, partners.length);

 for (let i = 0; i < count; i += 1) {
  rows.push(
   `<tr>
     <td>${i + 1}</td>
     <td>${escapeHtml(formatPos(starts[i]))}</td>
     <td>${escapeHtml(formatPos(ends[i]))}</td>
     <td>${escapeHtml(formatPos(facings[i]))}</td>
     <td>${escapeHtml(formatPos(partners[i]))}</td>
   </tr>`
  );
 }

 return rows.length
  ? `<table class="figure-table">
       <thead><tr><th>#</th><th>Start</th><th>End</th><th>Face</th><th>Partner</th></tr></thead>
       <tbody>${rows.join('')}</tbody>
     </table>`
  : '<p class="empty-note">No step data available.</p>';
}

function renderCrips(data) {
 const crips = Array.isArray(data.CriptDesc) ? data.CriptDesc : [];
 if (!crips.length) return '<p class="empty-note">No crips available.</p>';
 return `<ol class="figure-crips">${crips.map(crip => `<li>${escapeHtml(crip)}</li>`).join('')}</ol>`;
}

function renderDanceSummary(data) {
 const summary = document.getElementById('dance-summary');
 if (!summary) return;
 summary.innerHTML = `
 <div><strong>Name:</strong> ${escapeHtml(data.Name || data.name || '')}</div>
 <div><strong>Version:</strong> ${escapeHtml(data.Version || '')}</div>
 <div><strong>Shape:</strong> ${escapeHtml(data.shape || data.Shape || '')}</div>
 <div><strong>Description:</strong> ${escapeHtml(data.Desc || '')}</div>
 `;
}

function renderFigureDetail(data) {
 const header = document.getElementById('figure-name');
 const meta = document.getElementById('figure-meta');
 const steps = document.getElementById('figure-steps');
 const crips = document.getElementById('figure-crips');
 const json = document.getElementById('figure-json');

 header.textContent = data.Name || data.name || 'Figure';
 meta.innerHTML = `
  <div><strong>Version:</strong> ${escapeHtml(data.Version || '')}</div>
  <div><strong>Bars:</strong> ${escapeHtml(data.Bars || '')}</div>
  <div><strong>Formation:</strong> ${escapeHtml(data.Formation || data.Type || '')}</div>
  <div><strong>Description:</strong> ${escapeHtml(data.Desc || '')}</div>
 `;
 steps.innerHTML = renderSteps(data);
 crips.innerHTML = renderCrips(data);
 json.textContent = JSON.stringify(data, null, 2);
}

async function loadFigures() {
 const r = await api('/api/figures');
 if (r.status !== 200) { console.error('Failed to load figures'); return; }
 const list = document.getElementById('fig-list');
 list.innerHTML = '';
 currentFigureSummary = null;
 r.body.forEach(f => {
   if (!f.file || f.file.endsWith('figure.schema.json')) return;
   const li = document.createElement('li');
   li.textContent = `${f.Name || f.file} (${f.Bars || '?'} bars)`;
   li.dataset.figureKey = f.key || f.file.replace('.json', '');
   li.dataset.figureFile = f.file.replace('.json','');
   li.dataset.formation = f.Formation || f.Type || 'Other';
   li.addEventListener('click', onFigureClick);
   list.appendChild(li);
   if (!currentFigureSummary) currentFigureSummary = f;
 });

 if (currentFigureSummary) {
   await showFigure(currentFigureSummary.key || currentFigureSummary.file.replace('.json', ''), list.querySelector('li'));
 }
}

async function loadDances() {
 const r = await api('/api/dances');
 if (r.status !== 200) { console.error('Failed to load dances'); return; }
 const sel = document.getElementById('dance-select');
 sel.innerHTML = '<option value="">-- Select a dance --</option>';
 r.body.forEach(d => {
   const opt = document.createElement('option');
   opt.value = d.file.replace('.json','');
   opt.textContent = d.Name || d.file;
   sel.appendChild(opt);
 });
  
 // Remove old listener if any
 const newSel = sel.cloneNode(true);
 sel.parentNode.replaceChild(newSel, sel);
  
 // Add new listener
 const currentSel = document.getElementById('dance-select');
 currentSel.addEventListener('change', (e) => {
   if (e.target.value) initJsTree(e.target.value);
 });
  
 // Load first dance if available
 if (r.body.length) {
   currentSel.value = r.body[0].file.replace('.json','');
   initJsTree(r.body[0].file.replace('.json',''));
 }
}

async function initJsTree(danceName) {
 const r = await api(`/api/dances/${encodeURIComponent(danceName)}`);
 const treeDiv = document.getElementById('dance-tree');
 const title = document.getElementById('dance-title');
 if (r.status !== 200) { treeDiv.textContent = 'Failed to load tree'; return; }
 currentDanceName = danceName;
 currentDanceCouples = parseInt((r.body.dance && r.body.dance.shape ? String(r.body.dance.shape).split('/')[0] : '3'), 10);
 if (!isFinite(currentDanceCouples) || currentDanceCouples < 1) currentDanceCouples = 3;
 if (title) title.textContent = r.body.dance && (r.body.dance.Name || r.body.dance.name) || danceName;
 renderDanceSummary(r.body.dance || {});
 const treeData = r.body.tree;
 // init jstree
 // destroy existing
 try { $(treeDiv).jstree(true).destroy(); } catch(e) {}
 $(treeDiv).jstree({ 'core': { 'data': [ treeData ], 'check_callback': true }, 'plugins': ['dnd','wholerow'] });

 $(treeDiv).off('select_node.jstree');
 $(treeDiv).on('select_node.jstree', async function (e, data) {
  var node = data && data.node ? data.node : null;
  if (!node || !node.data || !node.data.figureName) return;
  document.body.dataset.selectedFigure = node.data.figureName;
  await showFigure(node.data.figureName, null);
 });

 // when node moved, send updated tree to backend
 $(treeDiv).on('move_node.jstree', function(e, data) {
   const tree = $(treeDiv).jstree(true).get_json('#', { 'flat': false });
   // send to backend
   fetch(`/api/dances/${encodeURIComponent(currentDanceName)}/tree`, {
     method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ tree: tree[0] })
   }).then(r=>r.json()).then(j=>{ if (j.status==='ok') alert('Tree updated'); else alert('Update failed'); }).catch(err=>{ alert('Update failed'); });
 });
}

async function showFigure(identifier, selectedElement, canvasOptions) {
 const detail = document.getElementById('figure-json');
 const header = document.getElementById('figure-name');
 const r = await api(`/api/figures/${encodeURIComponent(identifier)}`);
 if (r.status !== 200) {
  detail.textContent = 'Error loading figure';
  return;
 }
 renderFigureDetail(r.body);
 document.body.dataset.selectedFigure = identifier;

 const items = document.querySelectorAll('#fig-list li');
 items.forEach(li => li.classList.remove('selected'));
 if (selectedElement) {
  selectedElement.classList.add('selected');
 } else {
  items.forEach(li => {
   if (li.dataset.figureKey === identifier || li.dataset.figureFile === identifier) li.classList.add('selected');
  });
 }
}

async function onFigureClick(e) {
 const identifier = e.currentTarget.dataset.figureKey || e.currentTarget.dataset.figureFile;
 await showFigure(identifier, e.currentTarget);
}

async function previewFigure() {
 alert('Floor rendering is paused for now.');
}

async function executeFigure() {
 alert('Floor rendering is paused for now.');
}

function showConflict(body) {
 const modal = document.getElementById('conflict-modal');
 modal.classList.remove('hidden');
 document.getElementById('conflict-message').textContent = body.error || 'Konflikt';
 document.getElementById('conflict-details').textContent = JSON.stringify(body.conflicts, null, 2);
}

function hideConflict() {
 document.getElementById('conflict-modal').classList.add('hidden');
}

function wire() {
 document.getElementById('execute-figure').addEventListener('click', executeFigure);
 document.getElementById('preview-figure').addEventListener('click', previewFigure);
 document.getElementById('dismiss').addEventListener('click', hideConflict);
 document.getElementById('inspect-tree').addEventListener('click', ()=>{ console.log('Inspect tree'); hideConflict(); });
 document.getElementById('edit-params').addEventListener('click', ()=>{ console.log('Edit params'); hideConflict(); });
}

window.addEventListener('DOMContentLoaded', async () => {
 await loadFigures();
 await loadDances();
 wire();
});