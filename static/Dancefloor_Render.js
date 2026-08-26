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
  // options: {width, height, paddingPx, tokenLogicalRadius, palette}
  const width = options.width || 800;
  const height = options.height || 600;
  const paddingPx = options.paddingPx != null ? options.paddingPx : 28;
  const palette = options.palette || COLOR_PALETTE;
  const tokenLogicalRadius = options.tokenLogicalRadius != null ? options.tokenLogicalRadius : 0.5;

  const svg = createSVG(width, height, `0 0 ${width} ${height}`);
  makeDefs(svg);
  const svgNS = 'http://www.w3.org/2000/svg';

  const positions = floorJson.positions || {};
  const bbox = computeBBox(positions, {minX:0,minY:0,maxX:options.couples||4,maxY:options.couples||4});
  // map function closure
  const mapper = coord => mapLogicalToPixel(coord, bbox, [width, height], paddingPx);

  // background / header
  const header = document.createElementNS(svgNS,'rect');
  header.setAttribute('x','0'); header.setAttribute('y','0');
  header.setAttribute('width',String(width)); header.setAttribute('height','44');
  header.setAttribute('fill','#ffffff');
  svg.appendChild(header);

  // men/woman simple headers: compute approximate column centers using bbox
  const colLeft = bbox[0];
  const colRight = bbox[2];
  // we will place "Men" above x ~ 1/3 and "Woman" above x ~ 2/3 of logical span
  const logicalSpanX = (bbox[2] - bbox[0]) || 1;
  const menLogicalX = bbox[0] + logicalSpanX * 0.33;
  const womLogicalX = bbox[0] + logicalSpanX * 0.66;
  const menPos = mapper([menLogicalX, bbox[1] - 0.8]);
  const womPos = mapper([womLogicalX, bbox[1] - 0.8]);

  const menText = document.createElementNS(svgNS,'text');
  menText.setAttribute('x', String(menPos.x));
  menText.setAttribute('y', '30');
  menText.setAttribute('text-anchor','middle');
  menText.setAttribute('font-size','20');
  menText.setAttribute('fill','#111827');
  menText.textContent = 'Men';
  svg.appendChild(menText);

  const womText = document.createElementNS(svgNS,'text');
  womText.setAttribute('x', String(womPos.x));
  womText.setAttribute('y', '30');
  womText.setAttribute('text-anchor','middle');
  womText.setAttribute('font-size','20');
  womText.setAttribute('fill','#111827');
  womText.textContent = 'Woman';
  svg.appendChild(womText);

  // rows labels: use integer y positions within bbox (if floor has rows 1..N)
  // find integer y values in range
  const minY = Math.ceil(bbox[1]);
  const maxY = Math.floor(bbox[3]);
  for (let r = minY; r <= maxY; r++) {
    const p = mapper([bbox[0]-0.8, r]);
    const t = document.createElementNS(svgNS,'text');
    t.setAttribute('x', String(p.x));
    t.setAttribute('y', String(p.y + 6)); // tweak for baseline
    t.setAttribute('text-anchor','middle');
    t.setAttribute('font-size','18');
    t.setAttribute('fill','#374151');
    t.setAttribute('font-weight','700');
    t.textContent = String(r);
    svg.appendChild(t);
  }

  // helper: couple index -> color
  function coupleColor(index) {
    return palette[(index - 1) % palette.length];
  }

  // render tokens
  for (const key in positions) {
    const pos = positions[key];
    const coord = Array.isArray(pos.coord) ? pos.coord.map(Number) : null;
    if (!coord) continue;
    // compute pixel center and scale
    const {x,y,scale} = mapper(coord);
    // decide couple index: use rounded x (row) if obvious or try reading from key (like '1m' => 1)
    let coupleIndex = null;
    const m = String(key).match(/^(\d+)/);
    if (m) coupleIndex = Number(m[1]);
    if (!coupleIndex && Number.isFinite(coord[0])) coupleIndex = Math.round(coord[0]);
    if (!coupleIndex) coupleIndex = 1;
    const color = coupleColor(coupleIndex);

    const dancer = pos.dancer || {};
    const gender = (dancer.gender || '').toString().toLowerCase().startsWith('m') ? 'M' : 'W';
    // compute pixel radius so tokenLogicalRadius (logical units) maps to px
    const unitMap = mapLogicalToPixel([bbox[0]+1, bbox[1]], bbox, [width,height], paddingPx);
    // distance in px for one logical unit: use scale returned by mapper (scale)
    const pxPerLogical = unitMap.scale;
    const pxRadius = Math.max(8, tokenLogicalRadius * pxPerLogical); // min size
    const tokenGroup = document.createElementNS(svgNS,'g');
    tokenGroup.setAttribute('transform', `translate(${x}, ${y})`);

    if (gender === 'M') {
      const c = document.createElementNS(svgNS,'circle');
      c.setAttribute('cx','0'); c.setAttribute('cy','0');
      c.setAttribute('r', String(pxRadius));
      c.setAttribute('fill', color);
      c.setAttribute('stroke','#111827');
      c.setAttribute('stroke-width','2');
      tokenGroup.appendChild(c);
    } else {
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
      tokenGroup.appendChild(s);
    }

    // facing: compute rotation angle. If facing is vector or degrees. Default 0 (right).
    const facing = pos.facing;
    const angle = degFromFacing(facing || 0);
    // Draw arrowhead as small polygon placed at token edge and rotated with tokenGroup
    const arrow = document.createElementNS(svgNS,'polygon');
    // position arrow at (token radius + small gap) along +X axis, but the whole group will be rotated by angle
    const arrowDist = pxRadius + Math.max(6, Math.round(pxPerLogical*0.15));
    const ax = arrowDist;
    const ay = 0;
    // small triangular arrow pointing outward (triangle with tip at (ax+6, 0))
    const tip = ax + Math.max(6, Math.round(pxPerLogical*0.2));
    const base1Y = -Math.max(4, Math.round(pxPerLogical*0.12));
    const base2Y = Math.max(4, Math.round(pxPerLogical*0.12));
    arrow.setAttribute('points', `${tip},0 ${ax},${base1Y} ${ax},${base2Y}`);
    arrow.setAttribute('fill','#111827');
    // wrap arrow in rotation group so arrow rotates around center
    const arrowWrap = document.createElementNS(svgNS,'g');
    arrowWrap.setAttribute('transform', `rotate(${angle})`);
    arrowWrap.appendChild(arrow);
    tokenGroup.appendChild(arrowWrap);

    // accessibility: role and title
    const title = document.createElementNS(svgNS,'title');
    title.textContent = `${gender} couple ${coupleIndex}`;
    tokenGroup.appendChild(title);

    svg.appendChild(tokenGroup);
  }

  return svg;
}

/* Example usage:
import { renderDanceFloor } from './dancefloorRenderer.js';
const floor = await fetch('/api/dancefloor/init', {method:'POST', body: JSON.stringify({couples:4})}).then(r=>r.json());
const svgEl = renderDanceFloor(floor, {width:900,height:600, paddingPx:24, tokenLogicalRadius:0.5});
document.getElementById('middle').innerHTML=''; // panel
document.getElementById('middle').appendChild(svgEl);
*/
