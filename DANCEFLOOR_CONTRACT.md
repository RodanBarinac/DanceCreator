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
  "coord": [1, 1],        // Dancer's current position
  "facing": [1, 3]        // Position they're facing toward (not [2, 0])
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
