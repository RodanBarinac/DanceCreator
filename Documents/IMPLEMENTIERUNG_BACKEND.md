# Implementierung: Backend (DanceCreator)

> **Valid from version:** -  
> **End of validity:** -  
> **Status:** LEGACY - Design reference document  
> **Last updated:** 2026-08-23

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
  - Konfliktverhalten: Die Standardstrategie ist "raise" — bei paralleler Ausführung werden die Sub-Figuren separat berechnet; wenn mehrere Sub-Figuren dieselbe Tanzflächen-Position mit unterschiedlichen Tänzern belegen, wird ein CombineConflictError ausgelöst und die Gesamt-Ausführung abgebrochen. Das Backend sollte diesen Fehler in einen HTTP 409-Response mit detaillierten Konfliktangaben (Positionen und welche Sub-Figure welche Tänzer schreiben wollte) übersetzen, damit die GUI den Nutzer informieren und zur Behebung leiten kann.

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
    - Errors: 409 Conflict when parallel execution results in position write-conflicts. Response body: {"error": "message", "conflicts": {"pos": [{"floor": idx, "dancer": "name"}, ...]}}
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

---

## Detaillierte Algorithmen & Beispiele (erweiterte technische Details)

### DanceMove (Algorithmus + Verhalten)
Zweck: Erzeuge aus einem Eingabe-DanceFloor und einer Figure (Simple/Complex) einen neuen DanceFloor mit aktualisierten Positionen.

Prinzipien:
- SimpleFigure: hat StartPos -> EndPos. DanceMove:
  1. Validieren, dass die erwarteten Tänzer an StartPos vorhanden sind.
  2. Berechne Zielkoordinaten durch Addition von Anchor-Offset.
  3. Prüfe Kollisionen (Ziel besetzt) — Verhalten nach Konfiguration: raise | first-wins | merge-with-offset.
  4. Erzeuge neues DanceFloor (kopie) und setze Tänzer auf EndPos.
  5. Inkrementiere Tick/Bar entsprechend figure.Bars.

- ComplexFigure:
  - Rekursive Bearbeitung der FigureList.
  - Sequenz ("s"): wende Sub-Figuren nacheinander an (jeweils newFloor = sub.DanceMove(prevFloor)).
  - Parallel ("p"): berechne für jede Sub-Figur ein unabhängiges Ergebnisfloor aus demselben Eingangs-Floor unter Berücksichtigung von Anchors; kombiniere Ergebnisse via combineDanceFloor.

Pseudocode (vereinfacht):
```
function DanceMove(figure, oldFloor):
  if figure is SimpleFigure:
    validate start positions on oldFloor
    targetPositions = computeTargets(figure.EndPos, figure.anchor)
    newFloor = oldFloor.copy()
    for mapping dancer->target in targetPositions:
      newFloor.move(dancer, target)
    newFloor.tick += figure.Bars
    return newFloor
  else if figure is ComplexFigure:
    if figure.mode == 's':
      floor = oldFloor
      for sub in figure.subList:
         floor = DanceMove(sub, floor)
      return floor
    else if figure.mode == 'p':
      floors = []
      for sub in figure.subList:
         floors.append( DanceMove(sub, oldFloor.copy()) )
      return combineDanceFloor(floors)
```

### combineDanceFloor (Parallel-Resultate zusammenführen)
Zweck: Vereint mehrere DanceFloor-Resultate in ein einziges, konsistentes Floor.

Regeln:
- Wenn mehrere Floors dieselbe Position belegen, Konfliktauflösung per Priorität (z. B. by sub-index) oder konfigurierbare Strategie.
- Positionen, die nur in einem Floor geändert wurden, werden übernommen.
- Facing/Meta werden deterministisch zusammengeführt.

Standardverhalten: Die Referenzimplementierung wählt die Strategie "raise" für parallele Konflikte — das heißt, bei widersprüchlichen Positionsschreibzugriffen wird ein CombineConflictError ausgelöst (siehe DanceFloor.combine_dancefloors). Das ermöglicht der API, einen HTTP 409 zurückzugeben und der GUI eine klare Konfliktstruktur zur Anzeige zu liefern.

Empfehlung: Implementiere eine Config-Option zur Konflikt-Auflösung: ["raise", "first-wins", "merge-with-offset"].

### Cript-Template-Expansion
Template-Variablen: {Dancer}, {StartPos}, {EndPos}, {Face}, {Partner}

Regeln:
- Expansion erhält Kontext: DanceFloor (Mapping positions->Dancer), node.data (anchor, addons).
- Fehlende Auflösungen behalten Platzhalter und führen zu Warnungen in Logs.
- Beispiel: "Move from {StartPos} to {EndPos}" → "Move from 1m (1,1) to 3w (3,3)".

### JSON-Beispiele
SimpleFigure (v2):
```
{
  "Version":2,
  "Name":"Reel Across",
  "Desc":"...",
  "Bars":8,
  "StartPos":[[1,1],[1,3]],
  "EndPos":[[3,3],[3,1]],
  "CriptDesc":["Bar 1-8: ..."],
  "Faceing":[[1,3],[1,1]],
  "Partner":[[1,3],[1,1]],
  "Addons":{}
}
```

ComplexFigure (v3):
```
{
  "Version":3,
  "Name":"Marrie's Wedding - Full",
  "FigureList":[ [[0,0],"Reel Across"], [[0,0],["s", [ [[0,0],"Right Hand Turn"], [[0,0],"Change Across"] ]]] ]
}
```

DanceFloor JSON:
```
{
  "name":"Marrie's Wedding",
  "couples":3,
  "tick":0,
  "positions":{
    "1m": {"dancer":{"name":"A","gender":"M"},"coord":[1,1]},
    ...
  }
}
```

### Video / Render-Job API (Ergänzung)
- POST /api/dances/<name>/render-video  {"resolution":"720p","fps":25}
  - Response: 202 Accepted {"jobId":"..."}
- GET /api/render-status/<jobId>
  - Response: 200 {"state":"pending|running|done|failed","progress":0-100,"url":"..."}
- GET /api/dances/<name>/video -> redirect/download when ready

### HTTP-Statuscodes & Fehlerpayload
- 200 OK: erfolgreiche GET
- 201 Created: resource created
- 202 Accepted: job accepted (async)
- 400 Bad Request: invalid payload
- 404 Not Found: resource missing
- 409 Conflict: position collision / entity exists
- 500 Internal Server Error: unexpected
- Fehlerpayload: {"error":"message","code":"E_VALIDATION","details":{...}}

### Tests & Beispiele (Empfehlung)
- Beispiel-JSONs in Figures/ und Dances/ (Simple/Complex minimal)
- Unit-Tests:
  - test_simple_move: apply SimpleFigure on 1-couple floor and assert positions
  - test_complex_seq: sequence of two figures produces expected final positions
  - test_parallel_combine: parallel figures combine deterministisch

---

Anmerkung: Dieses Dokument umfasst die erforderlichen Signaturen, JSON-Schemata, Algorithmus-Beschreibungen und API-Erweiterungen, um eine lauffähige Implementierung zu ermöglichen.
