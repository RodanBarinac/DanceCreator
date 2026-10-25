import {
  TracePlayback,
  buildPlaybackSteps,
  floorForRenderer,
} from '../../static/Trace_Playback.js';

describe('floorForRenderer', () => {
  test('converts API floor snapshots without losing coordinates or dancer metadata', () => {
    const floor = floorForRenderer({
      '1.5:3.25': {
        position: [1.5, 3.25],
        dancer: { name: 'Alex', gender: 'person' },
        facing: [0.5, 1],
      },
    });

    expect(floor.positions['1.5:3.25']).toEqual({
      coord: [1.5, 3.25],
      dancer: { name: 'Alex', gender: 'person' },
      facing: [0.5, 1],
    });
  });
});

describe('trace boundary playback', () => {
  const initialFloor = {
    '1m': { position: [1, -1], dancer: { name: '1m', gender: 'male' }, facing: [1, 1] },
  };
  const childFloor = {
    '1:0': { position: [1, 0], dancer: { name: '1m', gender: 'male' }, facing: [1, 0] },
  };

  test('creates only initial, occurrence, and group boundary steps', () => {
    const steps = buildPlaybackSteps({
      trace: [
        {
          nodeId: 'occurrence',
          kind: 'figure',
          status: 'completed',
          barRange: [1, 8],
          incomingFloor: initialFloor,
          outgoingFloor: childFloor,
          writes: [[1, 0]],
          branches: [],
        },
        {
          nodeId: 'parallel',
          kind: 'parallel',
          status: 'completed',
          incomingFloor: childFloor,
          outgoingFloor: childFloor,
          branches: [],
        },
      ],
      execution: { lastValidFloor: childFloor },
    });

    expect(steps.map(step => [step.kind, step.nodeId])).toEqual([
      ['initial', null],
      ['occurrence', 'occurrence'],
      ['group', 'parallel'],
    ]);
    expect(steps[1].floor.positions['1:0'].coord).toEqual([1, 0]);
    expect(steps[1].record.barRange).toEqual([1, 8]);
  });

  test('failed group retains isolated branches and displays last valid floor, not a partial result', () => {
    const steps = buildPlaybackSteps({
      trace: [{
        nodeId: 'parallel',
        kind: 'parallel',
        status: 'failed',
        incomingFloor: initialFloor,
        outgoingFloor: null,
        branches: [
          { nodeId: 'left', status: 'completed', outgoingFloor: childFloor, writes: [[1, 0]] },
          { nodeId: 'right', status: 'completed', outgoingFloor: initialFloor, writes: [[1, -1]] },
        ],
        conflict: { code: 'parallel_write_conflict' },
      }],
      execution: { lastValidFloor: initialFloor },
    });
    const group = steps[1];

    expect(group.outgoingFloor).toBeNull();
    expect(group.floor.positions['1m'].coord).toEqual([1, -1]);
    expect(group.branches.map(branch => branch.floor.positions)).toHaveLength(2);
    expect(group.conflict.code).toBe('parallel_write_conflict');
  });

  test('navigation and selection stop at authoritative trace boundaries', () => {
    const playback = new TracePlayback({
      trace: [{
        nodeId: 'figure',
        kind: 'figure',
        status: 'completed',
        incomingFloor: initialFloor,
        outgoingFloor: childFloor,
        branches: [],
      }],
      execution: { lastValidFloor: childFloor },
    });

    expect(playback.current.kind).toBe('initial');
    expect(playback.previous().kind).toBe('initial');
    expect(playback.next().nodeId).toBe('figure');
    expect(playback.next().nodeId).toBe('figure');
    expect(playback.selectNode('figure')).toBe(true);
    expect(playback.current.kind).toBe('occurrence');
    expect(playback.selectNode('unknown')).toBe(false);
  });
});
