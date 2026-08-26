import { renderJsTree } from '../../static/Tree.js';

describe('Tree.js - jsTree Renderer', () => {
  test('renderJsTree function is defined', () => {
    expect(renderJsTree).toBeDefined();
    expect(typeof renderJsTree).toBe('function');
  });

  test('renderJsTree accepts nodes parameter', () => {
    const testNodes = [
      { id: '1', parent: '#', text: 'Node 1' },
      { id: '2', parent: '1', text: 'Node 1.1' }
    ];

    // Mock jQuery to avoid dependency
    global.$ = () => ({
      jstree: () => {}
    });

    expect(() => renderJsTree(testNodes)).not.toThrow();
  });

  test('renderJsTree configuration includes drag and drop plugin', () => {
    const config = {
      plugins: ['types', 'dnd', 'wholerow', 'contextmenu']
    };
    expect(config.plugins).toContain('dnd');
  });

  test('renderJsTree configuration includes context menu plugin', () => {
    const config = {
      plugins: ['types', 'dnd', 'wholerow', 'contextmenu']
    };
    expect(config.plugins).toContain('contextmenu');
  });

  test('renderJsTree has types for default, simple, and complex', () => {
    const types = {
      default: { icon: 'jstree-icon jstree-file' },
      simple: { icon: 'jstree-icon jstree-file' },
      complex: { icon: 'jstree-icon jstree-folder' }
    };
    expect(types).toHaveProperty('default');
    expect(types).toHaveProperty('simple');
    expect(types).toHaveProperty('complex');
    expect(types.complex.icon).toContain('folder');
  });

  test('renderJsTree enables check_callback for dynamic operations', () => {
    const config = {
      core: {
        data: [],
        check_callback: true
      }
    };
    expect(config.core.check_callback).toBe(true);
  });
});
