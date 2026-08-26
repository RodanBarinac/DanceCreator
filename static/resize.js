
export function makeSplitter(splitterId, leftPanelId, rightPanelId) {
  const splitter = document.getElementById(splitterId);
  const leftPanel = document.getElementById(leftPanelId);
  const rightPanel = document.getElementById(rightPanelId);

  if (!splitter || !leftPanel || !rightPanel) return;

  splitter.addEventListener('mousedown', function(e) {
    e.preventDefault();
    document.addEventListener('mousemove', resize);
    document.addEventListener('mouseup', stopResize);
  });

  function resize(e) {
    const totalWidth = splitter.parentNode.offsetWidth;
    const leftWidth = e.clientX;
    const rightWidth = totalWidth - leftWidth - 10; // 10 = 2 splitters width

    if (leftWidth > 100 && rightWidth > 100) {
      leftPanel.style.width = leftWidth + 'px';
      rightPanel.style.width = rightWidth + 'px';
    }
  }

  function stopResize() {
    document.removeEventListener('mousemove', resize);
    document.removeEventListener('mouseup', stopResize);
  }
}

if (typeof document !== 'undefined' && document.getElementById('splitter-left')) {
  makeSplitter('splitter-left', 'left', 'middle');
  makeSplitter('splitter-right', 'middle', 'right');
}