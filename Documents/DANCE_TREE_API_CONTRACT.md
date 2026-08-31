# Dance Tree API Communication Contract

## Purpose

This document defines the contract between the Python dance engine and the JavaScript UI for managing dance tree structures. It specifies how dance choreography is represented as hierarchical tree data and communicated via API.

## Overview

The Dance Tree API provides two primary operations:
1. **Get Dance Tree** - Retrieve complete dance structure as a jsTree-compatible tree
2. **List Dances** - Retrieve available dances with metadata

Dance trees represent the hierarchical structure of a dance:
- **Root** = Dance
- **Branches** = Groups of figures (series/parallel)
- **Leaves** = Individual figures

All communications are governed by formal JSON Schemas for validation and consistency.

## Core Principles

1. **Hierarchical Structure**: Dance choreography is represented as a tree, not a flat list
2. **Group Types**: Groups can be "series" (sequential) or "parallel" (simultaneous)
3. **Figure Resolution**: Each leaf node references a specific figure definition
4. **Position Anchoring**: Each figure can specify an anchor position in the dance
5. **Addon Support**: Figures can include addon modifiers (e.g., "E2c" for H1DR)
6. **Complete Definition**: Tree includes sufficient data to render or execute the dance
7. **Error Clarity**: All errors are structured and provide actionable information

## API Endpoints

### 1. List Dances

#### Request

**Endpoint**: `GET /api/dances`

**Query Parameters** (all optional):
```
?version=N           - Filter by schema version (integer)
?minCouples=N       - Filter dances for at least N couples (integer)
?maxCouples=N       - Filter dances for at most N couples (integer)
?search=TERM        - Search by name or description (substring, case-insensitive)
?limit=N            - Limit response to N items (integer, default 100, max 1000)
?offset=N           - Pagination offset (integer, default 0)
?sort=FIELD         - Sort by field ('name', 'couples', 'version', default 'name')
?order=ASC|DESC     - Sort order (default 'ASC')
```

**Request Headers**:
```
Accept: application/json
Accept-Encoding: gzip, deflate
```

**Example Request**:
```
GET /api/dances?minCouples=3&sort=name HTTP/1.1
Host: localhost:5000
Accept: application/json
```

#### Response

**Success Response** (HTTP 200 OK):

```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-08-30T23:35:00Z",
  "count": 2,
  "total": 12,
  "offset": 0,
  "limit": 100,
  "filters_applied": {
    "minCouples": 3
  },
  "dances": [
    {
      "file": "Marries Wedding_all.json",
      "Name": "Marries Wedding",
      "Desc": "A traditional Scottish dance",
      "shape": "3/32",
      "Version": 3,
      "EstimatedBars": 40,
      "Couples": "3",
      "Formation": "square"
    },
    {
      "file": "Dances/BotheredAbout.json",
      "Name": "Bothered About",
      "Desc": "A lively Strathspey",
      "shape": "3/32",
      "Version": 3,
      "EstimatedBars": 32,
      "Couples": "3",
      "Formation": "square"
    }
  ]
}
```

**Response Schema**: Validated by `api_dances_list.schema.json`

**Response Fields**:
- `status` - Always "ok" on success
- `version` - API contract version
- `timestamp` - ISO 8601 UTC timestamp
- `count` - Number of dances in this response
- `total` - Total number of dances matching filters
- `offset` - Current pagination offset
- `limit` - Maximum items per page
- `filters_applied` - Echo back of filters applied
- `dances` - Array of dance summaries

**Dance Summary Fields**:
- `file` - Filename where dance is stored
- `Name` - Display name
- `Desc` - Human-readable description
- `shape` - Dance shape (e.g., "3/32", "4/40")
- `Version` - Schema version of the dance definition
- `EstimatedBars` - Total bars in the dance (calculated)
- `Couples` - Number of couples (from shape)
- `Formation` - Formation type (square, circle, line, etc.)

#### Error Responses

**Bad Request** (HTTP 400):
```json
{
  "status": "error",
  "error": "invalid_request",
  "code": 400,
  "message": "Invalid parameter: minCouples must be between 1 and 16",
  "details": {
    "parameter": "minCouples",
    "value": "20",
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
  "message": "Failed to load dance database",
  "details": {
    "operation": "load_dances",
    "hint": "Check that data/Dances directory exists and is readable"
  }
}
```

---

### 2. Get Dance Tree

#### Request

**Endpoint**: `GET /api/dances/<identifier>/tree`

**URL Parameters**:
- `<identifier>` - Dance key or filename (with or without .json extension)

**Query Parameters** (optional):
```
?expand=true       - Return expanded tree (all nodes open)
?format=jstree     - Output format ('jstree' default, future: 'graph', 'flat')
```

**Request Headers**:
```
Accept: application/json
```

**Example Request**:
```
GET /api/dances/Marries%20Wedding_all/tree HTTP/1.1
Host: localhost:5000
Accept: application/json
```

#### Response

**Success Response** (HTTP 200 OK):

```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-08-30T23:36:00Z",
  "format": "jstree",
  "dance": {
    "file": "Marries Wedding_all.json",
    "Name": "Marries Wedding",
    "Desc": "A traditional Scottish dance",
    "shape": "3/32",
    "Version": 3
  },
  "tree": {
    "id": "root",
    "text": "Marries Wedding",
    "children": [
      {
        "id": "node-0",
        "text": "Series (Bars 1-8)",
        "type": "group",
        "children": [
          {
            "id": "node-0-0",
            "text": "1cRT (Right Hand Turn)",
            "type": "figure",
            "data": {
              "figureName": "1cRT",
              "anchor": [0, 0],
              "addons": [],
              "bars": 2,
              "startPos": [[0, 0], [0, 2]],
              "endPos": [[0, 0], [0, 2]],
              "original": ["1cRT", []]
            }
          },
          {
            "id": "node-0-1",
            "text": "1cCast1p (Cast One Place)",
            "type": "figure",
            "data": {
              "figureName": "1cCast1p",
              "anchor": [0, 0],
              "addons": [],
              "bars": 2,
              "original": ["1cCast1p", []]
            }
          }
        ],
        "data": {
          "groupType": "s",
          "groupIndex": 0,
          "expanded": true,
          "original": ["s", [...]]
        }
      },
      {
        "id": "node-1",
        "text": "Series (Bars 9-24)",
        "type": "group",
        "children": [
          {
            "id": "node-1-0",
            "text": "1cLT (Left Hand Turn)",
            "type": "figure",
            "data": {
              "figureName": "1cLT",
              "anchor": [0, 0],
              "addons": [],
              "bars": 4,
              "original": ["1cLT", []]
            }
          },
          {
            "id": "node-1-1",
            "text": "H1DR with E2c (Half Diagonal Reel, End 2 Corners)",
            "type": "figure",
            "data": {
              "figureName": "H1DR",
              "anchor": [0, 0],
              "addons": ["E2c"],
              "bars": 4,
              "original": ["H1DR", ["E2c"]]
            }
          }
        ],
        "data": {
          "groupType": "s",
          "groupIndex": 1,
          "expanded": true,
          "original": ["s", [...]]
        }
      }
    ],
    "data": {
      "figureName": "Marries Wedding",
      "version": 3,
      "original": [...]
    }
  }
}
```

**Response Schema**: Validated by `api_dance_tree_response.schema.json`

**Response Fields**:
- `status` - Always "ok" on success
- `version` - API contract version
- `timestamp` - ISO 8601 UTC timestamp
- `format` - Tree format (currently "jstree")
- `dance` - Dance metadata
- `tree` - jsTree-compatible tree structure

#### Error Responses

**Not Found** (HTTP 404):
```json
{
  "status": "error",
  "error": "not_found",
  "code": 404,
  "message": "Dance not found: UnknownDance",
  "details": {
    "identifier": "UnknownDance",
    "type": "dance",
    "hint": "Check the dance name from /api/dances list"
  }
}
```

**Invalid Request** (HTTP 400):
```json
{
  "status": "error",
  "error": "invalid_request",
  "code": 400,
  "message": "Invalid dance identifier format",
  "details": {
    "identifier": "../../../etc/passwd",
    "reason": "path_traversal_attempt"
  }
}
```

---

## Data Structures (Detailed)

### Dance Summary Format

Used in the `/api/dances` list response.

```json
{
  "file": "string",
  "Name": "string",
  "Desc": "string",
  "shape": "string (e.g., '3/32')",
  "Version": "integer",
  "EstimatedBars": "integer",
  "Couples": "string",
  "Formation": "string"
}
```

### jsTree Node Format

Each node in the tree follows jsTree conventions:

```json
{
  "id": "string (unique within tree)",
  "text": "string (display text)",
  "type": "group | figure | root",
  "children": "array of jsTree nodes (optional)",
  "data": {
    "figureName": "string",
    "version": "integer (optional)",
    "bars": "integer or array (optional)",
    "anchor": "[row, col] (optional)",
    "addons": "array of strings (optional)",
    "startPos": "array of positions (optional)",
    "endPos": "array of positions (optional)",
    "groupType": "s | p (series or parallel, for groups)",
    "groupIndex": "integer (for groups)",
    "expanded": "boolean (for groups)",
    "original": "original data structure from dance JSON"
  }
}
```

### Group Types

- `"s"` - **Series**: Figures execute sequentially (one after another)
- `"p"` - **Parallel**: Figures execute simultaneously (different couples doing different things)

### Figure Reference Format

In dance JSON, figures are referenced as:

**Simple figure reference**:
```json
"1cRT"
```

**Figure with anchor and addons**:
```json
["H1DR", ["E2c"]]
```

or with explicit anchor:
```json
["H1DR", {"anchor": [0, 0], "addons": ["E2c"]}]
```

---

## Dance Tree Structure

### Root Node

The root node represents the entire dance:

```json
{
  "id": "root",
  "text": "Dance Name",
  "type": "root",
  "children": [...],
  "data": {
    "figureName": "Dance Name",
    "version": 3,
    "original": [...]
  }
}
```

### Group Nodes

Group nodes contain multiple figures (series or parallel):

```json
{
  "id": "node-0",
  "text": "Series (Bars 1-8)",
  "type": "group",
  "children": [...],
  "data": {
    "groupType": "s",
    "groupIndex": 0,
    "expanded": true,
    "original": ["s", [...]]
  }
}
```

### Leaf Nodes (Figures)

Leaf nodes represent individual figures:

```json
{
  "id": "node-0-0",
  "text": "1cRT (Right Hand Turn)",
  "type": "figure",
  "children": [],
  "data": {
    "figureName": "1cRT",
    "anchor": [0, 0],
    "addons": [],
    "bars": 2,
    "original": ["1cRT", []]
  }
}
```

---

## Dance Shape Format

The `shape` field describes the dance structure:

```
COUPLES/BARS
3/32      = 3 couples, 32 bars
4/40      = 4 couples, 40 bars
3/48      = 3 couples, 48 bars
```

### Common Shapes

| Shape | Meaning | Examples |
|-------|---------|----------|
| 3/32 | 3 couples, 32 bars | Most common Scottish dances |
| 3/40 | 3 couples, 40 bars | Longer dances |
| 4/32 | 4 couples, 32 bars | Square formations |

---

## Pagination

All list endpoints support pagination using `limit` and `offset` parameters.

**Defaults**:
- `limit`: 100 items
- `offset`: 0

**Constraints**:
- Maximum limit: 1000 items per request
- Minimum limit: 1 item per request

**Example**: Retrieve dances 20-40
```
GET /api/dances?offset=20&limit=20
```

---

## Filtering and Search

### By Couple Count

```
GET /api/dances?minCouples=3&maxCouples=4
```

### By Shape

```
GET /api/dances?shape=3/32
```

### By Name/Description

```
GET /api/dances?search=wedding
```

Searches both `Name` and `Desc` fields (substring, case-insensitive).

### By Version

```
GET /api/dances?version=3
```

---

## Versioning

### API Version

The Dance Tree API version is specified in the response:
```json
{
  "version": "1",
  ...
}
```

### Dance Schema Version

Each dance has a `Version` field indicating its schema version:
```json
{
  "Version": 3
}
```

### Compatibility

- **Version 1**: Initial release (Schema Version 3 dances)
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
| `not_found` | 404 | Requested dance does not exist |
| `server_error` | 500 | Internal server error |
| `service_unavailable` | 503 | Server temporarily unavailable |

---

## Example Workflows

### Workflow 1: Display Dance List in UI

```javascript
// Step 1: Fetch all dances
const response = await fetch('/api/dances');
const data = await response.json();

if (data.status !== 'ok') {
  console.error('Failed to load dances:', data.message);
  return;
}

// Step 2: Populate UI list
data.dances.forEach(dance => {
  addDanceToList(dance.Name, dance.file, dance.Desc);
});

// Step 3: Show pagination info
console.log(`Loaded ${data.count}/${data.total} dances`);
```

### Workflow 2: Display Dance Tree in jsTree

```javascript
// Step 1: Get dance identifier (from list)
const danceName = 'Marries Wedding_all';

// Step 2: Fetch tree structure
const response = await fetch(`/api/dances/${danceName}/tree`);
const data = await response.json();

if (data.status !== 'ok') {
  console.error('Failed to load dance tree:', data.message);
  return;
}

// Step 3: Initialize jsTree with response
$('#tree').jstree({
  core: {
    data: [data.tree]
  }
});

// Step 4: Display dance metadata
displayDanceInfo(data.dance);
```

### Workflow 3: Execute Dance from Tree

```javascript
// When user selects a figure node in tree:
const nodeData = node.data;

if (nodeData.figureName && nodeData.original) {
  // Execute the figure
  const response = await fetch('/api/dancefloor/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      figure: nodeData.figureName,
      couples: 3,
      anchor: nodeData.anchor || [0, 0],
      addons: nodeData.addons || []
    })
  });
  
  const result = await response.json();
  displayDancefloor(result.floor);
  displayCrips(result.crips);
}
```

### Workflow 4: Filter Dances by Couples

```javascript
// Fetch only 3-couple dances
const response = await fetch('/api/dances?minCouples=3&maxCouples=3&sort=name');
const data = await response.json();

console.log(`Found ${data.count} 3-couple dances`);
data.dances.forEach(dance => console.log(dance.Name));
```

---

## Implementation Notes

### Backend (Python/Flask)

1. Load dance definitions from `data/Dances/` directory
2. Cache dance metadata and tree structures for performance
3. Validate all query parameters
4. Recursively build tree structure from dance FigureList
5. Return errors in standard format
6. Handle circular references in figure definitions gracefully

### Frontend (JavaScript)

1. Cache dance list in-memory to reduce API calls
2. Lazy-load tree structures (fetch only when user expands)
3. Implement client-side filtering for better UX
4. Validate error responses and display user-friendly messages
5. Handle network errors gracefully
6. Use jsTree widget for tree rendering

---

## Performance Considerations

### Caching

Dance data is relatively static. Recommended caching:
- **Client-side**: Cache for session (clear on logout)
- **Server-side**: Cache for 1 hour (invalidate when files change)

### Response Size

Typical dance tree response (complex 3-couple dance):
- **Uncompressed**: ~50-150 KB
- **Gzip compressed**: ~10-30 KB

### Tree Rendering

Large trees (100+ nodes) may impact browser performance:
- Consider lazy-loading child nodes on expand
- Implement virtual scrolling for large lists
- Use `expand=false` by default for large trees

---

## Security Considerations

1. **Path Traversal Prevention**
   - Validate dance identifiers to prevent `../` attacks
   - Only allow alphanumeric, underscore, hyphen in identifiers

2. **Resource Exhaustion**
   - Limit `limit` parameter to reasonable maximum (1000)
   - Implement rate limiting on complex tree operations
   - Set maximum tree depth to prevent infinite recursion

3. **Information Disclosure**
   - Do not expose internal file paths in error messages
   - Provide only actionable error details

---

## Appendix: Schema Validation

All Dance Tree API responses must conform to these schemas:

- **Dance List Response**: `api_dances_list.schema.json`
- **Dance Tree Response**: `api_dance_tree_response.schema.json`
- **Dance Detail Response**: `dance.schema.json`
- **jsTree Node Format**: `jstree_node.schema.json`
- **Error Response**: `api_error.schema.json`

Use these schemas in your client and server validation code to ensure compatibility.
