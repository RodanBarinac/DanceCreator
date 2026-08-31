# DanceCreator API Quick Reference

## Overview

The DanceCreator API provides programmatic access to dance figures, dances, and dancefloor execution. All APIs return JSON and support filtering, pagination, and validation against JSON schemas.

## Running the API Server

```bash
.\.venv\Scripts\python.exe GUI_DanceCreator_App.py
```

Server runs at `http://localhost:5000`

## Testing the APIs

```bash
# Run all API tests
.\.venv\Scripts\python.exe -m pytest tests/test_api_*.py -v

# Run specific test file
.\.venv\Scripts\python.exe -m pytest tests/test_api_figures_list.py -v
```

## API Endpoints

### 1. Figure List API

**GET /api/figures**

List available figures with filtering and pagination.

**Query Parameters:**
- `version=N` - Filter by schema version
- `formation=TYPE` - Filter by formation (turn, reel, hey, circle, etc.)
- `minBars=N`, `maxBars=N` - Filter by bar count
- `search=TERM` - Search by name or description
- `limit=N` - Items per page (default 100, max 1000)
- `offset=N` - Pagination offset
- `sort=FIELD` - Sort by name, bars, or version
- `order=ASC|DESC` - Sort order

**Example:**
```bash
curl "http://localhost:5000/api/figures?formation=reel&minBars=4&sort=name"
```

**Response:**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-08-31T08:00:00Z",
  "count": 3,
  "total": 15,
  "offset": 0,
  "limit": 100,
  "filters_applied": {"formation": "reel", "minBars": 4},
  "figures": [...]
}
```

### 2. Figure Detail API

**GET /api/figures/<identifier>**

Get complete figure definition.

**Example:**
```bash
curl "http://localhost:5000/api/figures/H1DR"
```

### 3. Dance List API

**GET /api/dances**

List available dances with filtering and metadata.

**Query Parameters:**
- `version=N` - Filter by schema version
- `minCouples=N`, `maxCouples=N` - Filter by couple count
- `search=TERM` - Search by name or description
- `limit=N`, `offset=N` - Pagination
- `sort=FIELD` - Sort by name, couples, version, or bars
- `order=ASC|DESC` - Sort order

**Example:**
```bash
curl "http://localhost:5000/api/dances?minCouples=3&sort=name"
```

**Response:**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-08-31T08:00:00Z",
  "count": 2,
  "total": 12,
  "dances": [
    {
      "file": "Marries Wedding_all.json",
      "Name": "Marries Wedding",
      "shape": "3/32",
      "Version": 3,
      "EstimatedBars": 32,
      "Couples": 3
    }
  ]
}
```

### 4. Dance Tree API

**GET /api/dances/<identifier>/tree**

Get dance choreography as hierarchical jsTree-compatible structure.

**Example:**
```bash
curl "http://localhost:5000/api/dances/Marries%20Wedding_all.json/tree"
```

**Response:**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-08-31T08:00:00Z",
  "format": "jstree",
  "dance": {
    "file": "Marries Wedding_all.json",
    "Name": "Marries Wedding",
    "shape": "3/32",
    "Version": 3
  },
  "tree": {
    "id": "root",
    "text": "Marries Wedding",
    "children": [...]
  }
}
```

### 5. Dancefloor APIs

**POST /api/dancefloor/init**

Initialize dancefloor.

**Request:**
```json
{
  "couples": 3,
  "name": "Test Floor"
}
```

**POST /api/dancefloor/execute**

Execute a figure on the dancefloor.

**Request:**
```json
{
  "figure": "H1DR",
  "couples": 3,
  "anchor": [1, 1],
  "addons": []
}
```

**Response:**
```json
{
  "status": "ok",
  "floor": {...},
  "crips": [...]
}
```

## Schema Validation

All responses are validated against JSON schemas in `/schema`:
- `api_figures_list.schema.json`
- `api_dances_list.schema.json`
- `api_dance_tree_response.schema.json`
- `dancefloor_contract.schema.json`

## Error Responses

All errors return JSON with:
```json
{
  "status": "error",
  "error": "error_code",
  "message": "Human-readable message"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Validation error or bad request
- `404` - Resource not found
- `500` - Internal server error

## Contract Documentation

For detailed API specifications, see:
- `Documents/FIGURE_LIST_API_CONTRACT.md`
- `Documents/DANCE_TREE_API_CONTRACT.md`
- `Documents/DANCEFLOOR_CONTRACT_README.md`

## Implementation Notes

- Request validation: `src/engine/validators/ApiRequestValidator.py`
- Response validation: `src/engine/validators/ApiResponseValidator.py`
- Tests: `tests/test_api_*.py`
- Recursion protection: Tree building limited to 50 levels depth
- Backward compatibility: Breaking changes update example data instead of adding legacy shims
