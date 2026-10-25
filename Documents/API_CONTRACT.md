# API Contract

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23  
> **Status:** DRAFT

## Source of truth

The backend Python files and JSON data files are the source of truth.
The JavaScript frontend is a consumer and may be incomplete or broken.
Do not infer contract requirements from `static/app.js` unless they are also supported by the backend or data files.

## File Schemas

### Figure files
- Schema: `schema/figure.schema.json`
- Scope: `/Figures/*.json`
- Purpose: describe a single figure or complex figure definition

### Dance files
- Schema: `schema/dance.schema.json`
- Scope: `/Dances/*.json`
- Purpose: describe a dance built from figures\n- The schema supports both inline composition and modular bar references for the same dance
- Required fields:
  - `Name`
  - `Desc`
  - `shape`
  - `FigureList`
  - `Version`
- `shape` format: `couples_dancing/couples_in_set`, for example `2/4` or `3/3`

### jsTree nodes
- Schema: `schema/jstree_node.schema.json`
- Scope: `/tree` and tree-like backend responses
- Purpose: feed the GUI tree widget

### Dance floor state
- Schema: `schema/dancefloor.schema.json`
- Scope: backend floor state and execution responses
- Purpose: describe dancer positions on the floor

## Current backend routes

These are the routes currently present in `GUI_DanceCreator_App.py`:

- `GET /` - HTML page
- `GET /figures` - normalized figure summaries
- `GET /dances` - normalized dance summaries
- `GET /tree?file=<name>` - tree view for one figure or dance file
- `GET /get_nodes/<node_Name>` - tree node lookup for loaded figures

## Versioned API routes

The `/api/` namespace mirrors the current backend contract and is the preferred entry point for GUI consumption:

- `GET /api/figures`
- `GET /api/figures/<name>` - full figure JSON
- `GET /api/dances`
- `GET /api/dances/<name>` - dance JSON plus nested tree
- `GET /api/dances/<name>/tree` - nested tree only
- `GET /api/tree?file=<name>`
- `GET /api/get_nodes/<node_Name>`
- `POST /api/dancefloor/init`
- `POST /api/dancefloor/execute` - serialized floor plus structured crips
- `POST /api/figures/<name>/preview` - isolated catalog preview including structured crips
- `POST /api/dances/<dance-id>/nodes/<node-id>/preview` - no-side-effect preview of proposed edits using the node's trace incoming floor
- `GET /api/dances/<name>` (also `/tree` and `/trace`) - dance trace plus structured crips

## Structured crips (Q9)

The engine exposes one non-printing crips data path for a figure or dance figure node and its
incoming floor. Its line objects have this exact shape (schema:
`schema/api_crip_line.schema.json`; list schema: `schema/api_crips.schema.json`):

```json
{
  "figureRef": "1cLT",
  "dancer": "1m",
  "barRange": [1, 4],
  "text": "turns left hand with 1w and ends facing 2w's position."
}
```

`text` is rendered from the existing `getCrips` text without the legacy `start - end:` prefix or a repeated leading dancer name; the `dancer` field is the authoritative line label. Position references use possessives, for example `2w's position`. The legacy `getCrips` method keeps its dancer-prefixed text for existing CLI callers.
`barRange` is inclusive and reflects the effective `B<n>` duration. Serial children advance the
range; parallel children share the group's incoming range. Addon text such as `E1c` is included.
Floor snapshots are maps from the serialized position key to an entry with `position`, `dancer` (`name` and `gender`), and `facing`; see `schema/api_floor_snapshot.schema.json`. For catalog figures, `POST /api/figures/<identifier>/preview` returns `crips` for the generated `incomingFloor` and selected `addons`. For dance nodes, the dance detail/tree/trace response
returns a flattened `crips` list built from each figure occurrence's trace `incomingFloor` and
`barRange`; the caller's floor is not used. Dance response lines do not include a node ID: the
figure reference, dancer, range and text identify each instruction line. The preview response
shape is documented by `schema/api_figure_preview_response.schema.json`.


### No-side-effect dance-node preview (Q10)

`POST /api/dances/<dance-id>/nodes/<node-id>/preview` previews proposed anchor/add-on values for a simple figure occurrence inside a dance. `<node-id>` is the canonical node ID exposed in the dance response's `tree`; it is not the figure reference. Request body (schema: `schema/api_dance_node_preview_request.schema.json`):

```json
{"anchor": [1, 0], "addons": ["B4", "E1c"]}
```

The `anchor` is the selected node's own anchor (not including a containing composite's anchor); `addons` is the complete proposed selection. On success (schema: `schema/api_dance_node_preview_response.schema.json`), the response is:

```json
{
  "danceId": "Marries Wedding_all",
  "nodeId": "node-figure-1",
  "figureRef": "1cLT",
  "incomingFloor": {
    "1m": {"position": [1, -1], "dancer": {"name": "1m", "gender": "male"}, "facing": [1, 1]},
    "1w": {"position": [1, 1], "dancer": {"name": "1w", "gender": "female"}, "facing": [1, -1]}
  },
  "outgoingFloor": {
    "1.5:0.5": {"position": [1.5, 0.5], "dancer": {"name": "1m", "gender": "male"}, "facing": [2, 1]},
    "0.5:-0.5": {"position": [0.5, -0.5], "dancer": {"name": "1w", "gender": "female"}, "facing": [0, -1]}
  },
  "crips": [{"figureRef": "1cLT", "dancer": "1m", "barRange": [1, 4], "text": "turns left hand with 1w and ends facing 2w's position."}]
}
```

`incomingFloor` comes from that node's execution trace, not from a newly generated catalog floor. The proposed occurrence is executed in isolation against a private floor snapshot. The route does not alter the dance document, execution history, revision, proposal registry, or dance file. Composite nodes and non-figure nodes are not previewable. Catalog preview remains `POST /api/figures/<figure-ref>/preview` and uses the generated incoming floor.

The existing `POST /api/dances/<dance-id>/proposals` route applies edit commands to an immutable document copy and does not commit the dance document, execution history, revision, or file. It does create a server-memory pending-proposal token. `POST /api/dances/<dance-id>/apply` validates and commits that token to in-memory document/history state (including its revision and trace); it does not write the dance file. A rejected apply does not commit and returns affected dancers when the validation issue identifies them. `POST /api/dances/<dance-id>/save` persists a validated document. The inspector preview route deliberately does not create a proposal token.

Preview and addon validation failures use the shared error schema (`schema/api_error.schema.json`). When known, `error.dancers` lists affected dancer names or start-position labels, for example:

```json
{"error": {"code": "addon_conflict", "message": "Conflicting duration addons 'B2' and 'B3' both modify Bars.", "dancers": ["start position 1", "start position 2"]}}
```

## Normalized contract

The list endpoints should return summary objects, not raw filenames or raw figure payloads.

### `GET /figures`
Use `schema/api_figures_response.schema.json`.

Each item should include:
- `file`
- `key`
- `Name`
- `Desc` when available
- `Bars` when available
- `Formation` when available
- `Version` when available

### `GET /dances`
Use `schema/api_dances_response.schema.json`.

Each item should include:
- `file`
- `Name`
- `Desc` when available
- `shape`
- `Version` when available

### `GET /tree?file=<name>`
Use `schema/api_tree_response.schema.json`.

### `GET /get_nodes/<node_Name>`
Use `schema/jstree_node.schema.json` for the intended GUI shape.

## Notes

- Dance `shape` is required for new files.
- Legacy dance files may exist without `shape`, but should be migrated.
- Files under `Dances/subDances/` are legacy fragments; they are loadable by the resolver but are not yet treated as full dances in validation.
- Dance trees are recursive and should keep expanding groups until only simple figures remain.
- Modular figure references should expand to their own trees when the figure file contains a `FigureList`.
- `FigureList` belongs to the tree response, not the metadata summary.
- The GUI may consume these routes later via `/api/*`, but that is not the current truth.
- Contract work should follow the backend routes and data files first.
