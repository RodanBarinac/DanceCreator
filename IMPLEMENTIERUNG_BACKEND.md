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
  - GET /api/dances -> list dances
  - GET /api/dances/<name> -> dance JSON + tree
  - GET /api/dances/<name>/crips -> full cripts for dance
  - GET /api/dances/<name>/visualization -> SVG for entire dancefloor
  - POST /api/dancefloor/init -> {"couples": int} -> returns initial floor JSON
  - POST /api/dancefloor/execute -> {"figure": name_or_object, "anchor": [r,c], "addons": {}} -> returns new floor JSON + cripts
  - GET /api/dancefloor/state -> current floor JSON
  - GET /api/search?q=... -> filtered results

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
