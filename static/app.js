// Minimal frontend to interact with backend API

async function api(path, opts) {
 const res = await fetch(path, opts);
 const contentType = res.headers.get('content-type') || '';
 let body = null;
 if (contentType.includes('application/json')) body = await res.json();
 else body = await res.text();
 return { status: res.status, body };
}

async function loadFigures() {
 const r = await api('/api/figures');
 if (r.status !== 200) { console.error('Failed to load figures'); return; }
 const list = document.getElementById('fig-list');
 list.innerHTML = '';
 r.body.forEach(f => {
   if (!f.file || f.file.endsWith('figure.schema.json')) return; // skip schema file
   const li = document.createElement('li');
   li.textContent = `${f.Name || f.file} (${f.Bars || '?'} bars)`;
   li.dataset.file = f.file.replace('.json','');
   li.dataset.formation = f.Formation || f.Type || 'Other';
   li.addEventListener('click', onFigureClick);
   list.appendChild(li);
 });
}

async function loadDances() {
 const r = await api('/api/dances');
 if (r.status !== 200) { console.error('Failed to load dances'); return; }
 const sel = document.getElementById('dance-select');
 sel.innerHTML = '';
 r.body.forEach(d => {
   const opt = document.createElement('option');
   opt.value = d.file.replace('.json','');
   opt.textContent = d.Name || d.file;
   sel.appendChild(opt);
 });
 sel.addEventListener('change', () => initJsTree(sel.value));
 if (r.body.length) initJsTree(r.body[0].file.replace('.json',''));
}

async function initJsTree(danceName) {
 const r = await api(`/api/dances/${encodeURIComponent(danceName)}`);
 const treeDiv = document.getElementById('dance-tree');
 if (r.status !== 200) { treeDiv.textContent = 'Failed to load tree'; return; }
 const treeData = r.body.tree;
 // init jstree
 // destroy existing
 try { $(treeDiv).jstree(true).destroy(); } catch(e) {}
 $(treeDiv).jstree({ 'core': { 'data': [ treeData ], 'check_callback': true }, 'plugins': ['dnd','wholerow'] });

 // when node moved, send updated tree to backend
 $(treeDiv).on('move_node.jstree', function(e, data) {
   const tree = $(treeDiv).jstree(true).get_json('#', { 'flat': false });
   // send to backend
   fetch(`/api/dances/${encodeURIComponent(danceName)}/tree`, {
     method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ tree: tree[0] })
   }).then(r=>r.json()).then(j=>{ if (j.status==='ok') alert('Tree updated'); else alert('Update failed'); }).catch(err=>{ alert('Update failed'); });
 });
}

async function onFigureClick(e) {
 const name = e.currentTarget.dataset.file;
 const detail = document.getElementById('figure-json');
 const header = document.getElementById('figure-name');
 const r = await api(`/api/figures/${encodeURIComponent(name)}`);
 if (r.status !== 200) { detail.textContent = 'Error loading figure'; return; }
 header.textContent = r.body.Name || name;
 detail.textContent = JSON.stringify(r.body, null, 2);
 // store current selected name
 document.body.dataset.selectedFigure = name;
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