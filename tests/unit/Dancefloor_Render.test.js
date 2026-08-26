import { degFromFacing, computeBBox, mapLogicalToPixel, renderDanceFloor } from '../../static/Dancefloor_Render.js';

describe('Dancefloor_Render helpers', () => {
  test('degFromFacing accepts degrees and vectors', () => {
    expect(degFromFacing(90)).toBe(90);
    const deg = degFromFacing([0, 1]); // downwards
    // atan2(1,0) = 90
    expect(Math.round(deg)).toBe(90);
    const deg2 = degFromFacing([1, 0]);
    expect(Math.round(deg2)).toBe(0);
  });

  test('computeBBox extracts coords and expands margin', () => {
    const positions = {
      '1m': { coord: [1,1] },
      '2w': { coord: [2,3] }
    };
    const bbox = computeBBox(positions);
    expect(bbox.length).toBe(4);
    // minX should be <=1, maxX >=2
    expect(bbox[0]).toBeLessThanOrEqual(1);
    expect(bbox[2]).toBeGreaterThanOrEqual(2);
  });

  test('mapLogicalToPixel maps to px and returns scale', () => {
    const bbox = [0,0,4,4];
    const res = mapLogicalToPixel([2,2], bbox, [400,400], 20);
    expect(res.x).toBeGreaterThan(0);
    expect(res.y).toBeGreaterThan(0);
    expect(res.scale).toBeGreaterThan(0);
  });
});

describe('renderDanceFloor', () => {
  test('returns an SVG element with tokens for positions', () => {
    const floor = {
      name: 'test',
      couples: 2,
      tick: 0,
      positions: {
        '1m': { dancer: { name: 'A', gender: 'M' }, coord: [1,1], facing: 0 },
        '1w': { dancer: { name: 'B', gender: 'F' }, coord: [1,3], facing: 0 }
      }
    };
    const svg = renderDanceFloor(floor, { width: 600, height: 300, paddingPx: 10, tokenLogicalRadius: 0.5 });
    expect(svg).toBeTruthy();
    // should contain two token groups (g elements) appended after headers
    const gs = svg.querySelectorAll('g');
    expect(gs.length).toBeGreaterThanOrEqual(1);
    // ensure there is at least one circle (man) and one rect (woman)
    expect(svg.querySelector('circle')).not.toBeNull();
    expect(svg.querySelector('rect')).not.toBeNull();
  });
});
