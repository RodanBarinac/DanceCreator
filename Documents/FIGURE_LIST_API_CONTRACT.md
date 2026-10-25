# Figure List API Communication Contract

## Purpose

This document defines the contract between the Python dance engine and the JavaScript UI for managing figure lists. It specifies the structure and behavior of all figure-related API communications.

## Overview

The Figure List API provides three primary operations:
1. **List Figures** - Retrieve available figures with metadata
2. **Get Figure Detail** - Retrieve complete figure definition
3. **Search Figures** - Filter figures by properties (optional advanced feature)

All communications are governed by formal JSON Schemas for validation and consistency.

## Core Principles

1. **Discoverability**: All available figures must be discoverable without prior knowledge
2. **Minimal Overhead**: List responses should be lightweight (no full definitions)
3. **Versioning**: Each figure has an explicit version for compatibility tracking
4. **Metadata Completeness**: List responses include sufficient metadata for UI display
5. **Error Clarity**: All errors are structured and provide actionable information
6. **Backwards Compatibility**: API versions support older clients gracefully

## API Endpoints

### 1. List Figures

#### Request

**Endpoint**: `GET /api/figures`

**Query Parameters** (all optional):
```
?version=N              - Filter by schema version (integer)
?formation=TYPE        - Filter by formation type (string: 'turn', 'reel', 'hey', etc.)
?minBars=N            - Filter figures with at least N bars (integer)
?maxBars=N            - Filter figures with at most N bars (integer)
?search=TERM          - Search by name or description (substring, case-insensitive)
?limit=N              - Limit response to N items (integer, default 100, max 1000)
?offset=N             - Pagination offset (integer, default 0)
?sort=FIELD           - Sort by field ('name', 'bars', 'version', default 'name')
?order=ASC|DESC       - Sort order (default 'ASC')
```

**Request Headers**:
```
Accept: application/json
Accept-Encoding: gzip, deflate
```

**Example Request**:
```
GET /api/figures?formation=reel&minBars=4&sort=name HTTP/1.1
Host: localhost:5000
Accept: application/json
```

#### Response

**Success Response** (HTTP 200 OK):

```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-08-30T23:30:00Z",
  "count": 3,
  "total": 15,
  "offset": 0,
  "limit": 100,
  "filters_applied": {
    "formation": "reel",
    "minBars": 4
  },
  "figures": [
    {
      "key": "H1DR",
      "file": "H1DR.json",
      "Name": "Half Diagonal Reel",
      "Desc": "Half Diagonal Reel on the first diagonal",
      "Formation": "reel",
      "Bars": 4,
      "Version": 2,
      "StartPos": [[0, -1], [0.5, -0.5], [1.5, 0.5], [2, 1]],
      "EndPos": [[2, 1], [1.5, 0.5], [0.5, -0.5], [0, -1]],
      "HasFacing": true,
      "Addons": ["E2c", "ELA"]
    },
    {
      "key": "H2DR",
      "file": "H2DR.json",
      "Name": "Half Diagonal Reel (Second Diagonal)",
      "Desc": "Half Diagonal Reel on the second diagonal",
      "Formation": "reel",
      "Bars": 4,
      "Version": 2,
      "StartPos": [[0, 1], [0.5, 0.5], [1.5, -0.5], [2, -1]],
      "EndPos": [[2, -1], [1.5, -0.5], [0.5, 0.5], [0, 1]],
      "HasFacing": true,
      "Addons": ["E2c", "ELA"]
    }
  ]
}
```

**Response Schema**: Validated by `api_figures_list.schema.json`

**Response Fields**:
- `status` - Always "ok" on success
- `version` - API contract version (for versioning support)
- `timestamp` - ISO 8601 UTC timestamp of response generation
- `count` - Number of figures in this response
- `total` - Total number of figures matching filters (for pagination)
- `offset` - Current pagination offset
- `limit` - Maximum items per page
- `filters_applied` - Echo back of filters that were applied
- `figures` - Array of figure summaries

**Figure Summary Fields**:
- `key` - Unique identifier (used in API calls)
- `file` - Filename where this figure is stored
- `Name` - Display name
- `Desc` - Human-readable description
- `Formation` - Type of formation (turn, reel, hey, etc.)
- `Bars` - Number of bars (integer or array if variable)
- `Version` - Schema version of the figure definition
- `StartPos` - Starting positions (for UI preview)
- `EndPos` - Ending positions (for UI preview)
- `HasFacing` - Boolean indicating if figure includes facing information
- `Addons` - Array of available addon names

#### Error Responses

**Bad Request** (HTTP 400):
```json
{
  "status": "error",
  "error": "invalid_request",
  "code": 400,
  "message": "Invalid parameter: limit must be between 1 and 1000",
  "details": {
    "parameter": "limit",
    "value": "2000",
    "reason": "exceeds_maximum"
  }
}
```

**Internal Server Error** (HTTP 500):
```json
{
  "status": "error",
  "error": "server_error",
  "code": 500,
  "message": "Failed to load figure database",
  "details": {
    "operation": "load_figures",
    "hint": "Check that data/Figures directory exists and is readable"
  }
}
```

**Error Schema**: Validated by `api_error.schema.json`

---

### 2. Get Figure Detail

#### Request

**Endpoint**: `GET /api/figures/<identifier>`

**URL Parameters**:
- `<identifier>` - Figure key or filename (with or without .json extension)

**Request Headers**:
```
Accept: application/json
```

**Example Request**:
```
GET /api/figures/H1DR HTTP/1.1
Host: localhost:5000
Accept: application/json
```

#### Response

**Success Response** (HTTP 200 OK):

```json
{
  "status": "ok",
  "figure": {
    "EndFacing": [[], [2,1], [0,-1], []],
    "CriptDesc": [
      "{Dancer} dances half a diagonal reel to end in {EndPos}",
      "{Dancer} dances half a diagonal reel to face {Face}",
      "{Dancer} dances half a diagonal reel to face {Face}",
      "{Dancer} dances half a diagonal reel to end in {EndPos}"
    ],
    "StartPos": [[0, -1], [0.5, -0.5], [1.5, 0.5], [2, 1]],
    "EndPos": [[2, 1], [1.5, 0.5], [0.5, -0.5], [0, -1]],
    "StartDancers": ["2m", "1w", "1m", "3w"],
    "StartFacing": [[0.5, -0.5], [0, -1], [2, 1], [1.5, 0.5]],
    "Name": "Half Diagonal Reel",
    "Desc": "Half Diagonal Reel on the first diagonal",
    "Formation": "reel",
    "Bars": 4,
    "Version": 2,
    "Addons": {
      "E2c": {
        "EndFacing": [[], [2,-1], [0,1], []],
        "EndPos": [[2, 1], [1.5, -0.5], [0.5, 0.5], [0, -1]],
        "Name": "E2c",
        "Desc": "End facing 2 corner",
        "Version": 1
      },
      "ELA": {
        "EndFacing": [[], [], [], []],
        "EndPos": [[2, 1], [2, 0], [0, 0], [0, -1]],
        "Name": "ELA",
        "CriptDesc": ["", "end {EndPos}", "end {EndPos}", ""],
        "CriptReplace": ["", "face {Face}", "face {Face}", ""],
        "Desc": "End in lines across",
        "Version": 1
      }
    }
  }
}
```

**Response Schema**: Validated by `figure.schema.json`

Simple figure definitions may include optional `StartDancers` and `StartFacing` arrays parallel to `StartPos`. `StartDancers` IDs have the form `2m` or `1w`; automatic entries are allocated by start order and all resolved IDs must be unique. `StartFacing` entries are empty arrays or `[row, column]` target coordinates, not direction vectors. These values define an isolated catalog preview only; when a figure runs in a dance, floor dancers retain their existing identity and incoming facing.

#### Isolated Figure Preview

`POST /api/figures/<identifier>/preview` renders one simple figure on its own. Preview dancer names/genders come from `StartDancers` (or the automatic allocation), and incoming facing comes from `StartFacing` (or the same-row opposite-line default). Couple color continues to follow the numeric couple part of each dancer ID. `StartFacing` and `StartDancers` do not override the actual dancers or facing inside a dance.

#### Error Responses

**Not Found** (HTTP 404):
```json
{
  "status": "error",
  "error": "not_found",
  "code": 404,
  "message": "Figure not found: UnknownFigure",
  "details": {
    "identifier": "UnknownFigure",
    "type": "figure",
    "hint": "Check the figure key from /api/figures list"
  }
}
```

**Invalid Request** (HTTP 400):
```json
{
  "status": "error",
  "error": "invalid_request",
  "code": 400,
  "message": "Invalid figure identifier format",
  "details": {
    "identifier": "../../../etc/passwd",
    "reason": "path_traversal_attempt"
  }
}
```

---

## Data Structures (Detailed)

### Figure Summary Format

Used in the `/api/figures` list response.

```json
{
  "key": "string",
  "file": "string",
  "Name": "string",
  "Desc": "string",
  "Formation": "string",
  "Bars": "integer or array",
  "Version": "integer",
  "StartPos": "array of [row, col] pairs",
  "EndPos": "array of [row, col] pairs",
  "StartDancers": "optional array of dancer IDs parallel to StartPos",
  "StartFacing": "optional array of target-coordinate pairs (empty entry means default)",
  "HasFacing": "boolean",
  "Addons": "array of strings"
}
```

### Figure Detail Format

Full figure definition as stored in JSON files. See `figure.schema.json` for complete specification.

Key elements:
- **SimpleFigure**: Has `StartPos`, `EndPos`, `Bars`, `CriptDesc`, `Formation`
- **ComplexFigure**: Has `FigureList` containing nested figures
- **Addons**: Modifications to base figure behavior

---

## Pagination

All list endpoints support pagination using `limit` and `offset` parameters.

**Defaults**:
- `limit`: 100 items
- `offset`: 0

**Constraints**:
- Maximum limit: 1000 items per request
- Minimum limit: 1 item per request

**Example**: Retrieve figures 20-40
```
GET /api/figures?offset=20&limit=20
```

---

## Filtering and Search

### By Formation Type

```
GET /api/figures?formation=reel
```

Valid formations (case-insensitive):
- `turn` - Hand turns
- `reel` - Reels
- `hey` - Heys
- `circle` - Circles
- `line` - Lines

### By Bar Count

```
GET /api/figures?minBars=4&maxBars=8
```

### By Name/Description

```
GET /api/figures?search=reel
```

Searches both `Name` and `Desc` fields (substring, case-insensitive).

### By Version

```
GET /api/figures?version=2
```

---

## Versioning

### API Version

The Figure List API version is specified in the response:
```json
{
  "version": "1",
  ...
}
```

### Figure Schema Version

Each figure has a `Version` field indicating its schema version:
```json
{
  "Version": 2
}
```

### Compatibility

- **Version 1**: Initial release
- **Future versions**: Will be announced with migration guides
- **Backwards compatibility**: Older clients can continue using Version 1 APIs

---

## Error Handling

### Error Response Structure

All errors follow this pattern:

```json
{
  "status": "error",
  "error": "ERROR_CODE",
  "code": 400,
  "message": "Human-readable error message",
  "details": {
    "field": "value"
  }
}
```

### Common Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `invalid_request` | 400 | Malformed request or invalid parameters |
| `not_found` | 404 | Requested figure does not exist |
| `server_error` | 500 | Internal server error |
| `service_unavailable` | 503 | Server temporarily unavailable |

---

## Example Workflows

### Workflow 1: Display Figure List in UI

```javascript
// Step 1: Fetch all figures
const response = await fetch('/api/figures');
const data = await response.json();

if (data.status !== 'ok') {
  console.error('Failed to load figures:', data.message);
  return;
}

// Step 2: Populate UI list
data.figures.forEach(fig => {
  addFigureToList(fig.Name, fig.key, fig.Desc);
});

// Step 3: Show pagination info
console.log(`Loaded ${data.count}/${data.total} figures`);
```

### Workflow 2: Load Figure for Editing

```javascript
// Step 1: Get figure summary (key from list)
const figureKey = 'H1DR';

// Step 2: Fetch full definition
const response = await fetch(`/api/figures/${figureKey}`);
const data = await response.json();

if (data.status !== 'ok') {
  console.error('Failed to load figure:', data.message);
  return;
}

// Step 3: Display in editor
displayFigureEditor(data.figure);
```

### Workflow 3: Filter by Formation Type

```javascript
// Fetch only reel figures
const response = await fetch('/api/figures?formation=reel&sort=name');
const data = await response.json();

console.log(`Found ${data.count} reel figures`);
data.figures.forEach(fig => console.log(fig.Name));
```

---

## Implementation Notes

### Backend (Python/Flask)

1. Load all figures from `data/Figures/` directory
2. Cache figure metadata for performance
3. Implement filtering logic before pagination
4. Validate all query parameters
5. Return errors in standard format

### Frontend (JavaScript)

1. Cache figure list in-memory to reduce API calls
2. Implement client-side pagination/filtering for better UX
3. Validate error responses and display user-friendly messages
4. Handle network errors gracefully
5. Use Accept-Encoding for compression support

---

## Performance Considerations

### Caching

The figure list is relatively static. Recommended caching:
- **Client-side**: Cache for session (clear on logout)
- **Server-side**: Cache for 1 hour (invalidate when files change)

### Response Size

Typical figure list response (100 figures):
- **Uncompressed**: ~50-100 KB
- **Gzip compressed**: ~10-20 KB

### Pagination

For large deployments (1000+ figures):
- Always use pagination
- Default to 50-100 items per page
- Implement server-side result set limits

---

## Security Considerations

1. **Path Traversal Prevention**
   - Validate figure identifiers to prevent `../` attacks
   - Only allow alphanumeric, underscore, hyphen in identifiers

2. **Resource Exhaustion**
   - Limit `limit` parameter to reasonable maximum (1000)
   - Implement rate limiting on search operations

3. **Information Disclosure**
   - Do not expose internal file paths in error messages
   - Provide only actionable error details

---

## Appendix: Schema Validation

All Figure List API responses must conform to these schemas:

- **Figure List Response**: `api_figures_list.schema.json`
- **Figure Detail Response**: `figure.schema.json`
- **Error Response**: `api_error.schema.json`

Use these schemas in your client and server validation code to ensure compatibility.


## Centered-grid coordinates and composable addons

Figure offsets use the centered grid: columns are `-1` (men), `0` (centre), and `+1`
(ladies); rows remain 1-based and unchanged. Serialized end-facing data uses `EndFacing`; the
legacy `Faceing` spelling is not accepted, and `Facing` alone is not a key or property.
Optional `StartDancers` and `StartFacing` fields are available for isolated preview; their validation and execution semantics are described above.

Engine-reserved addon names `B<n>` (capital B followed by any positive integer) set the bar count
on any simple figure and are not defined in the figure file; they change bars only, and can
shorten or lengthen the figure. Other addons can modify positions, end facing, and/or instruction
text. Addons are combined, but changing the same field for the same dancer is an error; multiple
`B<n>` duration addons are also an error. `1cLT` with `B4` and `E1c` replaces `1cLT1c`: `B4`
sets four bars only, while `E1c` changes end positions, end facing, and ending text without
changing bars. Two half reels each using `B3` form a six-bar reel; there are no separate 6- or
8-bar reel figures.
