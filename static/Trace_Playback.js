export function floorForRenderer(floor) {
  if (!floor || typeof floor !== 'object') return null;
  const source = floor.positions && typeof floor.positions === 'object'
    ? floor.positions
    : floor;
  const positions = {};
  Object.entries(source).forEach(([key, value]) => {
    if (!value || typeof value !== 'object') return;
    const coord = Array.isArray(value.coord)
      ? value.coord
      : Array.isArray(value.position)
        ? value.position
        : null;
    if (!coord || coord.length < 2) return;
    positions[key] = {
      coord: [coord[0], coord[1]],
      dancer: value.dancer || {},
      facing: value.facing
    };
  });
  return { positions };
}

export function buildPlaybackSteps(readModel) {
  const trace = readModel && Array.isArray(readModel.trace) ? readModel.trace : [];
  const execution = readModel && readModel.execution ? readModel.execution : {};
  const lastValidFloor = execution.lastValidFloor || null;
  const initialFloor = trace.length
    ? trace[0].incomingFloor
    : lastValidFloor;
  const steps = [{
    kind: 'initial',
    nodeId: null,
    status: trace.length ? 'ready' : (execution.status || 'unavailable'),
    floor: floorForRenderer(initialFloor),
    outgoingFloor: floorForRenderer(initialFloor),
    incomingFloor: null,
    branches: [],
    conflict: null,
    record: null
  }];

  trace.forEach(record => {
    const outgoingFloor = record.outgoingFloor || null;
    const displayFloor = outgoingFloor || lastValidFloor || record.incomingFloor;
    const occurrence = record.kind === 'figure' || record.kind === 'composite';
    steps.push({
      kind: occurrence ? 'occurrence' : 'group',
      nodeId: record.nodeId,
      status: record.status,
      barRange: record.barRange || null,
      floor: floorForRenderer(displayFloor),
      incomingFloor: floorForRenderer(record.incomingFloor),
      outgoingFloor: floorForRenderer(outgoingFloor),
      branches: (record.branches || []).map(branch => ({
        nodeId: branch.nodeId,
        status: branch.status,
        floor: floorForRenderer(branch.outgoingFloor),
        writes: branch.writes || []
      })),
      conflict: record.conflict || null,
      record
    });
  });
  return steps;
}

export class TracePlayback {
  constructor(readModel) {
    this.steps = buildPlaybackSteps(readModel);
    this.index = 0;
  }

  get current() {
    return this.steps[this.index] || null;
  }

  previous() {
    this.index = Math.max(0, this.index - 1);
    return this.current;
  }

  next() {
    this.index = Math.min(this.steps.length - 1, this.index + 1);
    return this.current;
  }

  selectNode(nodeId) {
    const index = this.steps.findIndex(step => step.nodeId === nodeId);
    if (index < 0) return false;
    this.index = index;
    return true;
  }
}
