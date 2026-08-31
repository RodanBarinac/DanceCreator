# Engine-UI Communication Contracts - Overview

## Introduction

This document provides an overview of all formal communication contracts between the Python dance engine and the JavaScript UI. These contracts ensure consistent, validated data exchange across all system layers.

## Contract Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│         Engine-UI Communication Contracts                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
├─ Dancefloor Renderer Contract                               │
│  └─ Contracts dancefloor visualization communication         │
│     File: DANCEFLOOR_RENDERER_CONTRACT.md                    │
│     Schema: dancefloor_contract.schema.json                  │
│     Scope: Real-time dancefloor state for rendering          │
│                                                               │
├─ Figure List API Contract                                    │
│  └─ Contracts figure list/detail communication               │
│     File: FIGURE_LIST_API_CONTRACT.md                        │
│     Schemas:                                                  │
│       • api_figures_list.schema.json (GET /api/figures)      │
│       • figure.schema.json (GET /api/figures/<id>)           │
│     Scope: Discover and load figure definitions              │
│                                                               │
├─ Dance Tree API Contract                                     │
│  └─ Contracts dance tree communication                        │
│     File: DANCE_TREE_API_CONTRACT.md                         │
│     Schemas:                                                  │
│       • api_dances_list.schema.json (GET /api/dances)        │
│       • api_dance_tree_response.schema.json (GET /tree)      │
│       • dance.schema.json (GET /api/dances/<id>)             │
│     Scope: Dance choreography hierarchy                      │
│                                                               │
└─ Error Response Contract                                     │
   └─ Contracts error handling                                 │
      File: All contracts use api_error.schema.json            │
      Schema: api_error.schema.json                            │
      Scope: Consistent error responses across all APIs        │
```

## Quick Reference

### 1. Dancefloor Renderer Contract

**Purpose**: Serialize dancefloor state for visualization

**Key Components**:
- `name` - Dancefloor identifier
- `couples` - Number of couples
- `tick` - Current bar/beat
- `positions` - Map of dancer positions with facing

**Example**:
```json
{
  "name": "Initial Setup",
  "couples": 3,
  "tick": 1,
  "positions": {
    "1m": { "dancer": {"name": "M1", "gender": "M"}, "coord": [1, 1], "facing": [1, 3] },
    "1w": { "dancer": {"name": "W1", "gender": "F"}, "coord": [1, 3], "facing": [1, 1] }
  }
}
```

**Documents**: 
- `DANCEFLOOR_RENDERER_CONTRACT.md` (specification)
- `schema/dancefloor_contract.schema.json` (validation)

---

### 2. Figure List API Contract

**Purpose**: Discover available figures and retrieve definitions

**Endpoints**:
- `GET /api/figures` - List available figures
- `GET /api/figures/<identifier>` - Get full figure definition

**Response Structure**:
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "ISO-8601",
  "count": 3,
  "total": 15,
  "offset": 0,
  "limit": 100,
  "filters_applied": {...},
  "figures": [
    {
      "key": "H1DR",
      "file": "H1DR.json",
      "Name": "Half Diagonal Reel",
      "Desc": "...",
      "Formation": "reel",
      "Bars": 4,
      "Version": 2,
      "StartPos": [...],
      "EndPos": [...],
      "HasFacing": true,
      "Addons": ["E2c", "ELA"]
    }
  ]
}
```

**Features**:
- Pagination support (limit, offset)
- Filtering (formation, bars, version)
- Search by name/description
- Metadata for UI preview
- Complete error responses

**Documents**:
- `FIGURE_LIST_API_CONTRACT.md` (specification)
- `schema/api_figures_list.schema.json` (list response)
- `schema/figure.schema.json` (detail response)
- `schema/api_error.schema.json` (errors)

---

### 3. Dance Tree API Contract

**Purpose**: Represent dance choreography as hierarchical tree

**Endpoints**:
- `GET /api/dances` - List available dances
- `GET /api/dances/<identifier>/tree` - Get dance tree structure

**Response Structure**:
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "ISO-8601",
  "format": "jstree",
  "dance": {
    "file": "...",
    "Name": "Marries Wedding",
    "Desc": "...",
    "shape": "3/32",
    "Version": 3
  },
  "tree": {
    "id": "root",
    "text": "Marries Wedding",
    "type": "root",
    "children": [
      {
        "id": "node-0",
        "text": "Series (Bars 1-8)",
        "type": "group",
        "data": {"groupType": "s", "expanded": true},
        "children": [
          {
            "id": "node-0-0",
            "text": "1cRT",
            "type": "figure",
            "data": {"figureName": "1cRT", "bars": 2}
          }
        ]
      }
    ],
    "data": {}
  }
}
```

**Features**:
- jsTree-compatible format
- Hierarchical group/figure structure
- Series (s) and parallel (p) groups
- Figure metadata for execution
- Addon support
- Pagination for dance lists

**Documents**:
- `DANCE_TREE_API_CONTRACT.md` (specification)
- `schema/api_dances_list.schema.json` (list response)
- `schema/api_dance_tree_response.schema.json` (tree response)
- `schema/dance.schema.json` (dance definition)
- `schema/api_error.schema.json` (errors)

---

## Workflow Integration Map

```
User Interface
    │
    ├─→ [Figure List API] ─→ GET /api/figures
    │                         ↓
    │                    Figure Database
    │                         ↓
    │                    api_figures_list ←─┐
    │                                        │
    ├─→ [Dance Tree API] ─→ GET /api/dances │
    │                         ↓              │
    │                    Dance Database      │
    │                         ↓              │
    │                    api_dances_list ←──┤
    │                                        │
    ├─→ [Dance Tree API] ─→ GET /api/dances/<id>/tree
    │                         ↓              │
    │                    Dance Definition    │
    │                         ↓              │
    │                    api_dance_tree_response
    │
    ├─→ [Dancefloor Renderer] ─→ POST /api/dancefloor/execute
    │                              ↓
    │                         Figure Execution
    │                              ↓
    │                         dancefloor_contract
    │                              ↓
    │                         Render on Canvas
    │
    └─→ Error Responses ←──────────── api_error (all APIs)
```

## Schema Files Summary

| File | Purpose | Type |
|------|---------|------|
| `dancefloor_contract.schema.json` | Dancefloor state | Response |
| `api_figures_list.schema.json` | Figure list response | Response |
| `api_dances_list.schema.json` | Dance list response | Response |
| `api_dance_tree_response.schema.json` | Dance tree response | Response |
| `figure.schema.json` | Figure definition | Data model |
| `dance.schema.json` | Dance definition | Data model |
| `jstree_node.schema.json` | jsTree node format | Data format |
| `api_error.schema.json` | Error response | Response |

## Implementation Checklist

### Backend (Python)

- [ ] Implement `/api/figures` endpoint with filtering/pagination
- [ ] Implement `/api/figures/<id>` endpoint
- [ ] Validate all responses against api_figures_list.schema.json
- [ ] Implement `/api/dances` endpoint with filtering/pagination
- [ ] Implement `/api/dances/<id>/tree` endpoint
- [ ] Validate all responses against api_dance_tree_response.schema.json
- [ ] Implement error responses using api_error.schema.json
- [ ] Add query parameter validation
- [ ] Implement response caching for performance
- [ ] Add rate limiting (optional but recommended)

### Frontend (JavaScript)

- [ ] Load figure list with pagination support
- [ ] Implement figure filtering/search UI
- [ ] Display figure details when selected
- [ ] Load dance list with pagination support
- [ ] Render dance tree using jsTree widget
- [ ] Handle tree node expansion/collapse
- [ ] Display error messages from api_error responses
- [ ] Implement request/response validation
- [ ] Add loading indicators for API calls
- [ ] Implement offline caching (optional)

## Versioning Strategy

### API Versions

Each contract API has a `version` field in responses:
- **Current**: `"1"`
- **Backwards Compatibility**: Older clients can continue using v1 while v2 is being rolled out
- **Deprecation**: Version 1 APIs will be supported for at least 2 major releases

### Schema Versions

Each data object has a `Version` field indicating its schema version:
- **Figure**: `Version` field (currently 2)
- **Dance**: `Version` field (currently 3)
- **Dancefloor**: Implicit in contract

### Migration Path

When API changes are needed:
1. New endpoint version created (e.g., `/api/v2/figures`)
2. Existing version marked as deprecated
3. Deprecation notice in response headers
4. 6-month transition period
5. Version 1 support removed

## Error Handling

All APIs return structured errors using `api_error.schema.json`:

```json
{
  "status": "error",
  "error": "ERROR_CODE",
  "code": 400,
  "message": "Human-readable message",
  "details": {
    "additional": "context"
  }
}
```

### Common Error Codes

| Code | HTTP | Situation |
|------|------|-----------|
| `invalid_request` | 400 | Bad query params or request body |
| `not_found` | 404 | Figure or dance doesn't exist |
| `server_error` | 500 | Internal server error |
| `service_unavailable` | 503 | Server temporarily down |

## Performance Recommendations

### Caching Strategy

| Resource | Client-side | Server-side | Duration |
|----------|-------------|------------|----------|
| Figure list | Session | 1 hour | Clear on logout |
| Figure detail | Session | 1 hour | Clear on file change |
| Dance list | Session | 1 hour | Clear on logout |
| Dance tree | Session | 30 min | Clear on file change |

### Pagination Defaults

- **Default limit**: 100 items
- **Maximum limit**: 1000 items
- **Recommended UX limit**: 25-50 items per page

### Response Sizes

| Resource | Uncompressed | Gzip Compressed |
|----------|--------------|-----------------|
| Figure list (100) | 50-100 KB | 10-20 KB |
| Dance tree (large) | 50-150 KB | 10-30 KB |
| Single figure | 5-20 KB | 1-5 KB |

## Security Considerations

### Path Traversal Prevention

All file identifiers are validated to prevent `../` attacks:
- Only alphanumeric, underscore, hyphen allowed
- No path separators (/, \) allowed
- File resolution restricted to designated directories

### Rate Limiting

Recommended rate limits (optional but recommended):
- `/api/figures`: 100 requests/minute
- `/api/dances`: 100 requests/minute
- `/api/dancefloor/execute`: 30 requests/minute

### Information Disclosure

- No internal file paths in error messages
- No stack traces to clients
- Only actionable error details provided

## Testing

### Schema Validation Testing

```bash
# Validate API responses against schemas
pytest tests/test_schema_validation.py

# Validate individual schemas
ajv validate -s schema/api_figures_list.schema.json -d api_response.json
```

### Contract Compliance Testing

```bash
# Test all API endpoints
pytest tests/test_api_contracts.py

# Test error handling
pytest tests/test_error_responses.py
```

## Related Documents

- `DANCEFLOOR_RENDERER_CONTRACT.md` - Dancefloor rendering specification
- `FIGURE_LIST_API_CONTRACT.md` - Figure discovery and loading
- `DANCE_TREE_API_CONTRACT.md` - Dance choreography hierarchy
- `Documents/API_CONTRACT.md` - General API design principles

## Summary

These three contracts (Dancefloor Renderer, Figure List API, Dance Tree API) plus error handling form the complete communication specification between the Python engine and JavaScript UI. Each contract:

1. **Specifies structure** - JSON Schema for validation
2. **Defines behavior** - Request/response patterns and error handling
3. **Enables discovery** - API endpoints and query parameters
4. **Ensures consistency** - Versioning and backwards compatibility
5. **Improves reliability** - Error codes and debugging information

Together, they provide a professional, maintainable contract that separates concerns and enables independent development of backend and frontend.
