# Dancefloor Renderer Communication Contract

## Purpose

This document defines the contract between the Python dance engine and the JavaScript dancefloor renderer. It specifies the exact structure of data that must be exchanged to render dancefloor visualizations.

## Overview

The contract is governed by a formal JSON Schema (`dancefloor_contract.schema.json`) that validates all dancefloor state data. This ensures compatibility and prevents miscommunication between the Python backend and JavaScript frontend.

## Core Principles

1. **Single Source of Truth**: Each dancefloor state must be represented by exactly one JSON object conforming to this contract
2. **Immutable Positions**: Once a position is defined, its coordinates do not change
3. **Explicit Facing**: Every dancer must have an explicit facing direction (target position they are facing)
4. **Unique Keys**: Position identifiers must be unique within a dancefloor
5. **No Partial Data**: All dancer data must be complete (no null/undefined fields)

## Data Structure

### Root Object

The top-level dancefloor object contains metadata and position data:

```json
{
  "name": "string",
  "couples": "number",
  "tick": "number",
  "positions": { ... }
}
```

### Root Properties

#### `name` (required, string)
- **Description**: Human-readable identifier for this dancefloor state
- **Examples**: "Initial Setup", "After First H1DR", "After Half Hey"
- **Length**: 1-255 characters
- **Pattern**: Should be descriptive and unique within a dance sequence

#### `couples` (required, integer)
- **Description**: The number of couples on the dancefloor
- **Range**: 1-16
- **Usage**: Informs the renderer about the expected scale and layout
- **Common Values**: 3 (Scottish Dancing), 4, 5, 8

#### `tick` (required, integer)
- **Description**: The current bar or tick count in the dance
- **Range**: 0-999
- **Meaning**: 
  - `0` = Initial setup
  - `1+` = After each bar/movement
- **Usage**: Tracks progression through the dance sequence
- **Unit**: Typically bars (4 beats per bar in Scottish Country Dancing)

#### `positions` (required, object)
- **Description**: Map of all occupied positions on the dancefloor
- **Key Format**: Position identifier (e.g., "1m", "1w", "2m", "2w")
- **Key Meaning**: 
  - Numeric prefix = couple number (1-16)
  - Letter suffix = gender: "m" for man, "w" for woman
  - Alternative: "1:1" format for arbitrary positioning
- **Value**: Position object (see below)
- **Minimum**: 2 positions (at least one couple)
- **Maximum**: No hard limit (typically 32 for 16 couples)

### Position Object

Each position in the `positions` map is an object:

```json
{
  "dancer": {
    "name": "string",
    "gender": "M" | "F"
  },
  "coord": [row, column],
  "facing": [facingRow, facingColumn]
}
```

#### `dancer` (required, object)
- **Description**: Information about the dancer at this position

##### `dancer.name` (required, string)
- **Description**: Unique identifier for the dancer
- **Examples**: "1m", "John Smith", "dancer_001"
- **Length**: 1-255 characters
- **Note**: Should uniquely identify the dancer within the dance context

##### `dancer.gender` (required, string)
- **Description**: Gender of the dancer
- **Valid Values**: 
  - `"M"` = Man/Male
  - `"F"` = Woman/Female
- **Rendering Impact**: Determines visual representation (circle for M, square for F)
- **Case Sensitive**: Must be uppercase

#### `coord` (required, array of 2 numbers)
- **Description**: The current position of the dancer on the dancefloor
- **Format**: `[row, column]`
- **Type**: Numbers (integer or float)
- **Range**: Typically 1-16 for each dimension
- **Semantics**:
  - Row direction: typically vertical (1 = top, increasing downward)
  - Column direction: typically horizontal (1 = left, increasing rightward)
- **Example**: `[2, 3]` = Row 2, Column 3
- **Uniqueness**: Each position should have at most one dancer

#### `facing` (required, array of 2 numbers)
- **Description**: The position the dancer is facing (target position)
- **Format**: `[facingRow, facingColumn]`
- **Type**: Numbers (integer or float)
- **Range**: Same coordinate space as `coord`
- **Semantics**: The target position toward which the dancer is oriented
- **Important**: This is NOT a direction vector; it is an absolute position coordinate
- **Renderer Responsibility**: The renderer converts this to a direction vector:
  ```
  direction_vector = [facingColumn - currentColumn, facingRow - currentRow]
  ```
- **Example**: 
  - Dancer at `[1, 1]` facing `[1, 3]` means facing right (vector: [2, 0])
  - Dancer at `[1, 1]` facing `[3, 1]` means facing down (vector: [0, 2])
  - Dancer at `[1, 1]` facing `[3, 3]` means facing diagonally down-right (vector: [2, 2])

## Validation

All dancefloor data MUST conform to the JSON Schema defined in `../schema/dancefloor_contract.schema.json`.

### Validation Rules

1. **Required Fields**: All fields marked as required must be present
2. **Type Checking**: All values must match their specified types
3. **Range Validation**: Numeric values must be within specified ranges
4. **String Patterns**: Certain strings must match defined patterns
5. **Uniqueness**: Position keys within a dancefloor must be unique
6. **Referential Integrity**: Referenced entities (dancers) must exist

### Validation Execution

Python backend must validate before returning data:
```python
import jsonschema
from dancefloor_contract import DancefloorContract

contract = DancefloorContract()
contract.validate(floor_data)  # Raises if invalid
```

JavaScript frontend should validate before rendering:
```javascript
import { validateDancefloor } from './DancefloorValidator.js';
validateDancefloor(floorData);  // Throws if invalid
```

## Examples

### Example 1: Simple 2-Couple Initial Setup

```json
{
  "name": "Initial Setup",
  "couples": 2,
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
    }
  }
}
```

### Example 2: After Half Diagonal Reel

```json
{
  "name": "After Half Diagonal Reel",
  "couples": 3,
  "tick": 4,
  "positions": {
    "1m": {
      "dancer": {"name": "1m", "gender": "M"},
      "coord": [3, 1],
      "facing": [3, 3]
    },
    "1w": {
      "dancer": {"name": "1w", "gender": "F"},
      "coord": [3, 3],
      "facing": [3, 1]
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
      "coord": [1, 1],
      "facing": [1, 3]
    },
    "3w": {
      "dancer": {"name": "3w", "gender": "F"},
      "coord": [1, 3],
      "facing": [1, 1]
    }
  }
}
```

## Python API Conformance

The Python backend (`GUI_DanceCreator_App.py`) provides two main endpoints:

### `POST /api/dancefloor/init`
**Request**: 
```json
{"couples": 3, "name": "Demo"}
```
**Response**: Dancefloor object conforming to this contract

### `POST /api/dancefloor/execute`
**Request**: 
```json
{
  "figure": "H1DR",
  "couples": 3,
  "anchor": [0, 0],
  "addons": [],
  "dance_name": "After H1DR"
}
```
**Response**: Object containing `{"floor": {...}, "crips": [...], "status": "ok"}`

The `floor` object must conform to this contract.

## JavaScript Renderer Compliance

The JavaScript renderer (`Dancefloor_Render.js`) implements:

### `renderDanceFloor(floorJson, options)`
**Input**: `floorJson` must conform to this contract
**Processing**:
1. Extracts `positions` map
2. For each position:
   - Converts `facing` coordinates to direction vector
   - Renders dancer token (circle for M, square for F)
   - Renders facing arrow based on direction vector
3. Returns SVG element

## Versioning

This contract uses semantic versioning:
- **Major**: Breaking changes to required structure
- **Minor**: Addition of optional fields
- **Patch**: Clarification or constraint changes

**Current Version**: 1.0.0

## Change Log

### Version 1.0.0 (Initial Release)
- Defined core dancefloor data structure
- Established position and dancer object schemas
- Specified facing coordinate semantics
- Created formal JSON Schema validation

## Future Considerations

Potential extensions for future versions:

1. **Optional Fields**:
   - `title` (string): Full title of the dancefloor state
   - `notes` (string): Commentary or script notes
   - `duration` (number): Seconds for this state
   - `next_state` (string): Reference to next dancefloor state
   
2. **Dancer Extensions**:
   - `number` (integer): Unique dancer number
   - `alias` (string): Alternate name
   - `height` (string): Affects visual scaling
   
3. **Position Metadata**:
   - `formation` (string): Current formation name
   - `set_number` (integer): Which set this position belongs to
   - `distance_to_next` (number): Space to next position

4. **Rendering Hints**:
   - `renderOptions` (object): Specific rendering preferences
   - `highlight` (boolean): Whether to highlight this dancer
   - `animation_speed` (number): Speed for this state transition

## Questions & Clarifications

**Q: Can `facing` coordinate be the same as `coord`?**
A: Yes, it indicates the dancer is facing their own position (rare but valid).

**Q: Can multiple dancers occupy the same position?**
A: No, each position should have exactly one dancer.

**Q: What happens if facing position is off-grid?**
A: This is valid - the renderer will extrapolate the direction vector. Validation allows any numeric values.

**Q: Can `couples` count not match actual dancers?**
A: Yes, `couples` is informational (used for layout hints). The renderer counts actual dancers from `positions`.

**Q: How should the Python engine handle invalid dancefloor data?**
A: Validate before responding. Return error with specific validation failure details.

**Q: How should the JavaScript renderer handle invalid data?**
A: Validate on load. Render with error indicator showing which positions are invalid. Log to console.
