# Dance Engine Flow: Concepts and Data Flow

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-09-27

## Purpose

This document is the conclusive description of how a dance moves through the engine: what a
`Dance`, `Figure`, `ComplexFigure`, `DanceFloor`, and `Dancer` are, how figures combine into
dances, how Cripts (the human-readable instructions) are generated, and where a GUI can hook
into the process to render figures, dances, and the dancefloor.

It reflects the **active implementation** in `src/engine/`, not the legacy design documents in
this folder (`IMPLEMENTIERUNG_BACKEND.md`, `IMPLEMENTIERUNG_GUI.md`, `KONZEPT_CLEAN.md`), which
are kept for historical reference only.

---

## 1. Core Concepts

### 1.1 Dancer

`src/engine/models/Dancer.py`

The smallest unit. A `Dancer` has just two attributes:

```python
class Dancer:
    def __init__(self, name, gender):
        self.name = name      # e.g. "1m", "2w"
        self.gender = gender  # "male" or "female"
```

Dancers carry no position of their own — position is tracked externally by the `DanceFloor`.

### 1.2 DanceFloor

`src/engine/models/DanceFloor.py`

The `DanceFloor` is the state container: it maps **positions** to **(Dancer, facing)** pairs at
one point in time (one bar count).

```python
class DanceFloor:
    def __init__(self, name, NofCouple=0):
        self.name = name
        self.AktBar = 1          # current bar number
        self.maxRow = NofCouple  # number of couples, grows DanceFloorNames as needed
```

Key internals:

- `DanceFloorMap`: `{(row, col): [Dancer, facingPos]}` — the actual state.
- `DanceFloorNames`: `{(row, col): "1m" | "between 1c" | "1w" | ...}` — human-readable names for
  positions, auto-generated for `1..NofCouple` couples in a 3-column layout
  (col -1 = man, col 0 = between/aisle, col +1 = woman).
- `AktBar`: the bar count this floor state represents ("end of bar N").
- `addDancer(dancer, pos, facing)`: places a dancer; raises if the position is already taken.
- `DancerbyPos(pos)` / `PosNamebyPos(pos)`: look up a dancer / the display name of a position.
- `copy()`: deep-enough copy used before applying a move, so the original floor is never mutated.
- `__str__()`: renders an ASCII grid (Men | Between | Lady columns) — useful for debugging/logs.
- `combineDanceFloor(oldDFs=[])` (module-level function): merges several `DanceFloor` snapshots
  from **parallel** branches into a single one (see §3.2). All input floors must share the same
  `AktBar`, otherwise an exception is raised.

`setupDancefloor(NofCouples)` auto-populates a floor with `NofCouple` couples in the standard
starting formation (men in column -1 facing column +1, women in column +1 facing column -1).

### 1.3 Figure (abstract base)

`src/engine/models/Figures.py`

`Figure` is an abstract base class (ABC) that both `SimpleFigure` and `ComplexFigure` implement.
It defines the shared contract:

```python
class Figure(ABC):
    Desc, Bars, StartPos, EndPos, StartFacing, StartDancers, EndFacing, Anchor   # properties

    @abstractmethod
    def DanceMove(self, DanceFloor): ...   # returns a NEW DanceFloor after the figure runs

    @abstractmethod
    def getCrips(self, DanceFloor): ...    # returns the Cript lines describing the figure

    @abstractmethod
    def loadFigure(self, Filename): ...    # populates the figure from a JSON file
```

`Anchor` is a `[row, col]` offset added to every position the figure references, allowing the
same figure definition to be reused at different places on the floor (`posWithAnchor`).

A `FigureAddon` (also in `Figures.py`) is a small modifier object loaded from a figure's own
`"Addons"` dictionary. It can modify start/end positions, end facing, partner references, and
instruction text for a specific variant. Separately, engine-reserved addon names of the form
`B<n>` set the duration and are not defined in the figure's `Addons` dictionary.

### 1.4 SimpleFigure

`src/engine/figures/SimpleFigure.py` — a `Figure` loaded from a **version 2** JSON file.

A SimpleFigure is the atomic, non-decomposable dance move: it lists explicit `StartPos` and
`EndPos` for each dancer involved, and a Cript template per dancer.

Example (`data/Figures/1cRT.json` — "1st couple right-hand turn"):

```json
{
  "Name": "1cRT",
  "Desc": "Two bar right hand turn for one couple",
  "Version": 2,
  "Bars": 2,
  "StartPos": [[0, -1], [0, 1]],
  "EndPos":   [[0, -1], [0, 1]],
  "Partner":  [[0, 1], [0, -1]],
  "CriptDesc": [
    "{Dancer} turns right hand with {Partner} and ends in own place.",
    "{Dancer} turns right hand with {Partner} and ends in own place."
  ],
  "Addons": {}
}
```

Each parallel array index (`StartPos[i]`, `EndPos[i]`, `Partner[i]`, `CriptDesc[i]`) describes
**one dancer's** move within the figure. A figure can also define `"Addons"` — named variants
that patch `StartPos`/`EndPos`/`EndFacing`/`Cript` for special endings, e.g. `H1DR`'s `"E2c"`
addon changes where dancers finish facing.

`loadFigure(Filename, Addons)`:
1. Simple-figure definitions are loaded only from `data/Figures/`; dance definitions and
   fragments are loaded only from `data/Dances/`, including `data/Dances/subDances/`. Root-level
   `Figures/` and `Dances/` folders and fallback loading are not used.
2. Validates `Version == 2`.
3. Loads `StartPos`, `EndPos`, `CriptDesc`, `StartFacing`, `StartDancers`, `EndFacing`, and
   `Partner`. Optional `StartDancers` and `StartFacing` lists must parallel `StartPos`; dancer
   identifiers are validated for format and uniqueness after empty entries receive the automatic
   preview assignment. Empty facing entries use the same-row opposite-line default. `Facing` alone
   is not a figure key or property.
4. If `Addons` names were passed in, wraps each one in a `FigureAddon` and appends it to
   `self._Addons` — these are applied transparently whenever `StartPos`/`EndPos`/`EndFacing`/
   `Partner`/Cripts are read.

`StartDancers` and `StartFacing` configure an isolated catalog preview only. Preview allocation
uses alternating man/woman identities and couple `index // 2 + 1` when no dancer is declared;
declared IDs control preview name and gender, while renderer color follows the couple number. A
`StartFacing` coordinate is a target position (not a vector) and missing/empty entries face the
same row on the opposite side of the centre line. When a figure runs within a dance, `StartDancers`
does not rename dancers and `StartFacing` does not override floor facing; execution requires an
actual dancer at every `StartPos`.

`DanceMove(oldDF)`:
1. Creates a fresh `DanceFloor`.
2. For each dancer index `i`, looks up the dancer currently at `posWithAnchor(StartPos[i])` on
   `oldDF`, and places them at `posWithAnchor(EndPos[i])` on the new floor, with the resolved
   facing.
3. Sets the new floor's `AktBar = oldDF.AktBar + self.Bars`.
4. Returns the new floor — **the input floor is never mutated**.

`getCrips(myDF)`: expands the (possibly addon-modified) `CriptDesc` templates against the
**input** floor `myDF` (positions/names as they were *before* the move), substituting
`{Dancer}`, `{StartPos}`, `{EndPos}`, `{Face}`, `{Partner}` with resolved dancer/position names.
Each resulting line is prefixed with the bar range, e.g.
`"1 - 2: 1m turns right hand with 1w and ends in own place."`.

### 1.5 ComplexFigure

`src/engine/figures/ComplexFigure.py` — a `Figure` loaded from a **version 3** JSON file. A
ComplexFigure is a **composition** of other figures (Simple or Complex), combined either
**sequentially** or **in parallel**.

Example (`data/Dances/Marries Wedding_all.json`, a dance is itself a top-level ComplexFigure):

```json
{
  "Name": "Marries Wedding",
  "Version": 3,
  "FigureList": ["s", [
      ["p", [
          ["s", [[[1,0], ["1cRT",   []]], [[1,0], ["1cCast1p", []]]]],
          ["s", [[[2,0], ["1cWait", []]], [[2,0], ["1cSU",     []]]]],
          ["s", [[[3,0], ["1cWait", []]], [[3,0], ["1cWait",   []]]]]
      ]],
      [[1,0], ["H1DR", ["E2c"]]],
      [[1,0], ["6Hrb", []]]
  ]]
}
```

**FigureList grammar** (recursive):

- A leaf entry is `[anchor, [figureName, addons]]` (or the shorthand `[anchor, figureName]`
  when there are no addons). `anchor` is `[row, col]`, resolved relative to the parent figure's
  own anchor.
- A group entry is `["s", [entry, entry, ...]]` or `["p", [entry, entry, ...]]`:
  - `"s"` = **series** — sub-figures run **sequentially**, each one's output floor feeding the
    next one's input floor.
  - `"p"` = **parallel** — sub-figures each run independently against **the same input floor**,
    and their resulting floors are merged afterwards.
- Groups nest arbitrarily deep (a `"p"` block can contain `"s"` blocks and vice versa, as shown
  above: three couples doing different things in parallel, each couple's own moves in series).

`loadFigure()`:
1. Validates `Version == 3`.
2. Reads `FigureList` from JSON.
3. Recursively calls `loadSubFigure()`, which turns every leaf entry into a real `Figure` object
   via `Dance.getFigure(name, anchor, addons)` (see §2), while preserving the `"s"`/`"p"` group
   structure as nested Python lists of Figure objects. The result is stored in `_FigureObjs`.

`Bars` (property): recursively sums bars for a series, and asserts all parallel branches take
the **same** number of bars (raises otherwise) — a dance's timing must line up.

### 1.6 Dance

There is no dedicated `Dance` class — **a Dance is just a `ComplexFigure`** loaded from a
top-level dance JSON file (e.g. `data/Dances/Marries Wedding_all.json`). Conceptually:

> Dance = ComplexFigure (root of a FigureList tree) + dance-level metadata (`Name`, `Desc`,
> `shape`, `Version`, possibly `Couples`/`Formation`/`EstimatedBars` computed by the API layer).

`src/engine/models/Dance.py` provides the module-level helper functions used to obtain one:

```python
def getDance(Filename):
    """Loads a top-level ComplexFigure from data/Dances/<Filename>.json."""

def getFigure(Filename, Anchor=[0,0], Addons=[]):
    """Loads either a SimpleFigure or ComplexFigure, auto-detected by
       whether the JSON has a 'FigureList' key."""

def showCrips(myFig, myDF):
    """Recursively prints the (possibly nested) Cript lines returned by getCrips()."""
```

`getFigure` is what makes the system uniform: **anything** referenced from a `FigureList` —
whether it is itself Simple or Complex — is resolved through the same call, so `ComplexFigure`
never needs to know which kind of sub-figure it is dealing with.

---

## 2. How Figures Combine into a Dance

1. `Dance.getDance("Marries Wedding_all")` creates a root `ComplexFigure` and calls
   `loadFigure()`.
2. `loadFigure()` reads the dance's `FigureList` and recursively resolves every entry via
   `Dance.getFigure(...)`:
   - Leaf entries (figure names) become `SimpleFigure` or `ComplexFigure` instances, each
     carrying its own resolved `Anchor` (parent anchor + local anchor) and `Addons`.
   - `"s"`/`"p"` entries stay as `["s", [FigureObj, FigureObj, ...]]` / `["p", [...]]` — a tree
     of Figure objects mirroring the JSON structure.
3. The result is one root `Figure` object (`_FigureObjs`) whose `DanceMove()` / `getCrips()` walk
   this tree.

This gives a uniform recursive structure: **Dance → group(s) of Figures → group(s) of Figures →
… → SimpleFigure leaves**, at arbitrary nesting depth.

---

## 3. Execution: DanceMove

Calling `myDance.DanceMove(floor)` (where `floor` is a `DanceFloor` already populated with
dancers, e.g. via `DanceFloor(name, couples)`) walks the Figure tree and produces the **final**
`DanceFloor` after the whole dance/figure has executed.

### 3.1 Sequential (`"s"`) execution

`ComplexFigure.subDanceMove` for an `"s"` group:

```python
for FigObj in FigObjs[1]:
    newDF = self.subDanceMove(FigObj, newDF)   # chained: output feeds next input
return newDF
```

Each sub-figure's resulting floor becomes the next sub-figure's starting floor. `AktBar`
increases monotonically along the chain.

### 3.2 Parallel (`"p"`) execution

```python
newDFs = []
for FigObj in FigObjs[1]:
    newDFs.append(self.subDanceMove(FigObj, newDF))   # same input floor for every branch
return DF.combineDanceFloor(newDFs)
```

Every branch starts from the **same** input floor (so different couples/subsets can move
simultaneously), and the branch results are merged by `combineDanceFloor`:

- Asserts every branch ended on the same `AktBar` (they must take equally many bars — this is
  also checked by the `Bars` property beforehand).
- Copies every `(position -> dancer, facing)` entry from every branch into one new floor.
- **Conflict behavior**: if two branches write to the same position, `addDancer` raises an
  exception (the "raise" strategy referenced by the legacy backend doc — this is what the code
  actually does today; there is no configurable conflict-resolution strategy implemented).

### 3.3 Leaf execution

A `SimpleFigure.DanceMove` (see §1.4) is the base case that actually moves dancers between
positions; `ComplexFigure` only ever orchestrates calls down to these leaves.

---

## 4. Cript Generation

"Cripts" are the human-readable, bar-numbered instruction lines for a dance ("crib" in Scottish
Country Dance terminology). They are generated in lock-step with (but separately from) the
`DanceMove` walk, using `getCrips(floor)`:

### 4.1 SimpleFigure Cripts

`SimpleFigure.getCrips(myDF)`:
1. Takes the **CriptDesc** template list (patched by any active Addons).
2. For each dancer index, resolves placeholders against the **input** floor `myDF`:
   - `{Dancer}` → dancer name at `StartPos[i]`
   - `{StartPos}` / `{EndPos}` → position display name (e.g. `"1m's position"`)
   - `{Face}` → position name of `EndFacing[i]` (raises if figure requires facing but none is set)
   - `{Partner}` → dancer name at `Partner[i]` (raises if figure requires a partner but none is
     set)
3. Prefixes each resolved line with its bar range: `f"{AktBar} - {AktBar+Bars-1}: {line}"`.
4. Returns a flat `list[str]`, one entry per dancer (empty template lines are skipped).

### 4.2 ComplexFigure Cripts

`ComplexFigure.subgetCrips`, mirroring `subDanceMove`:

- **Series (`"s"`)**: Cripts are collected in order, and — critically — a **temporary copy** of
  the floor (`tmpDF = newDF.copy()`) is advanced with `subDanceMove()` after each sub-figure's
  Cripts are captured, so each sub-figure's Cripts are generated against **its own correct
  starting floor state**, not the dance's original floor.
- **Parallel (`"p"`)**: Cripts for every branch are collected against the **same** shared
  input floor (matching how `DanceMove` also uses the same input floor for every branch).

The result is a **nested list structure** mirroring the FigureList's `"s"`/`"p"` tree (lists of
lists of strings), *not* a flat list. `Dance.printCrip` / `Dance.showCrips` recursively flatten
and print this structure line by line — a GUI wanting structured (not just flattened) Cripts
should walk this nested structure itself rather than relying on `showCrips`, which only prints.

### 4.3 Important ordering rule

Because Cripts are computed from the **pre-move** floor, `getCrips(floor)` must always be
called with the *same* floor state that `DanceMove(floor)` will consume — computing Cripts from
a floor that has already advanced past the figure will produce wrong dancer/position names. See
`GUI_DanceCreator_App.py`'s `/api/dancefloor/execute` handler for the correct pattern:

```python
new_floor = figure.DanceMove(floor)   # advance
crips = figure.getCrips(floor)        # describe, using the ORIGINAL (pre-move) floor
```

---

## 5. End-to-End Flow Summary

```
JSON files (data/Figures/*.json, data/Dances/*.json)
        │  loadFigure()
        ▼
Figure objects (SimpleFigure leaves + ComplexFigure "s"/"p" trees)
        │  Dance.getDance() / Dance.getFigure()
        ▼
Root Figure (= "the Dance")  ──────────────┐
        │                                  │
        │ DanceMove(inputFloor)            │ getCrips(inputFloor)
        ▼                                  ▼
new DanceFloor (final dancer positions)   nested Cript lines (bar-numbered instructions)
```

A `DanceFloor` populated with `Dancer`s is the required starting state for both operations; both
operations are pure (they do not mutate their input floor) and can be called independently or
together.

---

## 6. GUI Hooks

This chapter lists the concrete places a GUI (or any external client) can attach to observe or
drive each concept, based on the Flask routes actually implemented in `GUI_DanceCreator_App.py`.

### 6.1 Showing a Figure (catalog / detail view)

| Need | Hook |
|---|---|
| List all figures (with filter/sort/paginate) | `GET /api/figures?search=&version=&formation=&minBars=&maxBars=&sort=&order=&limit=&offset=` |
| Full JSON of one figure (Simple or Complex) | `GET /api/figures/<name>` |
| Figure's un-filled Cript template | Not a dedicated endpoint today — derive from the figure JSON's `CriptDesc`, or execute it via `/api/dancefloor/execute` (§6.4) to get resolved Cripts |

A figure JSON returned here already contains everything needed to render it standalone: `Name`,
`Desc`, `Bars`, `StartPos`/`EndPos`/`EndFacing`/`Partner` arrays (Simple), or `FigureList` (Complex).

### 6.2 Showing a Dance (tree / choreography view)

| Need | Hook |
|---|---|
| List all dances (with filter/sort/paginate) | `GET /api/dances?minCouples=&maxCouples=&search=&sort=&order=&limit=&offset=` |
| Full dance JSON | `GET /api/dances/<identifier>` |
| jsTree-compatible structure of the dance's FigureList (for a tree widget) | `GET /api/dances/<identifier>/tree` |
| Create a dance | `POST /api/dances` |
| Replace a dance's contents | `PUT /api/dances/<identifier>` |
| Replace only the tree/FigureList (e.g. after drag-and-drop editing in jsTree) | `PUT /api/dances/<identifier>/tree` |
| Delete a dance | `DELETE /api/dances/<identifier>` |

The tree endpoint turns each `"s"`/`"p"` group into a `type: "group"` node (with
`data.groupType`) and each leaf into a `type: "figure"` node (with `data.figureName`,
`data.anchor`, `data.addons`, `data.original` for lossless round-tripping) — see
`Documents/DANCE_TREE_API_CONTRACT.md` for the exact node schema. This is the hook a GUI should
use to render/edit the choreography structure without re-implementing the FigureList grammar
client-side.

### 6.3 Showing a DanceFloor (positions of dancers)

| Need | Hook |
|---|---|
| Create/reset a floor with N couples | `POST /api/dancefloor/init` `{"couples": 3, "name": "..."}` → returns the serialized floor |
| Advance the floor by executing one figure | `POST /api/dancefloor/execute` `{"figure": "H1DR", "couples": 3, "anchor": [0,0], "addons": ["E2c"]}` → returns `{"floor": {...}, "crips": [...]}` |

The serialized floor shape follows the contract in
`Documents/DANCEFLOOR_RENDERER_CONTRACT.md`: `{"name", "couples", "tick", "positions": {"1m":
{"dancer": {"name","gender"}, "coord": [row,col], "facing": [row,col]}, ...}}`. A GUI should
render dancers at `coord` and orient them toward `facing` (a target position, **not** a
direction vector — compute `direction = [facing[1]-coord[1], facing[0]-coord[0]]`).

**Note**: `/api/dancefloor/execute` currently only resolves a single named figure (Simple or
Complex) at a fixed couple count, starting from a freshly-initialized floor each call — it does
not accept an arbitrary pre-existing floor state as input. A GUI that wants to step through an
entire dance bar-by-bar on a *persisted* floor across multiple calls will need either an
enhancement to this endpoint, or to run the whole dance's `DanceMove`/`getCrips` server-side and
have the GUI scrub through the resulting bar-indexed floor states rather than calling
`/execute` once per figure.

### 6.4 Showing Cripts

| Need | Hook |
|---|---|
| Resolved Cripts for a figure/dance execution | Returned inline as `crips` from `POST /api/dancefloor/execute` |
| Cripts for an entire dance | Not yet exposed as its own endpoint; would require walking the dance's `Figure` tree server-side (`ComplexFigure.getCrips`) and returning the nested structure or a flattened text/markdown block (this was the intent behind the legacy `GET /api/dances/<name>/crips` endpoint described in `IMPLEMENTIERUNG_GUI.md`/`IMPLEMENTIERUNG_BACKEND.md`, but it is **not implemented** in the current `GUI_DanceCreator_App.py`) |

Because Cripts are nested (§4.2), a future dance-level Cript endpoint should preserve the
`"s"`/`"p"` nesting in its JSON response (mirroring the tree endpoint's node structure) so the
GUI can align Cript lines with the corresponding tree nodes, rather than flattening server-side.

### 6.5 Validation hooks

Both request bodies and responses are validated against JSON Schemas
(`src/engine/validators/ApiRequestValidator.py`, `ApiResponseValidator.py`,
`DancefloorContractValidator.py`, schemas under `schema/`). A GUI can fetch these schemas
directly for client-side validation via `GET /schema/<path:filename>`.

---

## 7. Where to Look in Code

| Concept | File |
|---|---|
| Dancer | `src/engine/models/Dancer.py` |
| DanceFloor, combineDanceFloor | `src/engine/models/DanceFloor.py` |
| Figure (ABC), FigureAddon | `src/engine/models/Figures.py` |
| SimpleFigure | `src/engine/figures/SimpleFigure.py` |
| ComplexFigure | `src/engine/figures/ComplexFigure.py` |
| getDance / getFigure / showCrips | `src/engine/models/Dance.py` |
| jsTree conversion (dance ⇄ FigureList) | `src/engine/converters/TreeConverter.py` |
| Flask API / GUI hooks | `GUI_DanceCreator_App.py` |
| Related contracts | `Documents/DANCE_TREE_API_CONTRACT.md`, `Documents/DANCEFLOOR_RENDERER_CONTRACT.md` |

---

## 8. Terminology Cheat Sheet

- **Dance** = a top-level `ComplexFigure` (a dance JSON with `"FigureList"`) plus metadata.
- **Figure** = an atomic (`SimpleFigure`) or composite (`ComplexFigure`) dance move; both
  implement `DanceMove()` and `getCrips()`.
- **ComplexFigure** = a Figure defined purely by composing other Figures via a `FigureList`
  tree of `"s"` (series) / `"p"` (parallel) groups.
- **Anchor** = a `[row, col]` offset that repositions a figure's built-in coordinates onto the
  actual floor; anchors compose additively down the FigureList tree.
- **Addon** = a named variant of a figure (defined in the figure's own `"Addons"` dict) that
  patches start/end positions, facing, or Cript text for that instance only.
- **DanceFloor** = an immutable-per-step snapshot: which Dancer occupies which position, which
  way they face, and which bar this snapshot represents (`AktBar`).
- **Cript** = a resolved, bar-numbered natural-language instruction line ("crib") describing
  what one dancer does during one figure.


## Centered grid and duration addons

The floor coordinate is `[row, column]`: rows are 1-based couple positions; columns are
centered with the men's line at `-1`, centre at `0`, and ladies' line at `+1`. Default facing
remains opposite-side: a dancer on `-1` faces `+1`, and a dancer on `+1` faces `-1`. Figure
offsets and facing targets use that mapping. Figure offsets decrease by one column and top-level
dance anchors decrease by one during the migration, preserving absolute positions after floor
columns shift by two.

The engine recognizes addon names `B<n>` (capital B plus a positive integer) on any simple
figure; they are not declared in figure files and set the bar count to `n`, shortening or
lengthening the figure without changing its movement path. A figure may have at most one `B<n>`;
multiple duration addons, or addons that set the same field for the same dancer, are errors rather
than later-wins overrides. Addons may replace instruction text. For `1cLT`, `B4` changes only the
bars to four; `E1c` changes end positions, end facing, and ending text, but not bars. These addons
are independent and reusable. Two half reels in series, each with `B3`, take six bars; there are
no separate 6- or 8-bar reel figures.
