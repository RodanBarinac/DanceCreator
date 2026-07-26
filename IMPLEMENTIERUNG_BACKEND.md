# Implementierung: Backend (DanceCreator)

Zweck:
Dieses Dokument beschreibt die minimale und vollständige Backend-API, Daten- und Klassenstruktur, die benötigt wird, damit DanceCreator.py ausgeführt werden kann (Laden eines Tanzes, Simulation auf DanceFloor, Ausgabe von Cripts).

1) Kernmodule / Dateien
- Dance.py
  - Funktionen:
    - getDance(name: str) -> DanceObject
    - getFigure(name: str, anchor: List[int]=[0,0], addons: dict=None) -> FigureObject
    - showCrips(figure_or_dance, floor: DanceFloor) -> None  # druckt Cripts
- SimpleFigure.py
  - Klasse SimpleFigure(Figure):
    - DanceMove(oldDF: DanceFloor) -> DanceFloor
    - getCrips(oldDF: DanceFloor) -> List[str]
    - loadFromJSON(path)-> SimpleFigure
- ComplexFigure.py
  - Klasse ComplexFigure(Figure):
    - DanceMove(oldDF: DanceFloor) -> DanceFloor  # führt Sub-Figuren (s/p) aus
    - getCrips(oldDF: DanceFloor) -> List[str]
    - rekursive Hilfsfunktionen: subDanceMove(), subgetCrips()
- Figures.py
  - Basisklasse Figure (ABC): Signaturen wie oben, gemeinsame Attribute (Name, Version, Bars, Desc, Addons)
- DanceFloor.py
  - Klasse DanceFloor(name: str, couples: int)
    - Repräsentation: 2D-Gitter (rows = couples, cols = positions per couple)
    - state: mapping position_name -> Dancer
    - methods: initPositions(), applyMove(), getState(), __str__() (menschenlesbare Ausgabe)
    - combineDanceFloor(df_list: List[DanceFloor]) -> DanceFloor (für Parallel-Ausführung)
- Dancer.py
  - Klasse Dancer(name: str, gender: str)

2) Datenträger / JSON-Formate (unbedingt exakt implementieren)
- SimpleFigure (Version 2)
  - Felder: Version, Name, Desc, Bars, StartPos (list of [row,col]), EndPos, CriptDesc (list str mit Template-Variablen), Faceing, Partner, Addons
  - Beispiel im Konzept (kopieren)
- ComplexFigure (Version 3)
  - Felder: Version, Name, Desc, FigureList: [ [Anchor, Figure] ] wobei Figure String oder ["s", [..]] / ["p", [..]]
  - Anchor: [row_offset, col_offset]

3) Methodenkontrakte / Rückgabewerte
- Dance.getDance(name) -> returns object representing root ComplexFigure (oder wrapper Dance)
- Figure.DanceMove(oldDF) -> returns new DanceFloor reflecting positions after move
- Figure.getCrips(oldDF) -> returns list of formatted strings (kript lines) with variables expanded where possible
- Dance.showCrips(Marrie, Floor) -> should call getCrips and print each line

4) Sequenzielle vs. parallele Ausführung
- Sequenziell: Apply DanceMove eines Sub-Figure nacheinander, das resultierende DanceFloor ist Input für nächste
- Parallel: Erst compute für jede Sub-Figure ein isoliertes DanceFloor (auf Basis des gleichen Input mit ggf. Anchor-Offsets), dann combine via combineDanceFloor

5) Minimal implementierungs-API (für Flask/GUI-Anbindung)
- Intern (module functions) as above
- REST-Endpoints (Flask) - Pflichten:
  - GET /api/figures -> list of figures with metadata
  - GET /api/figures/<name> -> JSON of figure (Simple/Complex)
  - GET /api/figures/<name>/crips -> Ungefüllte Cripts (template)
  - GET /api/figures/<name>/thumbnail -> SVG string
  - GET /api/dances -> list of dances with metadata (name, version, bars, thumbnail)
  - GET /api/dances/<name> -> dance JSON + jsTree-compatible tree structure (see Tree Format below)
  - GET /api/dances/<name>/tree -> jsTree-compatible JSON only (optional convenience)
  - GET /api/dances/<name>/crips -> full cripts for dance
  - GET /api/dances/<name>/visualization -> SVG for entire dancefloor or per-bar positions
  - POST /api/dancefloor/init -> {"couples": int} -> returns initial floor JSON
  - POST /api/dancefloor/execute -> {"figure": name_or_object, "anchor": [r,c], "addons": {}} -> returns new floor JSON + cripts
  - GET /api/dancefloor/state -> current floor JSON
  - GET /api/search?q=... -> filtered results

Tree Format (jsTree-compatible)
- The backend must return a tree structure compatible with jsTree so the frontend can render and manipulate nodes. Each node is an object with at least the following fields:
  - id: string (unique within tree; use deterministic IDs when possible, e.g., "root", "fig-1", or path-like "0.1.2")
  - text: string (label displayed in the tree, e.g., "Reel Across [Bar 1-8]")
  - children: array of child nodes (can be empty)
  - type: string (optional, e.g., "dance", "figure", "seq", "par")
  - data: object (arbitrary payload used by frontend/backend): recommended keys:
    - figureName: string (for leaf nodes representing a figure)
    - version: int
    - bars: [start,end] or int
    - anchor: [row_offset,col_offset] (if present)
    - addons: object (if the node encodes parameter overrides)
    - original: the original FigureList entry (Anchor + Figure) to allow exact reconstruction

- Representation rules for ComplexFigure FigureList:
  - If a FigureList entry is a string (figure name), create a leaf node with type "figure" and data.figureName set.
  - If an entry is a sequenced or parallel group (e.g., ["s", [...]] or ["p", [...]]), create a parent node with type "seq" or "par" and create child nodes recursively for its subentries.
  - Anchors must be attached to the node's data (data.anchor) and preserved so the GUI can show offsets or edit them.
  - Maintain the order of entries in the FigureList by emitting children in the same order.

Example node (leaf):
{
  "id": "fig-3",
  "text": "Reel Across [Bar 1-8]",
  "type": "figure",
  "data": {
    "figureName": "Reel Across",
    "version": 2,
    "bars": [1,8],
    "anchor": [0,0],
    "addons": {},
    "original": [[0,0], "Reel Across"]
  },
  "children": []
}

Example node (sequence):
{
  "id": "seq-1",
  "text": "Sequence",
  "type": "seq",
  "data": {"original": [[0,0], ["s", [...]]]},
  "children": [ ... ]
}

Frontend responsibilities
- Use the provided node.id as unique identifier for operations (select, edit, move).
- When a node is moved in the tree, emit a backend call to persist ordering/structure (PUT /api/dances/<name>/tree) with the updated tree or minimal delta.
- When a figure leaf is double-clicked or clicked, load its details via GET /api/figures/<figureName> and render in the Canvas.

Backend responsibilities
- Build the jsTree structure deterministically from the dance JSON (FigureList) and return it as part of GET /api/dances/<name>.
- Ensure all nodes have unique IDs.
- Preserve anchors, addons and original FigureList entries in node.data so reconstruction and editing is lossless.
- Provide PUT /api/dances/<name>/tree to accept updates from the frontend and persist changes to the dance JSON (update FigureList accordingly).

6) JSON-Schemata (Kurz)
- DanceFloor JSON:
  - {"name": str, "couples": int, "tick": int, "positions": {"1m": {"name":"1m","dancer": {"name":"X","gender":"M"}, "coord":[r,c]}}}
- Figure JSON: wie oben (Simple/Complex)

7) Logging, Fehlerbehandlung, Validierung
- Auf JSON-Version prüfen, bei Mismatch Exception werfen
- Validierung von Positionsformaten (tuple/list len 2, ints)
- Aussagenreiche Exceptions (Name + Ursache)

8) Unit-Tests (empfohlen)
- Tests für: Laden SimpleFigure JSON, DanceMove auf kleinem Floor (1-2 Couples), ComplexFigure s/p-Ausführung, getCrips Template-Expansion

9) Schnittstellenbeispiele (Code-snippet)

```python
from Dance import getDance, showCrips
import DanceFloor as DF
Floor = DF.DanceFloor("Marrie's Wedding", 3)
M = getDance("Marries Wedding_all")
showCrips(M, Floor)
Floor = M.DanceMove(Floor)
print(Floor)
```

10) Dateien & Struktur (Erwartet, kopiert aus Konzept)
- DanceCreator.py (Haupteinstiegspunkt)
- Dance.py, DanceFloor.py, Figures.py, SimpleFigure.py, ComplexFigure.py, Dancer.py
- directories: Figures/*.json, Dances/*.json, templates/, static/

---

Anmerkung: Dieses Dokument reicht aus, um die minimale Funktionalität, die in DanceCreator.py verwendet wird, zuverlässig zu implementieren. Es enthält präzise Signaturen, JSON-Formate und REST-Endpoints.
