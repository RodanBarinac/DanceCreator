# Dancefloor Contract Integration Guide

## Quick Start

### For Backend Developers (Python)

1. **Import the validator**
   ```python
   from DancefloorContractValidator import validate_dancefloor, DancefloorSerializer
   ```

2. **Validate before sending to frontend**
   ```python
   @app.route('/api/dancefloor/init', methods=['POST'])
   def api_dancefloor_init():
       # ... create floor ...
       floor_json = serialize_floor(floor)
       validate_dancefloor(floor_json)  # Raises if invalid
       return jsonify(floor_json)
   ```

3. **Serialize internal Python objects to contract format**
   ```python
   floor_json = DancefloorSerializer.serialize_dancefloor(
       name="After First H1DR",
       couples=3,
       tick=4,
       dancer_map=floor.DanceFloorMap
   )
   ```

### For Frontend Developers (JavaScript)

1. **Import the validator**
   ```javascript
   import { DancefloorValidator } from '/static/DancefloorContractValidator.js';
   import { renderDanceFloor } from '/static/Dancefloor_Render.js';
   ```

2. **Validate and render**
   ```javascript
   const validator = new DancefloorValidator();
   
   try {
       await validator.validate(floorData);
       const svg = renderDanceFloor(floorData, options);
       container.appendChild(svg);
   } catch (err) {
       console.error('Invalid dancefloor:', err);
   }
   ```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Contract Specification | `Documents/DANCEFLOOR_RENDERER_CONTRACT.md` | Human-readable spec |
| JSON Schema | `schema/dancefloor_contract.schema.json` | Machine-readable schema |
| Python Validator | `DancefloorContractValidator.py` | Backend validation/serialization |
| JS Validator | `static/DancefloorContractValidator.js` | Frontend validation |
| Python Example | `GUI_DanceCreator_App.py` (uses `_serialize_floor`) | API endpoints |
| JS Example | `templates/dancefloor_mockup.html` | Frontend usage |

## Key Concepts

### Facing Coordinates
The `facing` field is **not** a direction vector—it's a target position:

```javascript
// Example: Dancer at position [1,1] facing [1,3]
const coord = [1, 1];      // Current position
const facing = [1, 3];     // Target position they're facing

// Renderer converts to direction vector:
const dx = facing[1] - coord[1];  // 3 - 1 = 2 (facing right)
const dy = facing[0] - coord[0];  // 1 - 1 = 0 (not up/down)
const direction = [dx, dy];       // [2, 0] = facing right
```

### Position Keys
Position identifiers follow specific patterns:

- `"1m"` - Couple 1, Man
- `"1w"` - Couple 1, Woman  
- `"2m"`, `"2w"` - Couple 2, etc.
- `"3:2"` - Arbitrary position (row 3, column 2)

### Couples Count
The `couples` field is informational:
- Used for layout hints in the renderer
- Actual dancer count comes from `positions.length`
- Can be different from actual dancer count

## Common Issues & Solutions

### Issue: "facing is a required property"
**Cause**: Missing `facing` field in position object
**Solution**: Ensure every position has both `coord` and `facing`

```python
# Wrong
positions['1m'] = {'dancer': {...}, 'coord': [1, 1]}

# Right
positions['1m'] = {'dancer': {...}, 'coord': [1, 1], 'facing': [1, 3]}
```

### Issue: "gender must be 'M' or 'F'"
**Cause**: Using lowercase 'm'/'f' or other values
**Solution**: Always use uppercase M or F

```python
# Wrong
dancer_gender = 'm'  # lowercase
dancer_gender = 'Male'  # spelled out
dancer_gender = 1  # numeric

# Right
dancer_gender = 'M'  # uppercase letter
dancer_gender = 'F'  # uppercase letter
```

### Issue: Renderer shows dancers but no arrows
**Cause**: `facing` coordinates same as `coord`, resulting in zero-length direction vector
**Solution**: Ensure `facing` is different from `coord`

```python
# Wrong - no direction
facing = coord  # [1, 1]

# Right - has direction
facing = [1, 3]  # facing to the right
```

## Testing Your Implementation

### Python Test
```bash
# Run built-in validator tests
python DancefloorContractValidator.py
```

### JavaScript Test (Browser Console)
```javascript
// Load validator
const validator = new DancefloorValidator();

// Test data
const testFloor = {
    name: "Test",
    couples: 1,
    tick: 0,
    positions: {
        "1m": {
            dancer: {name: "1m", gender: "M"},
            coord: [1, 1],
            facing: [1, 3]
        }
    }
};

// Validate
await validator.validate(testFloor);
console.log("Valid!");
```

### Integration Test (API)
```bash
# Test dancefloor/init endpoint
curl -X POST http://localhost:5000/api/dancefloor/init \
  -H "Content-Type: application/json" \
  -d '{"couples": 3}'

# Should return valid contract-conforming JSON
```

## IDE Integration

### VS Code JSON Schema
Add to `.vscode/settings.json`:
```json
{
  "json.schemas": [
    {
      "fileMatch": ["**/dancefloor*.json"],
      "url": "./dancefloor_contract.schema.json"
    }
  ]
}
```

This enables autocomplete and validation for dancefloor JSON files.

## Error Messages Reference

| Error | Meaning | Fix |
|-------|---------|-----|
| `name must be a string` | Name field wrong type | Use string value |
| `couples must be between 1 and 16` | Out of range | Use 1-16 |
| `tick must be between 0 and 999` | Out of range | Use 0-999 |
| `positions must have at least 2 dancers` | Not enough positions | Add more dancers |
| `Invalid position key` | Key format wrong | Use format like '1m', '2w', '3:1' |
| `dancer is required` | Missing dancer object | Add dancer info |
| `gender must be 'M' or 'F'` | Invalid gender | Use uppercase M or F |
| `coord must be an array` | Wrong type | Use [row, col] array |
| `facing must be an array` | Wrong type | Use [targetRow, targetCol] array |

## Validation Checklist

Before sending dancefloor data from backend to frontend:

- [ ] All required fields present (name, couples, tick, positions)
- [ ] `name` is 1-255 characters
- [ ] `couples` is 1-16
- [ ] `tick` is 0-999
- [ ] `positions` has 2+ dancers
- [ ] Position keys match pattern (`\d{1,2}[mwMW]` or `\d{1,2}:\d{1,2}`)
- [ ] Each position has `dancer`, `coord`, `facing`
- [ ] Each dancer has `name` (string) and `gender` (M|F)
- [ ] Each `coord` is array of 2 numbers
- [ ] Each `facing` is array of 2 numbers
- [ ] No extra/unknown fields
- [ ] Gender values are uppercase (M or F)

## Schema Versioning

Current version: **1.0.0**

- **Major** (1.x.y): Breaking changes to required structure
- **Minor** (x.1.y): New optional fields added
- **Patch** (x.y.1): Clarifications, same data format

Future versions will maintain backward compatibility where possible.

## Support

**For questions about the contract:**
- See `DANCEFLOOR_RENDERER_CONTRACT.md` for detailed specification
- Review `dancefloor_contract.schema.json` for exact schema
- Check examples in `DANCEFLOOR_CONTRACT_README.md`

**For implementation issues:**
- Run tests (Python or JavaScript)
- Check error messages for specific violations
- Verify all required fields are present
- Ensure values match specified types and ranges
