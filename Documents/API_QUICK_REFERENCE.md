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

Simple figure definitions may declare `StartDancers` and `StartFacing`, each parallel to `StartPos`. They control only isolated catalog preview: dancer IDs (such as `2m`, `1w`) supply preview name/gender and couple color identity; target-coordinate `StartFacing` values set incoming facing. Empty or omitted entries use automatic dancer allocation or the default same-row opposite-line facing, respectively. Inside a dance, declarations are ignored; floor dancers keep their actual identity and incoming facing. See `FIGURE_LIST_API_CONTRACT.md` and `figure.schema.json`.

`EndFacing` accepts coordinate targets or the symbolic values `=`, `I`, `O`, `U`, `D`, `OwnL`,
`OpL`, and `M` in base figures and addons. Preview `outgoingFloor` contains the target actually
resolved by execution, and `{Face}` crips use that target. `M` is explicitly unsupported at
runtime (`unsupported_facing_notation`); other notation errors depend on the final anchored
position or incoming dancer facing. See the normative
[general figure contract](Project%20Design/GENERAL_DANCE_AND_FIGURE_JSON_CONTRACT.md).

#### Figure Preview and Crips

**POST /api/figures/<identifier>/preview** accepts `anchor` and selected `addons`, and returns
`incomingFloor`, `outgoingFloor`, and a `crips` list generated from that incoming floor. The
response uses `schema/api_figure_preview_response.schema.json`; serialized floor maps use
`schema/api_floor_snapshot.schema.json`.

The same structured line format is returned in `crips` by dance detail/tree/trace responses,
where each figure node uses its trace `incomingFloor` (not the caller's floor):

```json
{
  "figureRef": "1cLT",
  "dancer": "1m",
  "barRange": [1, 4],
  "text": "turns left hand with 1w and ends facing 2w's position."
}
```

`barRange` is inclusive; it uses effective `B<n>` duration, serial groups advance the range,
and parallel children share a range. `text` is the figure/addon `getCrips` text without its legacy
bar prefix or repeated leading dancer name; position labels use possessives (for example, `2w's position`). The legacy `getCrips` method retains its prefixed text for CLI callers. See `schema/api_crip_line.schema.json`.
Trace-derived lines additionally contain `nodeId`, identifying the source figure occurrence.
Dance responses and dance-node previews use canonical dance-tree IDs; composite catalog previews
use their isolated execution-tree IDs. Simple catalog and other non-trace crips omit this field.

**POST /api/dances/<dance-id>/nodes/<node-id>/preview** previews proposed edits to a simple
figure or composite node using its execution-trace incoming floor. The request body is `{"anchor": [1, 0],
"addons": ["B4", "E1c"]}`; `node-id` is the canonical node ID in the dance tree. The success
response contains `danceId`, `nodeId`, `figureRef`, `incomingFloor`, `outgoingFloor`,
`activeDancers`, and `crips`. When identities are available, `activeDancers` identifies the
actual occupants of the proposed figure's start positions, including dancers who wait.
Trace records expose the
same field, with groups and composites reporting the union of participating descendants;
in either response, null means the participants are unavailable rather than an empty set.
It does not mutate the dance, history, revision, proposal registry, or file. The separate
`POST /api/dances/<dance-id>/proposals` route creates a pending in-memory token but does not
commit; `/apply` updates in-memory document/history state only after validation succeeds, and `/save`
persists the document. Schemas:
`schema/api_dance_node_preview_request.schema.json` and
`schema/api_dance_node_preview_response.schema.json`.

Composite-node preview keeps constituent anchors and add-ons and reports crips from the
canonical execution trace with each child's real bar range. Composite-level add-ons are
unsupported and return `composite_addons_unsupported`. Catalog Version 3 previews execute
their canonical serial/parallel tree on the minimum declared initial participant floor;
`StartDancers` and `StartFacing` declarations are honored where needed. Unsupported or
ambiguous initial formations fail explicitly instead of returning partial results. The
Version 3 catalog response can include `activeDancers` in addition to the usual floor and
crips fields.

Preview errors follow `schema/api_error.schema.json`; `error` contains `code` and `message`, and
when affected dancers are known it also contains `dancers` (names or labels such as `start position 1`).

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

The GUI tree editor is no longer read-only: the frontend `move_node.jstree` handler in `static/app.js` now saves drag-and-drop tree edits back to the server with `PUT /api/dances/<identifier>/tree`. The write endpoints below also support full dance creation, full-definition replacement, and soft delete.

### 5. Dance Write APIs

#### 5.1 Update Dance Definition

**PUT /api/dances/<identifier>**

Replace an existing dance JSON file with a complete dance definition.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---:|---|
| `Name` | string | Yes | Dance name. Must be a non-empty string up to 255 characters. |
| `Desc` | string | Yes | Human-readable dance description. Must be a non-empty string up to 5000 characters. |
| `shape` | string | No | Formation shape in `N/M` format such as `3/32`. |
| `FigureList` | array | Yes | Complete recursive dance structure in `[groupType, elements]` format. `groupType` is `s` or `p`; elements are figure calls or nested groups. |
| `Version` | integer | Yes | Must be exactly `3`. |

**Notes:**
- This is a full replacement API, not a partial patch API.
- The implementation also accepts an optional `_expected_hash` field for optimistic conflict detection. If provided and it does not match the current file hash, the endpoint returns `409 conflict`.
- Existing files are backed up automatically before overwrite as `filename.<counter-padded-to-at-least-8-digits>.bak`; only the newest 5 numbered backups are kept.

**Example:**
```bash
curl -X PUT "http://localhost:5000/api/dances/Existing%20Dance.json" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "Updated Dance",
    "Desc": "Updated description",
    "shape": "3/32",
    "FigureList": [
      "s",
      [
        [[1, 0], ["H1DR", []]],
        [[2, 0], ["1cWait", []]]
      ]
    ],
    "Version": 3
  }'
```

**Success Response (`200`):**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-09-27T19:00:00+00:00",
  "message": "Dance updated",
  "file": "Existing Dance.json",
  "dance": {
    "Name": "Updated Dance",
    "Version": 3,
    "shape": "3/32"
  }
}
```

**Possible Errors:**

| Status | `error` | When it happens |
|---:|---|---|
| `400` | `validation_error` | Identifier is invalid, request body is not a JSON object, malformed JSON is sent, or required/body fields fail validation (`Name`, `Desc`, `FigureList`, `Version`, optional `shape`). |
| `404` | `not_found` | The target dance file does not exist. |
| `409` | `conflict` | `_expected_hash` was supplied and the file changed since the client last read it. |
| `500` | `write_failed` | The validated update could not be written safely to disk. |

#### 5.2 Create Dance

**POST /api/dances**

Create a brand-new dance JSON file from a complete dance definition.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---:|---|
| `Name` | string | Yes | Dance name. Also used to derive the output filename. |
| `Desc` | string | Yes | Human-readable dance description. |
| `shape` | string | No | Formation shape in `N/M` format such as `3/32`. |
| `FigureList` | array | Yes | Complete recursive dance structure in `[groupType, elements]` format. |
| `Version` | integer | Yes | Must be exactly `3`. |

**Notes:**
- The server sanitizes `Name` into a safe filename, appends `.json` if needed, and writes the file into `data\Dances\`.
- New files are written without creating a `.bak` backup first.

**Example:**
```bash
curl -X POST "http://localhost:5000/api/dances" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "Brand New Dance",
    "Desc": "Brand New Dance description",
    "shape": "3/32",
    "FigureList": [
      "s",
      [
        [[1, 0], ["H1DR", []]],
        [[2, 0], ["1cWait", []]]
      ]
    ],
    "Version": 3
  }'
```

**Success Response (`201`):**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-09-27T19:00:00+00:00",
  "message": "Dance created",
  "file": "Brand New Dance.json",
  "dance": {
    "Name": "Brand New Dance",
    "Version": 3,
    "shape": "3/32"
  }
}
```

**Possible Errors:**

| Status | `error` | When it happens |
|---:|---|---|
| `400` | `validation_error` | Request body is not a JSON object, malformed JSON is sent, or required/body fields fail validation. |
| `409` | `conflict` | A dance with the same sanitized filename already exists. |
| `500` | `write_failed` | The validated dance could not be written safely to disk. |

#### 5.3 Update Dance Tree

**PUT /api/dances/<identifier>/tree**

Replace only the `FigureList` of an existing dance using a jsTree-compatible payload from the GUI editor.

**Request Body:**

| Field | Type | Required | Description |
|---|---|---:|---|
| `tree` | object | Yes | Root jsTree node. |
| `tree.id` | string | Yes | Unique node identifier. |
| `tree.text` | string | Yes | Display text for the node. |
| `tree.type` | string | Yes | Node type: `root`, `group`, or `figure`. |
| `tree.data.figureName` | string | Figure nodes | Figure name for `type=figure`. |
| `tree.data.groupType` | string | Group nodes | Group type for `type=group`: `s` or `p`. |
| `tree.data.anchor` | array[number, number] | No | Figure anchor position. Defaults to `[1, 0]` during conversion if missing or invalid. |
| `tree.data.addons` | array[string] | No | Figure addon names. |
| `tree.children` | array | No | Child jsTree nodes. Required by the converter for root/group processing. |

**Notes:**
- The request is validated structurally first, then converted into internal `Dance.FigureList` format by `TreeConverter`.
- Only `FigureList` is replaced; existing dance metadata such as `Name`, `Desc`, `shape`, and `Version` is preserved.
- Successful writes create a numbered `.bak` backup before overwriting the dance file.
- Empty group children arrays are allowed and convert to empty internal groups such as `["p", []]`.

**Example:**
```bash
curl -X PUT "http://localhost:5000/api/dances/Existing%20Dance.json/tree" \
  -H "Content-Type: application/json" \
  -d '{
    "tree": {
      "id": "root",
      "text": "Existing Dance",
      "type": "root",
      "data": {},
      "children": [
        {
          "id": "group-1",
          "text": "Series",
          "type": "group",
          "data": { "groupType": "s" },
          "children": [
            {
              "id": "figure-1",
              "text": "1cRT",
              "type": "figure",
              "data": {
                "figureName": "1cRT",
                "anchor": [1, 0],
                "addons": []
              },
              "children": []
            }
          ]
        }
      ]
    }
  }'
```

**Success Response (`200`):**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-09-27T19:00:00+00:00",
  "message": "Dance tree updated",
  "file": "Existing Dance.json"
}
```

**Possible Errors:**

| Status | `error` | When it happens |
|---:|---|---|
| `400` | `validation_error` | Identifier is invalid, request body is not a JSON object, malformed JSON is sent, `tree` is missing/not an object, or required node fields such as `tree.type` are invalid. |
| `400` | `conversion_error` | The jsTree payload is structurally valid JSON but cannot be converted into `FigureList` (for example, a figure node is missing `data.figureName`). Response includes `node_id` when available. |
| `404` | `not_found` | The target dance file does not exist. |
| `500` | `load_error` | The existing dance file could not be loaded before applying the tree update. |
| `500` | `write_failed` | The converted dance could not be written safely to disk. |

#### 5.4 Delete Dance

**DELETE /api/dances/<identifier>**

Soft-delete a dance by moving its JSON file into `data\Dances\.deleted\`.

**Request Body:** None.

**Notes:**
- The server creates a numbered `.bak` backup before moving the file.
- If `data\Dances\.deleted\filename.json` already exists, the moved file gets a timestamp suffix (for example `Delete Me-20260927190000000000.json`) to avoid collisions.
- The original `file` value in the response still refers to the source dance path relative to `data\Dances\`.

**Example:**
```bash
curl -X DELETE "http://localhost:5000/api/dances/Delete%20Me.json"
```

**Success Response (`200`):**
```json
{
  "status": "ok",
  "version": "1",
  "timestamp": "2026-09-27T19:00:00+00:00",
  "message": "Dance deleted",
  "file": "Delete Me.json"
}
```

**Possible Errors:**

| Status | `error` | When it happens |
|---:|---|---|
| `400` | `validation_error` | Identifier is empty or uses an invalid format such as path traversal. |
| `404` | `not_found` | The target dance file does not exist. |
| `500` | `delete_failed` | Backup creation or the move into `.deleted` failed. |

### 6. Dancefloor APIs

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
  "anchor": [1, 0],
  "addons": []
}
```

**Response:**
```json
{
  "status": "ok",
  "floor": {...},
  "crips": [
    {"figureRef": "1cLT", "dancer": "1m", "barRange": [1, 4], "text": "..."}
  ]
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


## Centered grid and addon timing

Dance-floor rows remain 1-based couple positions. Columns are centered (`-1` men's line, `0` centre, `+1` ladies' line); default facing points across to the opposite line. A missing tree anchor defaults to `[1, 0]`. Engine-reserved addons named `B<n>` set any simple figure to a positive-integer bar count, with no per-figure definition, and may shorten or lengthen it. `B<n>` changes bars only; its resolved value feeds execution ranges and parallel duration validation. Multiple duration addons or addons that change the same field for the same dancer are errors. For `1cLT`, `B4` changes bars only and `E1c` changes end positions, end facing, and ending text only. Two half reels with `B3` each form a six-bar reel; no separate 6- or 8-bar reel figures exist.
