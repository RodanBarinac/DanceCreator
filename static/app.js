// Minimal frontend to interact with backend API

let currentFigureSummary = null;
let currentDanceName = null;

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

function renderDanceNode(node) {
 const children = Array.isArray(node.children) ? node.children : [];
 const label = node.type === 'group'
 ? `${node.text}${node.data && node.data.mode ? ` (${node.data.mode})` : ''}`
 : node.text;
 const anchor = node.data && Array.isArray(node.data.anchor) ? ` ${formatPos(node.data.anchor)}` : '';
 const suffix = node.type === 'figure' ? anchor : '';
 const childHtml = children.length ? `<ul>${children.map(renderDanceNode).join('')}</ul>` : '';
 return `<li><span class="dance-node">${escapeHtml(label)}${escapeHtml(suffix)}</span>${childHtml}</li>`;
}

function renderDanceSequence(tree) {
 const panel = document.getElementById('dance-sequence');
 if (!panel) return;
 if (!tree) {
 panel.innerHTML = '<p class="empty-note">No dance selected.</p>';
 return;
 }
 const children = Array.isArray(tree.children) ? tree.children : [];
 panel.innerHTML = children.length
 ? `<ol class="dance-sequence-list">${children.map(renderDanceNode).join('')}</ol>`
 : '<p class="empty-note">No sequence data available.</p>';
}

function renderDanceJson(data) {
 const json = document.getElementById('dance-json');
 if (!json) return;
 json.textContent = JSON.stringify(data || {}, null, 2);
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
 if (title) title.textContent = r.body.dance && (r.body.dance.Name || r.body.dance.name) || danceName;
 renderDanceSummary(r.body.dance || {});
 renderDanceSequence(r.body.tree);
 renderDanceJson(r.body.dance || {});
 const treeData = r.body.tree;
 // init jstree
 // destroy existing
 try { $(treeDiv).jstree(true).destroy(); } catch(e) {}
 $(treeDiv).jstree({ 'core': { 'data': [ treeData ], 'check_callback': true }, 'plugins': ['dnd','wholerow'] });

 // when node moved, send updated tree to backend
 $(treeDiv).on('move_node.jstree', function(e, data) {
   const tree = $(treeDiv).jstree(true).get_json('#', { 'flat': false });
   // send to backend
   fetch(`/api/dances/${encodeURIComponent(currentDanceName)}/tree`, {
     method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ tree: tree[0] })
   }).then(r=>r.json()).then(j=>{ if (j.status==='ok') alert('Tree updated'); else alert('Update failed'); }).catch(err=>{ alert('Update failed'); });
 });
}

async function showFigure(identifier, selectedElement) {
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
 const name = document.body.dataset.selectedFigure;
 if (!name) { alert('No figure selected'); return; }
 const anchor = [parseInt(document.getElementById('anchor-row').value||0,10), parseInt(document.getElementById('anchor-col').value||0,10)];
 let addons = {};
 try { addons = JSON.parse(document.getElementById('addons-json').value); } catch(e) { alert('Invalid addons JSON'); return; }
 const body = { figure: name, anchor: anchor, addons: addons, couples: 3, dance_name: 'preview' };
 const res = await api('/api/dancefloor/execute', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
 if (res.status === 200) {
   console.log('Preview floor', res.body.floor);
   alert('Preview succeeded (see console)');
 } else if (res.status === 409) {
   showConflict(res.body);
 } else {
   alert('Preview failed: '+(res.body && res.body.error));
 }
}

async function executeFigure() {
 const name = document.body.dataset.selectedFigure;
 if (!name) { alert('No figure selected'); return; }
 const anchor = [parseInt(document.getElementById('anchor-row').value||0,10), parseInt(document.getElementById('anchor-col').value||0,10)];
 let addons = {};
 try { addons = JSON.parse(document.getElementById('addons-json').value); } catch(e) { alert('Invalid addons JSON'); return; }
 const body = { figure: name, anchor: anchor, addons: addons, couples: 3, dance_name: 'UI-exec' };
 const res = await api('/api/dancefloor/execute', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
 if (res.status === 200) {
   document.getElementById('status').textContent = 'Executed';
   alert('Execution succeeded. Check console for floor.');
   console.log(res.body.floor);
 } else if (res.status === 409) {
   showConflict(res.body);
 } else {
   alert('Execution failed: ' + (res.body && res.body.error));
 }
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