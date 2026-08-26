
/**
 * Initialisiert jsTree im treeContainer mit den übergebenen Daten.
 */
export function renderJsTree(nodes) {
  const treeContainer = $('#treeContainer');
  treeContainer.jstree('destroy'); // Vorherigen Baum entfernen
  treeContainer.jstree({
    core: {
      data: [],
      check_callback: true
    },
    plugins: ['types', 'dnd', 'wholerow', "contextmenu"],
    types: {
      default: { icon: 'jstree-icon jstree-file' },
      simple: { icon: 'jstree-icon jstree-file' },
      complex: { icon: 'jstree-icon jstree-folder' }
    }
  });
}
