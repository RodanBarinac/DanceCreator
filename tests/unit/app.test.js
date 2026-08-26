import { escapeHtml, formatPos, renderSteps, renderCrips } from '../../static/app.js';

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
      Facing: [0, 90],
      Partner: [[1,2], [1,3]]
    };
    const result = renderSteps(data);
    expect(result).toContain('<table class="figure-table">');
    expect(result).toContain('<th>#</th>');
    expect(result).toContain('(1, 1)');
  });

  test('renderCrips generates HTML list from crips', () => {
    const data = { CriptDesc: ['Turn right', 'Cast down'] };
    const result = renderCrips(data);
    expect(result).toContain('<ol class="figure-crips">');
    expect(result).toContain('<li>Turn right</li>');
    expect(result).toContain('<li>Cast down</li>');
  });

  test('renderCrips handles empty crips', () => {
    const data = { CriptDesc: [] };
    const result = renderCrips(data);
    expect(result).toContain('No crips available');
  });
});
