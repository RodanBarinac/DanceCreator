# Dancefloor Renderer Contract - Summary

## Files Created

This solution consists of 4 key files that establish a formal contract between the Python dance engine and JavaScript renderer:

### 1. **Documents/DANCEFLOOR_RENDERER_CONTRACT.md** (Specification)
- Complete human-readable specification of the data contract
- 10,700+ words covering all aspects of the contract
- Includes examples, validation rules, and future considerations
- **For**: Developers, architects, reviewers

### 2. **config/contract/dancefloor_contract.schema.json** (JSON Schema)
- Formal JSON Schema (Draft 7) for automated validation
- Defines all required fields, types, ranges, and patterns
- Can be used by validation tools and IDEs
- **For**: Automated validation, IDE integration, documentation

### 3. **src/engine/validators/DancefloorContractValidator.py** (Python Validator)
- Python module for contract validation and serialization
- Integrates with Python backend (Flask API)
- Provides `DancefloorValidator` class with validation methods
- Includes `DancefloorSerializer` for converting Python objects to contract JSON
- **For**: Backend validation before sending data to frontend

### 4. **static/DancefloorContractValidator.js** (JavaScript Validator)
- JavaScript/TypeScript module for contract validation
- Can be used in browser to validate incoming dancefloor data
- Provides detailed error reporting
- **For**: Frontend validation before rendering

## Contract Structure

```
Dancefloor (root object)
├── name (string, 1-255 chars)        → State identifier
├── couples (integer, 1-16)           → Number of couples
├── tick (integer, 0-999)             → Current bar/movement
└── positions (object)                → All occupied positions
    ├── "1m" (position key)           → Position identifier
    │   ├── dancer (object)           → Dancer info
    │   │   ├── name (string)         → Dancer identifier
    │   │   └── gender (M|F)          → Rendering type
    │   ├── coord [row, col]          → Current position
    │   └── facing [row, col]         → Target position (NOT vector)
    └── "1w", "2m", "2w", etc...
```

## Key Principles

1. **Facing is a Position, Not a Vector**
   - `facing: [2, 3]` means "facing toward row 2, column 3"
   - The renderer converts this to direction vector: `[col - currentCol, row - currentRow]`
   - This is more intuitive for the dance engine

2. **One Dataset Per Dancefloor State**
   - Each snapshot of the dance gets one complete dancefloor JSON
   - Multiple calls produce multiple JSON objects (one per state)
   - No delta/incremental updates - each state is complete

3. **All Occupied Positions**
   - Only positions with dancers are included in the `positions` map
   - Empty positions are omitted
   - Each position has exactly one dancer

4. **Validation Everywhere**
   - Python validates before sending to JavaScript
   - JavaScript validates before rendering
   - Both use the same schema for consistency

## Integration Instructions

### Python Backend (Flask)

```python
from DancefloorContractValidator import DancefloorSerializer, validate_dancefloor

# After executing a figure on the dancefloor:
floor_json = DancefloorSerializer.serialize_dancefloor(
    name="After H1DR",
    couples=3,
    tick=4,
    dancer_map=floor.DanceFloorMap
)

# Validate before sending
validate_dancefloor(floor_json)

# Return to frontend
return jsonify(floor_json)
```

### JavaScript Frontend

```javascript
import { DancefloorValidator } from '/static/DancefloorContractValidator.js';
import { renderDanceFloor } from '/static/Dancefloor_Render.js';

const validator = new DancefloorValidator();

// After receiving floor data from API:
const floorData = await response.json();

try {
    await validator.validate(floorData);
    const svg = renderDanceFloor(floorData, options);
    container.appendChild(svg);
} catch (err) {
    console.error('Invalid dancefloor data:', err);
}
```

## Example: Valid Dancefloor Data

```json
{
  "name": "Initial Setup",
  "couples": 3,
  "tick": 0,
  "positions": {
    "1m": {
      "dancer": {"name": "1m", "gender": "M"},
      "coord": [1, 1],
      "facing": [1, 3]
    },
    "1w": {
      "dancer": {"name": "1w", "gender": "F"},
      "coord": [1, 3],
      "facing": [1, 1]
    },
    "2m": {
      "dancer": {"name": "2m", "gender": "M"},
      "coord": [2, 1],
      "facing": [2, 3]
    },
    "2w": {
      "dancer": {"name": "2w", "gender": "F"},
      "coord": [2, 3],
      "facing": [2, 1]
    },
    "3m": {
      "dancer": {"name": "3m", "gender": "M"},
      "coord": [3, 1],
      "facing": [3, 3]
    },
    "3w": {
      "dancer": {"name": "3w", "gender": "F"},
      "coord": [3, 3],
      "facing": [3, 1]
    }
  }
}
```

## Validation Rules Summary

| Field | Type | Required | Range | Pattern |
|-------|------|----------|-------|---------|
| name | string | ✓ | 1-255 chars | Any |
| couples | integer | ✓ | 1-16 | N/A |
| tick | integer | ✓ | 0-999 | N/A |
| positions | object | ✓ | 2+ items | Keys: `\d{1,2}[mwMW]` or `\d{1,2}:\d{1,2}` |
| dancer.name | string | ✓ | 1-255 chars | Any |
| dancer.gender | string | ✓ | N/A | `M` or `F` |
| coord | array | ✓ | 2 numbers | Any finite numbers |
| facing | array | ✓ | 2 numbers | Any finite numbers |

## Testing

### Python Testing
```bash
# Run the validator with the example in the module
python DancefloorContractValidator.py
```

### JavaScript Testing
```javascript
// In browser console or test file
const validator = new DancefloorValidator();
const errors = validator.getValidationErrors(testData);
console.log(errors);
```

## Version

- **Current**: 1.0.0
- **Schema ID**: `https://dancecreator.local/schemas/dancefloor_contract.schema.json`
- **Status**: Ready for production

## Future Extensions

The contract is extensible. Potential future versions could add:
- Optional metadata fields (title, notes, duration)
- Animation timing hints
- Rendering preferences per dancer
- Historical state references
- Formation names and descriptions

## Benefits

✓ **Clear Communication**: Eliminates ambiguity between frontend and backend
✓ **Automated Validation**: Both sides can validate data independently  
✓ **IDE Support**: JSON Schema enables autocomplete and validation in IDEs
✓ **Documentation**: Schema serves as machine-readable documentation
✓ **Versioning**: Semantic versioning allows safe schema evolution
✓ **Testing**: Contract enables thorough integration tests
✓ **Debugging**: Clear error messages pinpoint contract violations

## Questions?

See **DANCEFLOOR_RENDERER_CONTRACT.md** for detailed specifications and examples.
