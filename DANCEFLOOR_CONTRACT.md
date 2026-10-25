# Dancefloor Renderer Contract - Quick Navigation

## 📚 Documentation

All contract documentation is in the **`Documents/`** directory:

### Getting Started
1. **[DANCEFLOOR_CONTRACT_README.md](Documents/DANCEFLOOR_CONTRACT_README.md)** - Quick overview and summary
2. **[DANCEFLOOR_RENDERER_CONTRACT.md](Documents/DANCEFLOOR_RENDERER_CONTRACT.md)** - Full specification (detailed)
3. **[DANCEFLOOR_CONTRACT_INTEGRATION.md](Documents/DANCEFLOOR_CONTRACT_INTEGRATION.md)** - Integration guide for developers

## 📋 Schema Files

All JSON schemas are in the **`config/`** directory:

- **[schema/dancefloor_contract.schema.json](schema/dancefloor_contract.schema.json)** - Machine-readable contract specification (Draft 7)
- **[schema/](schema/)** - API and data schemas

## 🔧 Implementation Files

### Python Backend
- **[src/engine/validators/DancefloorContractValidator.py](src/engine/validators/DancefloorContractValidator.py)** - Validation and serialization for Python
- **[GUI_DanceCreator_App.py](GUI_DanceCreator_App.py)** - Flask API with schema route (`/schema/<path>`)

### JavaScript Frontend
- **[static/DancefloorContractValidator.js](static/DancefloorContractValidator.js)** - Validation for JavaScript
- **[templates/dancefloor_mockup.html](templates/dancefloor_mockup.html)** - Example usage

## 🚀 Quick Start

### For Python Developers
```python
from src.engine.validators import DancefloorContractValidator

validator = DancefloorContractValidator.DancefloorValidator()
validator.validate(floor_json)
return jsonify(floor_json)
```

### For JavaScript Developers
```javascript
import { DancefloorValidator } from '/static/DancefloorContractValidator.js';

const validator = new DancefloorValidator();
await validator.validate(floorData);
```

## 📖 Reading Order

1. Start here: **Documents/DANCEFLOOR_CONTRACT_README.md**
2. Then read: **Documents/DANCEFLOOR_RENDERER_CONTRACT.md**
3. For implementation: **Documents/DANCEFLOOR_CONTRACT_INTEGRATION.md**
4. Reference: **schema/dancefloor_contract.schema.json**

## ✓ What's Included

- ✅ Complete contract specification (human-readable)
- ✅ JSON Schema (Draft 7, machine-readable)
- ✅ Python validation module with tests
- ✅ JavaScript validation module
- ✅ Flask route to serve schemas
- ✅ Integration guide with examples
- ✅ Error reference documentation

## 🎯 Key Concept: Facing

**Important**: The `facing` field is a **target position**, NOT a direction vector:

```json
{
  "coord": [1, -1],       // Row 1, men's line
  "facing": [1, 1]        // Target on the ladies' line (not a direction vector)
}
```

The renderer converts this to a direction vector:
```javascript
direction = [facing[1] - coord[1], facing[0] - coord[0]]  // [2, 0]
```

## 📞 Support

See the integration guide for:
- Common issues and solutions
- Error message reference
- Validation checklist
- Testing procedures

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2026-08-29


## Centered dance-floor grid (breaking coordinate change)

Rows remain 1-based couple positions. Columns are centered: men's line `-1`, centre line `0`, and ladies' line `+1`. Floor and facing coordinates use `[row, column]`; figure offsets shift their column by `-1`, while top-level dance anchors shift by `-1`, so every absolute floor column is the previous value minus `2`. Default facing targets the same row on the opposite side of the centre line: `[row, column]` faces `[row, -column]` (for example `[2,-1]` faces `[2,1]`). This is a target position, not a direction vector.
