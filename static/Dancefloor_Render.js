// dancefloorRenderer.js
// Usage: import { renderDanceFloor } from './dancefloorRenderer.js'

const COLOR_PALETTE = ['#0072B2','#E69F00','#CC79A7','#009E73','#56B4E9','#D55E00','#F0E442','#0072B2'];

export function degFromFacing(facing) {
  if (typeof facing === 'number') return facing;
  if (Array.isArray(facing) && facing.length >= 2) {
    const [dx, dy] = facing;
    // SVG +y is down; atan2(dy, dx) gives angle in radians; convert to degrees
    return Math.atan2(dy, dx) * 180 / Math.PI;
  }
  return 0;
}

function createSVG(width, height, viewBox) {
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('width', String(width));
  svg.setAttribute('height', String(height));
  if (viewBox) svg.setAttribute('viewBox', viewBox);
  svg.setAttribute('role','img');
  return svg;
}

function makeDefs(svg) {
  const svgNS = 'http://www.w3.org/2000/svg';
  const defs = document.createElementNS(svgNS, 'defs');
  // common arrow marker (but for rotation inside groups, we'll also use polygon)
  const marker = document.createElementNS(svgNS, 'marker');
  marker.setAttribute('id','df-arrow');
  marker.setAttribute('markerWidth','8');
  marker.setAttribute('markerHeight','8');
  marker.setAttribute('refX','6');
  marker.setAttribute('refY','3');
  marker.setAttribute('orient','auto');
  const path = document.createElementNS(svgNS,'path');
  path.setAttribute('d','M0,0 L6,3 L0,6 Z');
  path.setAttribute('fill','#111827');
  marker.appendChild(path);
  defs.appendChild(marker);
  svg.appendChild(defs);
  return defs;
}

export function mapLogicalToPixel(coord, bbox, pxSize, padding) {
  // coord: [x,y] logical
  const [minX, minY, maxX, maxY] = bbox;
  const [pxW, pxH] = pxSize;
  const pad = padding || 0;
  const scaleX = (pxW - 2*pad) / Math.max(1e-6, (maxX - minX));
  const scaleY = (pxH - 2*pad) / Math.max(1e-6, (maxY - minY));
  const scale = Math.min(scaleX, scaleY);
  // center if necessary
  const offsetX = pad + (pxW - 2*pad - (maxX-minX)*scale)/2;
  const offsetY = pad + (pxH - 2*pad - (maxY-minY)*scale)/2;
  const x = offsetX + (coord[0] - minX) * scale;
  const y = offsetY + (coord[1] - minY) * scale;
  return {x,y,scale,scaleX,scaleY,offsetX,offsetY};
}

export function computeBBox(positions, fallback = {minX:0,minY:0,maxX:5,maxY:5}) {
  // positions: object with keys -> { coord: [x,y], dancer: {...}, facing: ... }
  const coords = [];
  for (const key in positions) {
    try {
      const pos = positions[key];
      const c = pos.coord || pos.coordArray || null;
      if (Array.isArray(c) && c.length >= 2) coords.push([Number(c[0]), Number(c[1])]);
    } catch(e){}
  }
  if (coords.length === 0) {
    return [fallback.minX, fallback.minY, fallback.maxX, fallback.maxY];
  }
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  coords.forEach(([x,y])=>{
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  });
  // add small margin
  const margin = 0.8; // logical units
  return [minX - margin, minY - margin, maxX + margin, maxY + margin];
}

// main renderer
export function renderDanceFloor(floorJson, options = {}) {
  // options: {width, height, paddingPx, palette}
  const width = options.width || 800;
  const height = options.height || 600;
  const paddingPx = options.paddingPx != null ? options.paddingPx : 28;
  const palette = options.palette || COLOR_PALETTE;
  const tokenDiameter = 0.45;

  const svg = createSVG(width, height, `0 0 ${width} ${height}`);
  svg.classList.add('dancefloor-svg');
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.setAttribute('aria-label', options.contextLabel || 'Dance floor state');
  if (options.selectedNodeId) {
    svg.setAttribute('data-selected-node-id', String(options.selectedNodeId));
  }
  makeDefs(svg);
  const svgNS = 'http://www.w3.org/2000/svg';

  const positions = floorJson.positions || {};
  const displayCoord = coord => [Number(coord[0]), -Number(coord[1])];
  const displayPositions = Object.fromEntries(
    Object.entries(positions).map(([key, position]) => [
      key,
      { ...position, coord: Array.isArray(position.coord) ? displayCoord(position.coord) : null }
    ])
  );
  const bbox = computeBBox(displayPositions, {
    minX: 0,
    minY: -(options.couples || 4),
    maxX: options.couples || 4,
    maxY: 0
  });
  // map function closure
  const mapper = coord => mapLogicalToPixel(coord, bbox, [width, height], paddingPx);

  // background / header
  const header = document.createElementNS(svgNS,'rect');
  header.setAttribute('x','0'); header.setAttribute('y','0');
  header.setAttribute('width',String(width)); header.setAttribute('height','44');
  header.setAttribute('fill','#ffffff');
  svg.appendChild(header);

  if (options.contextLabel) {
    const context = document.createElementNS(svgNS, 'text');
    context.setAttribute('x', String(paddingPx));
    context.setAttribute('y', '18');
    context.setAttribute('font-size', '12');
    context.setAttribute('fill', '#374151');
    context.setAttribute('data-context', options.contextType || 'floor');
    context.textContent = options.contextLabel;
    svg.appendChild(context);
  }

  const sideLabels = [
    ['Ladies', 30],
    ['Men', height - 8]
  ];
  sideLabels.forEach(([label, y]) => {
    const text = document.createElementNS(svgNS, 'text');
    text.setAttribute('x', String(width / 2));
    text.setAttribute('y', String(y));
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('font-size', '16');
    text.setAttribute('fill', '#111827');
    text.textContent = label;
    svg.appendChild(text);
  });

  const minRow = Math.ceil(bbox[0]);
  const maxRow = Math.floor(bbox[2]);
  for (let r = minRow; r <= maxRow; r++) {
    const p = mapper([r, bbox[3] - 0.2]);
    const t = document.createElementNS(svgNS,'text');
    t.setAttribute('x', String(p.x));
    t.setAttribute('y', String(p.y + 6));
    t.setAttribute('text-anchor','middle');
    t.setAttribute('font-size','12');
    t.setAttribute('fill','#374151');
    t.setAttribute('font-weight','700');
    t.textContent = String(r);
    svg.appendChild(t);
  }

  // helper: couple index -> color
  function coupleColor(index) {
    return palette[(index - 1) % palette.length];
  }

  const selectedPositions = new Set(
    (options.selectedPositions || []).map(position =>
      `${Number(position[0])},${Number(position[1])}`
    )
  );
  const errorDancers = new Set((options.errorDancers || []).map(String));
  const errorPositions = new Set((options.errorPositions || []).map(position =>
    `${Number(position[0])},${Number(position[1])}`
  ));

  // render tokens
  let positionIndex = 0;
  for (const key in positions) {
    positionIndex += 1;
    const pos = positions[key];
    const rawCoord = Array.isArray(pos.coord) ? pos.coord.map(Number) : null;
    if (!rawCoord || rawCoord.length < 2 || !rawCoord.every(Number.isFinite)) continue;
    const coord = displayCoord(rawCoord);
    // compute pixel center and scale
    const {x,y,scale} = mapper(coord);
    const dancer = pos.dancer || {};
    const coupleIdentity = String(dancer.name || key);
    const m = coupleIdentity.match(/^(\d+)[mw]$/i) || String(key).match(/^(\d+)[mw]$/i);
    let coupleIndex = m ? Number(m[1]) : null;
    if (!coupleIndex && Number.isFinite(coord[0])) coupleIndex = Math.round(coord[0]);
    if (!coupleIndex) coupleIndex = 1;
    const color = coupleColor(coupleIndex);
    const isErrorDancer = errorDancers.has(String(dancer.name || key)) ||
      errorDancers.has(`start position ${positionIndex}`) ||
      errorPositions.has(`${rawCoord[0]},${rawCoord[1]}`);

    const genderValue = (dancer.gender || '').toString().toLowerCase();
    const gender = genderValue.startsWith('m') ? 'M' : genderValue.startsWith('f') ? 'W' : 'D';
    const pxRadius = tokenDiameter * scale / 2;
    const tokenGroup = document.createElementNS(svgNS,'g');
    let rotatableShape = null;
    if (isErrorDancer) {
      tokenGroup.classList.add('invalid-preview-marker');
      const outline = document.createElementNS(svgNS, 'circle');
      outline.setAttribute('cx', '0');
      outline.setAttribute('cy', '0');
      outline.setAttribute('r', String(pxRadius * 1.45));
      outline.setAttribute('fill', 'none');
      outline.setAttribute('stroke', '#c62828');
      outline.setAttribute('stroke-width', '4');
      outline.setAttribute('class', 'error-outline');
      tokenGroup.appendChild(outline);
    }
    tokenGroup.setAttribute('transform', `translate(${x}, ${y})`);
    tokenGroup.setAttribute('data-position', `${rawCoord[0]},${rawCoord[1]}`);
    tokenGroup.setAttribute('data-dancer', String(dancer.name || key));
    tokenGroup.setAttribute(
      'data-selected',
      String(selectedPositions.has(`${rawCoord[0]},${rawCoord[1]}`))
    );
    tokenGroup.setAttribute(
      'aria-label',
      `${dancer.name || key}, position ${rawCoord[0]}, ${rawCoord[1]}, facing ${String(pos.facing || 0)}`
    );
    if (typeof options.onDancerSelect === 'function') {
      tokenGroup.setAttribute('role', 'button');
      tokenGroup.setAttribute('tabindex', '0');
      const selectDancer = () => options.onDancerSelect(dancer.name || key, [...rawCoord]);
      tokenGroup.addEventListener('click', selectDancer);
      tokenGroup.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectDancer();
        }
      });
    }

    if (gender === 'M') {
      const c = document.createElementNS(svgNS,'circle');
      c.setAttribute('cx','0'); c.setAttribute('cy','0');
      c.setAttribute('r', String(pxRadius));
      c.setAttribute('fill', color);
      c.setAttribute('stroke','#111827');
      c.setAttribute('stroke-width','2');
      if (selectedPositions.has(`${rawCoord[0]},${rawCoord[1]}`)) {
        c.setAttribute('stroke', '#d84315');
        c.setAttribute('stroke-width', '4');
      }
      tokenGroup.appendChild(c);
    } else if (gender === 'W') {
      // square centered
      const s = document.createElementNS(svgNS,'rect');
      const side = pxRadius * 2;
      s.setAttribute('x', String(-side/2));
      s.setAttribute('y', String(-side/2));
      s.setAttribute('width', String(side));
      s.setAttribute('height', String(side));
      s.setAttribute('rx','4');
      s.setAttribute('fill', color);
      s.setAttribute('stroke','#111827');
      s.setAttribute('stroke-width','2');
      if (selectedPositions.has(`${rawCoord[0]},${rawCoord[1]}`)) {
        s.setAttribute('stroke', '#d84315');
        s.setAttribute('stroke-width', '4');
      }
      tokenGroup.appendChild(s);
      rotatableShape = s;
    } else {
      const diamond = document.createElementNS(svgNS, 'polygon');
      diamond.setAttribute(
        'points',
        `0,${-pxRadius} ${pxRadius},0 0,${pxRadius} ${-pxRadius},0`
      );
      diamond.setAttribute('fill', color);
      diamond.setAttribute(
        'stroke',
        selectedPositions.has(`${rawCoord[0]},${rawCoord[1]}`) ? '#d84315' : '#111827'
      );
      diamond.setAttribute(
        'stroke-width',
        selectedPositions.has(`${rawCoord[0]},${rawCoord[1]}`) ? '4' : '2'
      );
      tokenGroup.appendChild(diamond);
      rotatableShape = diamond;
    }

    // facing: compute rotation angle. If facing is vector or degrees. Default 0 (right).
    const facing = pos.facing;
    const angle = Array.isArray(facing) && facing.length >= 2
      ? degFromFacing([
        Number(facing[0]) - rawCoord[0],
        -(Number(facing[1]) - rawCoord[1])
      ])
      : degFromFacing(facing || 0);
    if (rotatableShape) {
      rotatableShape.setAttribute('transform', `rotate(${angle})`);
    }
    // Draw arrowhead as small polygon placed at token edge and rotated with tokenGroup
    const arrow = document.createElementNS(svgNS,'polygon');
    // position arrow at (token radius + small gap) along +X axis, but the whole group will be rotated by angle
    const arrowDist = pxRadius + scale * 0.06;
    const ax = arrowDist;
    const ay = 0;
    // small triangular arrow pointing outward (triangle with tip at (ax+6, 0))
    const tip = ax + scale * 0.12;
    const base1Y = -scale * 0.04;
    const base2Y = scale * 0.04;
    arrow.setAttribute('points', `${tip},0 ${ax},${base1Y} ${ax},${base2Y}`);
    arrow.setAttribute('fill','#111827');
    // wrap arrow in rotation group so arrow rotates around center
    const arrowWrap = document.createElementNS(svgNS,'g');
    arrowWrap.setAttribute('transform', `rotate(${angle})`);
    arrowWrap.setAttribute('data-facing', String(angle));
    arrowWrap.appendChild(arrow);
    tokenGroup.appendChild(arrowWrap);

    // accessibility: role and title
    const title = document.createElementNS(svgNS,'title');
    title.textContent = `${dancer.name || key} (${gender}) at ${rawCoord[0]}, ${rawCoord[1]}, facing ${angle} degrees`;
    tokenGroup.appendChild(title);

    svg.appendChild(tokenGroup);
  }

  return svg;
}

/* Example usage:
import { renderDanceFloor } from './dancefloorRenderer.js';
const floor = await fetch('/api/dancefloor/init', {method:'POST', body: JSON.stringify({couples:4})}).then(r=>r.json());
const svgEl = renderDanceFloor(floor, {width:900,height:600, paddingPx:24});
document.getElementById('middle').innerHTML=''; // panel
document.getElementById('middle').appendChild(svgEl);
*/
