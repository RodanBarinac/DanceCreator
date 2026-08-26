import { JSDOM } from 'jsdom';
import { makeSplitter } from '../../static/resize.js';

describe('resize.js - Panel Resizer', () => {
  let dom;
  let document;
  let window;

  beforeEach(() => {
    const html = `
      <!DOCTYPE html>
      <html>
        <body>
          <div id="container" style="display: flex; width: 1000px;">
            <div id="left" style="width: 300px;"></div>
            <div id="splitter-left" style="width: 10px;"></div>
            <div id="middle" style="width: 400px;"></div>
            <div id="splitter-right" style="width: 10px;"></div>
            <div id="right" style="width: 290px;"></div>
          </div>
        </body>
      </html>
    `;
    dom = new JSDOM(html);
    document = dom.window.document;
    window = dom.window;
    global.document = document;
    global.window = window;
  });

  test('makeSplitter function exists and is callable', () => {
    expect(() => makeSplitter('splitter-left', 'left', 'middle')).not.toThrow();
  });

  test('makeSplitter safely handles missing elements', () => {
    // Non-existent elements should not throw
    expect(() => makeSplitter('nonexistent', 'missing', 'nope')).not.toThrow();
  });

  test('makeSplitter can be called for multiple splitters', () => {
    expect(() => {
      makeSplitter('splitter-left', 'left', 'middle');
      makeSplitter('splitter-right', 'middle', 'right');
    }).not.toThrow();
  });

  test('makeSplitter operates on correct DOM elements', () => {
    const splitter = document.getElementById('splitter-left');
    const leftPanel = document.getElementById('left');
    const middle = document.getElementById('middle');
    
    expect(splitter).not.toBeNull();
    expect(leftPanel).not.toBeNull();
    expect(middle).not.toBeNull();
    
    // Should not throw when valid elements exist
    expect(() => makeSplitter('splitter-left', 'left', 'middle')).not.toThrow();
  });
});

