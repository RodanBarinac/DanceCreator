import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(
  new URL('../../static/DancefloorContractValidator.js', import.meta.url),
  'utf8',
);
const { DancefloorValidator } = vm.runInNewContext(
  `${source}\n;({ DancefloorValidator })`,
  { console },
);

const validCenteredFloor = () => ({
  name: 'centered',
  couples: 1,
  tick: 0,
  positions: {
    '1m': {
      dancer: { name: '1m', gender: 'M' },
      coord: [1, -1],
      facing: [1, 1],
    },
    '1w': {
      dancer: { name: '1w', gender: 'F' },
      coord: [1, 1],
      facing: [1, -1],
    },
  },
});

describe('DancefloorContractValidator centered grid', () => {
  test('accepts negative columns in coordinates and facing targets', () => {
    const validator = new DancefloorValidator();
    validator.schema = {};

    expect(validator.getValidationErrors(validCenteredFloor())).toEqual([]);
  });

  test('continues to reject coordinates with rows below one', () => {
    const validator = new DancefloorValidator();
    validator.schema = {};
    const floor = validCenteredFloor();
    floor.positions['1m'].coord[0] = 0;

    expect(validator.getValidationErrors(floor)).toContain(
      'positions.1m.coord[0] row must be at least 1',
    );
  });
});
