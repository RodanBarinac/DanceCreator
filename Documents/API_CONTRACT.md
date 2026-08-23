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
- Schema: `Documents/Schema/figure.schema.json`
- Scope: `/Figures/*.json`
- Purpose: describe a single figure or complex figure definition

### Dance files
- Schema: `Documents/Schema/dance.schema.json`
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
- Schema: `Documents/Schema/jstree_node.schema.json`
- Scope: `/tree` and tree-like backend responses
- Purpose: feed the GUI tree widget

### Dance floor state
- Schema: `Documents/Schema/dancefloor.schema.json`
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
- `POST /api/dancefloor/execute` - serialized floor plus crips

## Normalized contract

The list endpoints should return summary objects, not raw filenames or raw figure payloads.

### `GET /figures`
Use `Documents/Schema/api_figures_response.schema.json`.

Each item should include:
- `file`
- `key`
- `Name`
- `Desc` when available
- `Bars` when available
- `Formation` when available
- `Version` when available

### `GET /dances`
Use `Documents/Schema/api_dances_response.schema.json`.

Each item should include:
- `file`
- `Name`
- `Desc` when available
- `shape`
- `Version` when available

### `GET /tree?file=<name>`
Use `Documents/Schema/api_tree_response.schema.json`.

### `GET /get_nodes/<node_Name>`
Use `Documents/Schema/jstree_node.schema.json` for the intended GUI shape.

## Notes

- Dance `shape` is required for new files.
- Legacy dance files may exist without `shape`, but should be migrated.
- Files under `Dances/subDances/` are legacy fragments; they are loadable by the resolver but are not yet treated as full dances in validation.
- Dance trees are recursive and should keep expanding groups until only simple figures remain.
- The GUI may consume these routes later via `/api/*`, but that is not the current truth.
- Contract work should follow the backend routes and data files first.
