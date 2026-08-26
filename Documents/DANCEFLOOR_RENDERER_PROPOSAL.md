# DanceFloor Renderer Proposal

## Recommendation
Use an **SVG-based renderer** in the GUI's middle panel for the DanceFloor.

## Why SVG
- Fits the floor's discrete grid model (`row`, `col`) well.
- Easy to style dancers, positions, and occupancy states.
- Scales cleanly at any window size.
- Supports hover, selection, and click interaction without much complexity.

## Suggested Visual Model
- **Grid cells** for each couple row and the 3 positions (`m`, `center`, `w`).
- **Position labels** like `1m`, `1w`, `2m`.
- **Dancer tokens** as circles or rounded boxes with initials or names.
- **Facing indicator** as a small arrow or line.
- **State colors** for empty, occupied, selected, and conflict positions.

## Data Mapping
Use the floor JSON returned by:
- `POST /api/dancefloor/init`
- `POST /api/dancefloor/execute`

Map:
- `name` -> header label
- `couples` -> row count
- `positions` -> rendered cells
- `dancer.name` / `dancer.gender` -> token content and style
- `coord` -> row/column placement
- `facing` -> direction indicator

## GUI Placement
Render the SVG inside the **Arbeitsbereich** panel and keep the figure list and dance tree as supporting controls.

## Optional Next Step
Add a small legend so users can read dancer shape, facing, and occupied-state colors quickly.
