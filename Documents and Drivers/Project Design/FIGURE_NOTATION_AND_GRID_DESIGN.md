# Figure Notation and Dance Grid Design

> **Valid for version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-10-25 (open questions resolved)  
> **Status:** Decision record. C18, C19, Q8, and the decided Q1c are implemented and covered by tests; this status does not claim that every earlier work package in the document is complete.

## 1. Purpose

Record the decisions made about how figures are noted, so an implementation agent can apply
them. This is a design document only. It records the centered dance-floor grid, figure/addon changes, and facing/identity rules for isolated catalog previews and dance execution. Decisions C18, C19, Q8, and Q1c below clarify preview defaults, per-dancer declarations, and the boundary between isolated previews and in-dance behavior.

Instructions for an agent that turns a user's description into an addon are **not** part of this
document and are still to be written.

## 2. Confirmed requirements

| # | Requirement |
|---|---|
| C1 | All dancers face the opposite side unless a facing is declared. This rule stays. |
| C2 | Some figures need facing declared at the **start** of the figure, not only at the end. |
| C3 | `1cLT` has a data bug: its second dancer starts at `[0,1]` and must start at the lady's position (see C8 for the new coordinate). The same bug is in the `Partner` and `EndPos` entries. |
| C4 | `1cLT1c` is not a separate figure. It is `1cLT` plus a four-bar duration addon plus the ending addon `E1c`. |
| C5 | `E1c` changes only where the turn ends: end positions and end facing. It applies at any duration. |
| C6 | A duration addon changes only the bar count. The movement path stays the same; only its timing changes. |
| C7 | The duration addon is reusable and is combined with ending addons. It is not a one-off named variant. |
| C8 | The whole floor is re-centred on the centre line: men at column -1, centre at column 0, ladies at column +1. Anchors move with it. |
| C9 | Rows stay as they are: the row is the couple position (first couple position = row 1, second = row 2, and so on), counted from 1. |
| C10 | Start facing (Q1): declared start facing is a setup used when a figure is previewed on its own. Inside a dance, the starting facing is always determined by the previous figure, so a declared start facing is ignored there. |
| C11 | The duration addon is parameterised (Q2): `B<n>` (for example `B3`, `B4`, `B8`) sets the bar count to `n` on any figure, without being defined in the figure's file. It can shorten as well as lengthen a figure. |
| C12 | Conflicting addons (Q3): if two addons on one figure change the same value for the same dancer, the combination is rejected as an error. Later-wins is not allowed. |
| C13 | The misspelled key `Faceing` is renamed to `EndFacing` everywhere (Q4, C17), without a legacy shim. |
| C17 | Facing keys (Q1b): `StartFacing` declares facing at the start and `EndFacing` at the end, parallel to `StartPos` and `EndPos`. Both are per-dancer lists in the same format that `Faceing` has today (a position `[row, col]` to face, or an empty entry for the default). The key `Facing` alone is not used. |
| C14 | There are no separate 6-bar and 8-bar reel figures (Q5). A 6-bar reel is two half reels in series, each with `B3`. An 8-bar reel is two half reels at their default 4 bars. |
| C18 | Default facing (refines C1, 2026-10-25): without a declared facing, a dancer faces straight across the floor along the column axis. The facing is a target position (the same format as `EndFacing`): the dancer faces the position in the same row on the opposite line. The dancer on `[1,-1]` faces `[1,1]`, the dancer on `[2,-1]` faces `[2,1]`, and the dancer on `[1,1]` faces `[1,-1]`. The direction is therefore `[0,1]` for the men's line and `[0,-1]` for the ladies' line, but it is stored and rendered as the target position of the dancer's own row. This replaces the partner-index and "opposite side" fallbacks (for example in the preview in `src/api/canonical.py`). |
| C19 | Dancer roles (2026-10-25): inside a dance, the role, couple and facing of each dancer come from the previous figure and the floor. Only the catalog preview of a single figure has to guess. The default for the preview is the current preview behaviour: dancers are taken in the order of `StartPos`, even index is a man, odd index is a woman, and the couple is `index // 2 + 1` (1m, 1w, 2m, 2w, ...). A figure can overrule this by declaring its dancers: a list of dancer identifiers parallel to `StartPos`, in the same style as the names on the floor (couple number plus `m` or `w`). For H1DR the list is `["2m", "1w", "1m", "3w"]`. The preview uses the declared identifiers for name, gender and colour (the colour follows the couple number). The key is named `StartDancers`, parallel to `StartPos` and `StartFacing`. |
| C15 | Only `data/Figures/` and `data/Dances/` are used (Q7). The root `Figures/` and `Dances/` folders are removed, along with the loader's legacy fallback to them. |
| C16 | The `Dances/subDances/` fragments are kept and migrated like the other dances (Q6). They move to `data/Dances/subDances/` only. |

## 3. Grid change (C8, C9)

### 3.1 Current and new mapping

| | Current | New |
|---|---|---|
| Men's line | column 1 | column -1 |
| Centre line (between) | column 2 | column 0 |
| Ladies' line | column 3 | column 1 |
| Rows | 1, 2, 3, ... | unchanged |

Absolute floor position = dance anchor + any nested anchors + figure offset. Absolute columns
move by -2. This is split as follows:

- **Figure offsets** (`StartPos`, `EndPos`, `StartFacing`, `EndFacing`, `Partner`, and the same fields inside addons): the column value decreases by 1. Fractional values keep their fraction (`[0.5, 1.5]` becomes `[0.5, 0.5]`). Empty entries stay empty. Row values do not change.
- **Dance anchors** at the top level, such as `[1,1]`, `[2,1]`, `[3,1]`: the column value decreases by 1 (`[1,0]`, `[2,0]`, `[3,0]`).
- **Fragment anchors** in `data/Dances/subDances/` (for example `[0,0]`, `[2,2]`) sit below a top-level anchor. The per-dancer result must still equal the old result shifted by -2, so the implementer decides per anchor whether it changes, and shows the result with the invariant in section 3.3.

The invariant that decides correctness is in section 3.3, not the rules above.

### 3.2 Known places affected (not exhaustive)

This list comes from a read-only search and must be completed by the implementer.

- **Floor model:** `src/engine/models/DanceFloor.py` builds position names for columns 1, 2, 3, places dancers in columns 1 and 3 with facing targets in the opposite column, and prints the ASCII floor from columns 1 to 3. All of this changes, including how negative columns are named and printed.
- **Defaults and conversion:** `src/engine/converters/TreeConverter.py` (`DEFAULT_ANCHOR = [1, 1]`), `src/api/canonical.py` (default anchor `[1, 1]` and the "opposite column" calculation using +2/-2), `src/engine/validators/DancefloorContractValidator.py` (column 1 means man, column 3 means woman, facing column +2/-2), `src/engine/domain/*`, `src/engine/execution/executor.py`, `GUI_DanceCreator_App.py`.
- **Frontend:** `static/app.js` (`previewAnchor: [1, 1]` and anchor column handling), `static/Dancefloor_Render.js`, `static/DancefloorContractValidator.js`.
- **Data:** all 15 files in `data/Figures/` and `data/Dances/`, including `subDances/`. The root `Figures/` and `Dances/` copies are deleted (C15), and the legacy fallback paths in `SimpleFigure.loadFigure` and any other loaders are removed. Tests and code that read the root folders are updated to `data/`.
- **Schemas and contracts:** the dance-floor schemas and contract documents state coordinates in the range 1-16 or with minimum values (`schema/dancefloor_contract.schema.json`, `schema/dancefloor.schema.json`, `schema/api_*.schema.json`, `DANCEFLOOR_CONTRACT.md`, `Documents/DANCEFLOOR_*`). Columns can now be negative, so every minimum or range that applies to a column must be checked. Rows keep their minimum of 1.
- **Tests:** about 25 files under `tests/` use the old coordinates, `Faceing`, `1cLT`/`1cLT1c`, or "Marries Wedding" fixtures.

### 3.3 Acceptance invariant

For every dance in `data/Dances/` (capture the before-state before anything is changed) and for 1, 2 and 3 couples where the dance supports it:
executing the dance after the migration gives the same floors, bar counts and instruction text
as before, except that every column is mapped 1 to -1, 2 to 0, 3 to 1 and the instruction
text may name the new positions. The implementer should capture the before-state first and then
compare against it.

## 4. Figure notation changes

### 4.1 `1cLT` fix (C3)

Under the new grid, `1cLT` has its two dancers at `[0,-1]` and `[0,1]` for `StartPos`, `EndPos`
and `Partner`. The old value `[0,1]` for the second dancer is wrong. After the fix
the figure matches the start positions of `1cRT` and the other one-couple figures. `1cLT` also
has an `Anchor` field that the other one-couple figures do not have. The implementer must decide
whether it is needed (the loader does not read it from the file) and mention it in the report.

### 4.2 `1cLT1c` becomes a combination (C4 to C7)

`1cLT1c` stops being a figure file. Wherever it is used (`Marries Wedding_all` and the
`Bar 1-8` fragment in `data/Dances/`) it is replaced by `1cLT` with two addons:

| Addon | Changes | Does not change |
|---|---|---|
| `B4` (parameterised duration addon, C11) | Bar count only: 2 becomes 4 | positions, facing, instruction text |
| `E1c` | End positions and end facing, and the instruction text for the ending | bar count |

Derived values for `E1c` on `1cLT`, obtained by applying the column rule to the old `1cLT1c`.
The implementer must check them against the old figure:

- `EndPos`: `[[0.5, 0.5], [-0.5, -0.5]]`
- `EndFacing`: `[[1, 1], [-1, -1]]`
- Instruction text: the base text says "ends in own place" and the old `1cLT1c` text says "ends facing {Face}", so `E1c` replaces that phrase.

The two addons change different things, so the order in which they are listed does not matter.

### 4.3 Duration addon (C6, C7)

- Addons today cannot change `Bars`. The engine must recognise addon names of the form `B<n>` (a capital `B` followed by a positive whole number) itself, without a definition in the figure file, and treat them as "set the bar count to `n`". An addon defined in a figure file cannot use a name of this form.
- `B<n>` works on any simple figure and can shorten or lengthen it (a half reel with `B3` takes 3 bars instead of 4).
- If more than one `B<n>` addon is given for one figure, that is a conflict (C12).
- Everything that reads the duration of a figure must see the addon value: the bar counter of the floor after the move, the bar range in instruction lines (for example `1 - 4:`), and the duration checks for parallel groups.

### 4.4 Facing (C1, C2)

- **Default facing (C1, C18):** absent an explicit facing target, the dancer faces the target position in the same row on the opposite side of the centre line: `[row, column]` maps to `[row, -column]` (for example `[1,-1]` to `[1,1]`, `[2,-1]` to `[2,1]`, and `[1,1]` to `[1,-1]`). Facing remains a target coordinate, not a direction vector. This replaces partner-index and old-grid `+2/-2` fallbacks; do not rely on former columns 1 and 3.
- **Start facing (C2, C10, Q1c):** `StartFacing` is a per-dancer list parallel to `StartPos`, in the same target-coordinate format as `EndFacing`. It affects only isolated catalog preview. Missing or empty entries use C18's default. During dance execution it is ignored; dancers retain the actual floor-facing state and the figure's `EndFacing` remains responsible for explicit outgoing facing. `StartFacing` is now read and applied in preview.
- **Preview dancer identity (C19, Q8):** optional `StartDancers` is a list parallel to `StartPos`, using IDs such as `2m` and `1w`. Empty/missing entries use the prior automatic assignment (even index man, odd index woman, couple `index // 2 + 1`). Validate length, identifier format, and uniqueness after filling automatic entries. Catalog preview uses each identifier for name/gender; the renderer continues deriving couple color from the numeric couple identity. In-dance naming ignores `StartDancers`; execution uses the dancer already on the floor and rejects a missing dancer at any start coordinate.

### 4.5 Conflicting addons (C12)

Addons are applied together. If two addons on the same figure change the same value for the same dancer (for example both set `EndPos` for dancer 2), loading the figure fails with a clear error naming both addons and the value. Addons that change different values, or different dancers, combine without error. The error replaces the current silent behaviour in which the later addon overwrites the earlier one.

### 4.6 Defects and renames in this work

- The addon method that applies replacement instruction text (`FigureAddon.getCrips` in `src/engine/models/Figures.py`) discards the result of `str.replace`, so an addon cannot change instruction text today. `E1c` needs this, so it must be fixed as part of this work.
- `Faceing` is renamed to `EndFacing` in figure and addon data, engine code (including the `Facing` properties and addon methods that read it), schemas, API documents and tests (C13, C17). No old spelling is accepted afterwards.

## 5. Resolved questions and remaining follow-ups

Resolved on 2026-10-25: Q1 (C10), Q1b (C17), Q1c (C18/Q1c preview behavior), Q2 (C11), Q3 (C12), Q4 (C13), Q5 (C14), Q6 (C16), Q7 (C15), and Q8 (C19).

| # | Question | Notes |
|---|---|---|
| Q8 | Confirm the key name and validation rules for declared preview dancers (C19). | Decided 2026-10-25: optional `StartDancers`, parallel to `StartPos`; empty/missing entries use automatic allocation, then the full list must contain valid unique IDs. A declared/automatic collision is an error. Inside a dance, declarations do not rename dancers; execution verifies an actual dancer exists at every start position. H1DR is the only catalog pilot in this work. Decided 2026-10-25: figures needing `StartDancers`/`StartFacing` are H1DR (done), H2DR, HLReelAU, HLReelAD, HRReelAU and HRReelAD. The four three-dancer reels use `StartDancers` = `["2m","1w","2w"]` (corrected 2026-10-25). H2DR uses `StartDancers` = `["3m","1w","1m","2w"]`; the first two dancers face each other and the last two face each other, so `StartFacing` = `[[1.5,-0.5],[2,-1],[0,1],[0.5,0.5]]` (derived from the user's description, same pattern as H1DR). `AU`/`AD` means the direction in which the middle dancer starts (up or down the floor); base positions are identical, so the direction is not yet recorded in the notation or in the instruction text. The `Name` values of these four files now match their filenames. Catalog implementation is complete for H2DR and all four half-reel `StartFacing` declarations. Decided: HLReelAU `StartFacing` = `[[0,1],[0,-1],[0,-1]]` (target positions: the dancer at `[0,-1]` faces `[0,1]`, the middle dancer at `[0,0]` and the dancer at `[0,1]` face `[0,-1]`); HRReelAU `StartFacing` = `[[0,1],[0,1],[0,-1]]`; HRReelAD `StartFacing` = `[[0,1],[0,-1],[0,-1]]`; HLReelAD `StartFacing` = `[[0,1],[0,1],[0,-1]]`. Resolved 2026-10-25: the U/D direction has no separate field; it is implied by `StartFacing` and by the instruction text. |
| Q10 | Inspector editing: one Apply button, implicit cancel. | Decided 2026-10-25: the four buttons "Propose anchor", "Propose add-ons", "Apply" and "Cancel" are replaced by a single "Apply" button in the upper right area of the inspector panel. When a figure inside a dance is selected, the inspector shows a preview with the incoming floor of the dance; changes to the anchor and the add-ons are rendered immediately in the outgoing floor (and the instructions). "Apply" transfers the changes to the dance. Selecting a different figure discards pending changes without a prompt (implicit cancel). For a catalog figure the anchor and add-ons only change the preview. Decided: for a catalog figure "Apply" stays visible but is disabled. Decided: an invalid combination (for example conflicting add-ons, or a failed preview) disables "Apply" and shows the error in the outgoing floor: the diagram shows the last valid result dimmed, a red banner names the cause (for example which add-ons conflict on which value for which dancer), the dancers involved get a red outline, and their lines in the instructions get the same marker. Needs from the API: a structured error that names the dancers (positions or names) involved. This work is figure-catalog and inspector only; the dance tree error is for another session. |
| Q9 | Show the crips in the inspector with the current dancefloor. | Decided 2026-10-25: the inspector shows the crips of the selected figure as a text list, one line per dancer, together with the current dancefloor. For a figure inside a dance the floor is the dance's incoming floor; for a catalog figure it is the generated incoming floor. Selecting a line highlights that dancer on the floor. Decided: one crips function and one API serve both cases. The caller passes the figure (or dance node) and the incoming floor, which is either the dance's incoming floor or the generated catalog floor; the engine does not care where the floor came from. The result is structured lines (dancer, bar range, text, figure). The engine keeps its existing crip lines: the text of each line is still produced by `getCrips`, and the structured line wraps that text and adds dancer, bar range and figure. Only the printing (`printCrip`, `showCrips`) is replaced by this data path. Selecting a dancer on the floor highlights its text line, and selecting a line highlights the dancer. Today nothing calls `renderCrips` in `static/app.js`, the inspector has no crips element, and no API route returns crips. Open: the exact layout, how addons and the `B<n>` duration change the shown lines, and the response format. | This is the next step after the figure data. |
| Q1c | How does a preview use `StartFacing`? | Decided and implemented 2026-10-25: optional `StartFacing`, parallel to `StartPos`, uses the `EndFacing` target-coordinate format. Missing/empty entries use C18 default facing. It affects isolated catalog preview only and is ignored inside dances. H1DR pilot: `StartDancers` = `["2m","1w","1m","3w"]`; `StartFacing` = `[[0.5,-0.5],[0,-1],[2,1],[1.5,0.5]]`. API/GUI editing remains open. |

## 6. Suggested work packages

Work packages 2 and 3 depend on 1. They are listed for the supervisor and are not instructions
for any other agent.

0. **Clean-up (C13, C15).** Remove the root `Figures/` and `Dances/` folders and the loader's legacy fallback. Rename `Faceing` to `EndFacing`. Do this first, so later packages work on one set of data.
1. **Grid migration (C8, C9).** Capture the before-state of all dances. Update the floor model, defaults, validators, API and frontend code, schemas, data files, tests and contract documents. Prove the invariant in section 3.3.
2. **`1cLT` fix and addons (C3 to C7, C11, C12).** Fix `1cLT`. Add `E1c` to it. Add the engine-recognised `B<n>` addon and conflict detection for addons, and fix the instruction replacement. Remove `1cLT1c` and update the dances that use it. Prove that `1cLT` with `B4` and `E1c` gives the same floors and instruction text as the old `1cLT1c` (apart from the grid mapping). Test that two `B3` half reels in series give 6 bars.
3. **Documentation.** Update the existing documents that describe coordinates, figures and addons (`Documents/DANCE_ENGINE_FLOW.md`, `Documents/FIGURE_LIST_API_CONTRACT.md`, `Documents/API_QUICK_REFERENCE.md`, `DANCEFLOOR_CONTRACT.md`, `Documents/DANCEFLOOR_*`). Record both breaking changes in `CHANGELOG.md`.

Project rules apply: no legacy shims for the old coordinates, so the example data, tests and
documents are updated instead; tests are written first; the full suite runs with
`.\.venv\Scripts\python.exe -m pytest tests/ -v` before anything is committed.

## 7. Alternatives considered

- **Keep `1cLT1c` as a separate figure:** no engine change, but the move is duplicated and every addon of the turn has to be duplicated too. Rejected, because C4 states they are the same figure.
- **Make duration part of `E1c`:** one addon less, but then a two-bar turn cannot end the same way as a four-bar turn. Rejected, because C5 and C6 say these are independent.
- **Shift only the coordinates inside figures:** smaller change, but the floor, anchors and names would still use the old centre. Rejected by the decision for C8.

## 8. Status and handoff (2026-10-25)

Valid for version 0.1.0. Nothing is committed. All results below were reported by the Supervisor and spot-checked; the last full runs were `npm test` (6 Jest suites, 57 tests, plus the Playwright check) and `.\.venv\Scripts\python.exe -m pytest tests/ -q` (490 passed).

### 8.1 Implemented (uncommitted)

- Grid shift (men -1, centre 0, ladies +1), `Faceing` renamed to `EndFacing`, root `Figures/` and `Dances/` removed, `1cLT` fixed, `1cLT1c` replaced by `1cLT` + `B4` + `E1c`, `B<n>` duration addon, conflicting addons rejected (C1 to C17).
- `StartDancers` and `StartFacing` (C18, C19, Q8, Q1c) with data for H1DR, H2DR, HLReelAU, HLReelAD, HRReelAU and HRReelAD. The four reel `Name` values now equal their filenames.
- Crips as data (`getCripsData`), in the API (`crips` lists in preview, dance detail, tree and trace) and in the inspector (Q9). Instructions sit at full width above two equal side-by-side floors. Line and dancer highlight each other.
- Single Apply button, live preview for figures in a dance (`POST /api/dances/<dance-id>/nodes/<node-id>/preview`), implicit cancel, error display with affected dancers (Q10).
- Dancers rotate with their facing; "catalog preview" titles removed; `npm test` works again; `Test_Comparison.py` retired; backup files use a counter (`<name>.<counter>.bak`).

### 8.2 Defects found in the first browser test on a catalog figure (H1DR), not yet fixed

1. **Apply button covers text.** The "Apply" button at the top right of the inspector overlaps the "Catalog figure" label. Fix: place the label and the button side by side without overlap.
2. **Instructions ignore add-ons in the catalog preview.** The outgoing floor follows a ticked add-on, but the instruction lines do not change. Find out whether the preview API builds the crips without the selected add-ons, or whether the frontend keeps the old lines. Add a test: ticked add-on changes the text (for example `E1c` on `1cLT`: "ends facing ...").
3. **Anchor column has no effect.** The floors follow the anchor row but not the anchor column. User proposal: remove the column field from the inspector, since the column is not used in real life. Needs: remove the field, the API field and the tests that use it, or fix it. The user prefers removing it.

### 8.3 Open items

- The dance "Marries Wedding" fails to execute ("Execution failed. Showing the last valid floor."). The user wants this handled in a separate session. The preview of a figure inside a dance could not be tried because of it.
- The title text of the Dance floor snapshot overlaps the "Ladies" label (dance panel only).
- The first test of the single Apply button was written after the code, not first.
- Undo and redo are not tested directly with a pending preview.
- Agent instructions for turning a user description into an addon are not written (postponed on request).
- The inspector layout in the dance panel and the dance preview have not been judged on screen.

### 8.4 How to continue

- Workflow: design agent writes decisions into this document; a Supervisor agent (`.github/Agents/Supervisor.agent.md`) delegates to the `Coding` agent with TDD, and does not commit. Always use `.\.venv\Scripts\python.exe`. The Supervisor tends to go idle early, so check the worktree and its report.
- Suggested next task for the Supervisor: fix 8.2 items 1 to 3 (tests first), then run `npm test` and the pytest suite.
- Commit only after the user agrees. A commit message needs the Co-authored-by trailer.

