import { jest } from '@jest/globals';
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
      '1m': { coord: [1,-1] },
      '2w': { coord: [2,1] }
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
  test('keeps both set lines within the canvas when dancers are on one side', () => {
    const svg = renderDanceFloor({ positions: {
      man: { coord: [1, -1], dancer: { name: '1m' } },
    } }, { width: 320, height: 220, showSetLines: true });

    const lines = [...svg.querySelectorAll('line[data-set-line]')];
    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(Number(line.getAttribute('y1'))).toBeGreaterThan(30);
      expect(Number(line.getAttribute('y1'))).toBeLessThan(212);
    }
  });

  test('draws the two set lines in logical coordinates when requested', () => {
    const svg = renderDanceFloor({ positions: {
      man: { coord: [1, -1], dancer: { name: '1m' } },
      lady: { coord: [1, 1], dancer: { name: '1w' } },
    } }, { showSetLines: true, referenceBounds: [1, -1, 4, 1] });
    const lines = [...svg.querySelectorAll('line[data-set-line]')];
    expect(lines.map(line => line.getAttribute('data-set-line'))).toEqual(['ladies', 'men']);
    expect(lines.every(line => line.getAttribute('stroke-dasharray'))).toBe(true);
    const y = name => Number(svg.querySelector(`[data-dancer="${name}"]`)
      .getAttribute('transform').match(/, ([^)]+)\)/)[1]);
    expect(Number(lines[0].getAttribute('y1'))).toBeCloseTo(y('1w'));
    expect(Number(lines[1].getAttribute('y1'))).toBeCloseTo(y('1m'));
  });
  test('returns an SVG element with tokens for positions', () => {
    const floor = {
      name: 'test',
      couples: 2,
      tick: 0,
      positions: {
        '1m': { dancer: { name: 'A', gender: 'M' }, coord: [1,-1], facing: 0 },
        '1w': { dancer: { name: 'B', gender: 'F' }, coord: [1,1], facing: 0 }
      }
    };
    const svg = renderDanceFloor(floor, { width: 600, height: 300, paddingPx: 10 });
    expect(svg).toBeTruthy();
    // should contain two token groups (g elements) appended after headers
    const gs = svg.querySelectorAll('g');
    expect(gs.length).toBeGreaterThanOrEqual(1);
    // ensure there is at least one circle (man) and one rect (woman)
    expect(svg.querySelector('circle')).not.toBeNull();
    expect(svg.querySelector('rect')).not.toBeNull();
  });

  test('sets consistent intrinsic SVG dimensions and aspect-preserving viewBox', () => {
    const svg = renderDanceFloor({ positions: {} }, { width: 300, height: 210 });

    expect(svg.getAttribute('width')).toBe('300');
    expect(svg.getAttribute('height')).toBe('210');
    expect(svg.getAttribute('viewBox')).toBe('0 0 300 210');
    expect(svg.getAttribute('preserveAspectRatio')).toBe('xMidYMid meet');
    expect(svg.classList.contains('dancefloor-svg')).toBe(true);
  });

  test('renders selected context, coordinates, dancer identity, and facing accessibly', () => {
    const svg = renderDanceFloor({
      positions: {
        '1.5:2.25': {
          dancer: { name: 'Alex', gender: 'person' },
          coord: [1.5, 2.25],
          facing: [0.5, 1],
        },
      },
    }, {
      contextLabel: 'Parallel group',
      selectedPositions: [[1.5, 2.25]],
    });

    const token = svg.querySelector('[data-position="1.5,2.25"]');
    expect(svg.textContent).toContain('Parallel group');
    expect(token).not.toBeNull();
    expect(token.getAttribute('data-selected')).toBe('true');
    expect(token.querySelector('title').textContent).toContain('Alex');
    expect(token.querySelector('title').textContent).toContain('1.5, 2.25');
    expect(token.querySelector('[data-facing]')).not.toBeNull();
  });

  test('places the top of the set on the left and ladies above men', () => {
    const svg = renderDanceFloor({
      positions: {
        '1m': {
          dancer: { name: '1m', gender: 'male' },
          coord: [1, -1],
          facing: [1, 1],
        },
        '1w': {
          dancer: { name: '1w', gender: 'female' },
          coord: [1, 1],
          facing: [1, -1],
        },
        '2m': {
          dancer: { name: '2m', gender: 'male' },
          coord: [2, -1],
          facing: [2, 1],
        },
      },
    });
    const position = name => {
      const values = svg.querySelector(`[data-dancer="${name}"]`)
        .getAttribute('transform').match(/translate\(([^,]+), ([^)]+)\)/);
      return [Number(values[1]), Number(values[2])];
    };

    expect(position('1m')[0]).toBeLessThan(position('2m')[0]);
    expect(position('1w')[1]).toBeLessThan(position('1m')[1]);
    expect(svg.querySelector('[data-dancer="1m"] [data-facing]').getAttribute('data-facing'))
      .toBe('-90');
    expect(svg.querySelector('[data-dancer="1w"] [data-facing]').getAttribute('data-facing'))
      .toBe('90');
  });

  test('keeps couple colors with dancers when their positions change', () => {
    const svg = renderDanceFloor({
      positions: {
        '1:1': {
          dancer: { name: '2w', gender: 'female' },
          coord: [1, 1],
        },
        '2:-1': {
          dancer: { name: '1m', gender: 'male' },
          coord: [2, -1],
        },
        '3:-1': {
          dancer: { name: '2m', gender: 'male' },
          coord: [3, -1],
        },
        '4:1': {
          dancer: { name: '1w', gender: 'female' },
          coord: [4, 1],
        },
      },
    });
    const fill = name => {
      const token = svg.querySelector(`[data-dancer="${name}"]`);
      return token.querySelector('circle, rect').getAttribute('fill');
    };

    expect(fill('1m')).toBe(fill('1w'));
    expect(fill('2m')).toBe(fill('2w'));
    expect(fill('1m')).not.toBe(fill('2m'));
    expect(fill('1m')).toBe('#0072B2');
    expect(fill('2w')).toBe('#E69F00');
  });

  test('uses 0.45 logical units for dancer icon diameter', () => {
    const positions = Object.fromEntries(Array.from({ length: 5 }, (_, index) => {
      const couple = index + 1;
      return [`${couple}m`, {
        dancer: { name: `${couple}m`, gender: 'male' },
        coord: [couple, -1],
      }];
    }));
    positions['1w'] = {
      dancer: { name: '1w', gender: 'female' },
      coord: [1, 1],
    };
    const svg = renderDanceFloor({ positions });
    const center = name => svg.querySelector(`[data-dancer="${name}"]`)
      .getAttribute('transform').match(/translate\(([^,]+), ([^)]+)\)/).slice(1).map(Number);
    const scale = Math.abs(center('1m')[0] - center('2m')[0]);
    const circleDiameter = Number(svg.querySelector('[data-dancer="1m"] circle').getAttribute('r')) * 2;
    const squareDiameter = Number(svg.querySelector('[data-dancer="1w"] rect').getAttribute('width'));

    expect(circleDiameter / scale).toBeCloseTo(0.45);
    expect(squareDiameter / scale).toBeCloseTo(0.45);
    for (let couple = 1; couple < 5; couple += 1) {
      const gap = Math.abs(center(`${couple + 1}m`)[0] - center(`${couple}m`)[0])
        - circleDiameter;
      expect(gap).toBeGreaterThan(0);
    }
  });
  test('rotates squares and fallback diamonds to match facing without rotating circles', () => {
    const svg = renderDanceFloor({
      positions: {
        square: {
          dancer: { name: '1w', gender: 'female' },
          coord: [1, 1],
          facing: [1, 2],
        },
        diamond: {
          dancer: { name: '2x', gender: 'nonbinary' },
          coord: [2, 1],
          facing: [3, 2],
        },
        circle: {
          dancer: { name: '1m', gender: 'male' },
          coord: [1, -1],
          facing: [1, 1],
        },
      },
    }, {
      selectedPositions: [[1, 1], [2, 1]],
    });
    const square = svg.querySelector('[data-dancer="1w"] rect');
    const diamond = svg.querySelector('[data-dancer="2x"] polygon');
    const circle = svg.querySelector('[data-dancer="1m"] circle');
    const facingTransform = name => {
      const facingAngle = svg.querySelector(`[data-dancer="${name}"] [data-facing]`)
        .getAttribute('data-facing');
      return `rotate(${facingAngle})`;
    };

    expect(square.getAttribute('transform')).toBe(facingTransform('1w'));
    expect(diamond.getAttribute('transform')).toBe(facingTransform('2x'));
    expect(circle.hasAttribute('transform')).toBe(false);
    expect(square.getAttribute('stroke')).toBe('#d84315');
    expect(square.getAttribute('stroke-width')).toBe('4');
    expect(diamond.getAttribute('stroke')).toBe('#d84315');
    expect(diamond.getAttribute('stroke-width')).toBe('4');
  });

  test('marks dancers by name or start-position index and preserves selection stroke', () => {
    const svg = renderDanceFloor({
      positions: {
        first: { dancer: { name: 'Ann', gender: 'female' }, coord: [1, 1] },
        second: { dancer: { name: 'Ben', gender: 'male' }, coord: [2, -1] },
      },
    }, {
      errorDancers: ['Ann', 'start position 2'],
      selectedPositions: [[1, 1]],
    });
    const ann = svg.querySelector('[data-dancer="Ann"]');
    const ben = svg.querySelector('[data-dancer="Ben"]');

    expect(ann.classList.contains('invalid-preview-marker')).toBe(true);
    expect(ann.querySelector('.error-outline')).not.toBeNull();
    expect(ann.querySelector('rect').getAttribute('stroke')).toBe('#d84315');
    expect(ben.classList.contains('invalid-preview-marker')).toBe(true);
    expect(ben.querySelector('.error-outline')).not.toBeNull();
  });

  test('calls the dancer selection callback when a floor token is clicked', () => {
    const onDancerSelect = jest.fn();
    const svg = renderDanceFloor({ positions: {
      '1m': { dancer: { name: '1m', gender: 'male' }, coord: [1, 1] },
    } }, { onDancerSelect });
    const token = svg.querySelector('[data-dancer="1m"]');

    token.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(onDancerSelect).toHaveBeenCalledWith('1m', [1, 1]);
  });
});
