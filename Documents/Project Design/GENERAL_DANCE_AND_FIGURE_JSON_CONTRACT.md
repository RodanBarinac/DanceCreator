# General Dance and Figure JSON Contract

> **Valid for version:** 0.1.0  
> **Status:** Normative writing and reading contract for upstream dance authors  
> **Last updated:** 2026-11-08

## 1. Purpose and scope

This document defines the JSON files an upstream author must produce so DanceCreator can
resolve and execute dances and figures. It covers file placement, versions, field meanings,
composition, figure calls, addons, coordinates, timing, validation, and delivery requirements.
It is for source data files, not API responses or the GUI tree format.

The contract describes the current data model and runtime. It also sets conservative authoring
rules where existing legacy syntax is ambiguous. Follow the rules in this document even if an
older example or schema permits a looser form.

## 2. File types and locations

| File kind | Location | `Version` | JSON shape |
|---|---|---:|---|
| Atomic/simple figure | `data/Figures/<FigureName>.json` | `2` | Start/end positions, bars, instructions |
| Composite/reusable figure | `data/Figures/<FigureName>.json` | `3` | A recursive `FigureList` |
| Complete dance | `data/Dances/<DanceName>.json` | `3` | Dance metadata and a recursive `FigureList` |
| Reusable dance fragment | `data/Dances/subDances/<FragmentName>.json` | `3` | A recursive `FigureList`; called by a complete dance or another composite |

Use the JSON filename stem as the reference name. Names must be unique across both data
directories and all subdirectories: resolution may search recursively by basename, so duplicate
stems can resolve ambiguously. A reference is a name such as `"1cRT"`, not a path or a filename
with `.json`.

Write UTF-8 JSON with double-quoted strings, no comments, and no trailing commas. Do not write
Python tuples, `NaN`, or infinity.

## 3. Coordinates and anchors

Every position or anchor is a two-number array:

```json
[row, column]
```

Coordinates are finite numbers; fractional values are valid. Dance-floor columns use the
centered grid: men’s line `-1`, center `0`, women’s line `+1`. Couple rows are numbered from `1`.
Figure positions are offsets, not absolute floor positions.

An occurrence anchor translates a figure’s local coordinates onto the dance floor:

```text
absolute position = occurrence anchor + figure-local position
```

Anchors add down the composition tree. For example, an occurrence with anchor `[2, 0]` places a
local start position `[0, -1]` at `[2, -1]`. Use `[0, 0]` when no translation is needed.

Facing targets are coordinates, not direction vectors. Coordinate entries in `EndFacing` are
local target positions translated by every occurrence anchor. Empty or missing entries use the
default same-row opposite-column target: `[row, column]` faces `[row, -column]`. Runtime floors
store this default as a concrete target coordinate, not as an empty value.

`EndFacing` also accepts these exact, case-sensitive symbolic entries. They are resolved using
the dancer's final absolute position after all anchors and addons have been applied:

| Entry | Target |
|---|---|
| `=` | Preserve incoming direction: translate the incoming target-minus-start offset to the final position. A valid incoming target distinct from the start is required. |
| `I` | Face the center at `[row, 0]`. This is an error when the final absolute column is `0`. |
| `O` | Face away from the center at `[row, 2 * column]`. This is an error when the final absolute column is `0`. |
| `U` | Face one row up at `[row - 1, column]` (rows increase downward). |
| `D` | Face one row down at `[row + 1, column]`. |
| `OwnL` | Face the dancer's own line in the same row: male `-1`, female `+1`. It is an error when already on that line. |
| `OpL` | Face the opposite line in the same row: male `+1`, female `-1`. It is an error when already on that line. |
| `M` | Not executable: last-move direction is not available in the runtime. Execution returns the structured error `unsupported_facing_notation`; do not use `M`. |

No other strings are accepted. `I`/`O` test the final absolute column (not the local value),
and `OwnL`/`OpL` use the dancer identity on the incoming floor. In an isolated catalog preview,
identity comes from `StartDancers`. Crips `{Face}` uses the same resolved target as execution.

## 4. Dance and composite-figure format

A dance and a composite figure are both version 3 objects. Both have a root `FigureList` group.
A complete dance must include non-empty `Name`, `Desc`, and `shape` fields, plus `Version: 3`
and `FigureList`. `shape` is a string in `dancing-couples/couples-in-set` form, such as `"3/4"`.
The first number must not exceed the second. A reusable fragment may omit `shape`; it still
requires `Name`, `Desc`, `Version: 3`, and `FigureList`.

`FigureList` is recursively composed of groups and figure calls:

```text
Group       := ["s" | "p", [Element, ...]]
Element     := Group | FigureCall
FigureCall  := [Anchor, FigureTarget]
Anchor      := [rowOffset, columnOffset]
FigureTarget := FigureName | [FigureName, [AddonName, ...]]
```

Use a group as exactly `[groupType, elements]`. Groups can be nested directly. A figure call
uses an anchor and a target. Use the two-item target form consistently, including an empty addon
list when there are no addons:

```json
[[1, 0], ["1cRT", []]]
```

The string shorthand is also supported when no addons are selected:

```json
[[1, 0], "1cRT"]
```

The complete dance’s root group has the same group syntax:

```json
{
  "Name": "Example Dance",
  "Desc": "A short example",
  "shape": "1/1",
  "FigureList": [
    "s",
    [[[1, 0], ["1cRT", []]]]
  ],
  "Version": 3
}
```

Group behavior:

- `"s"` means **series**. Each element runs in order; the outgoing floor of one element is the
  incoming floor of the next. The group duration is the sum of its elements.
- `"p"` means **parallel**. Each branch starts from the same incoming floor and the results are
  merged. Every branch must take the same number of bars. Branches must describe compatible,
  non-conflicting dancer and position changes; do not make two branches move or overwrite the
  same dancers/positions.
- A group must contain at least one element. All nested groups must obey these rules.

Use unanchored nested groups (`["s", [...]]` or `["p", [...]]`) and put translations on figure
calls. Some legacy files wrap nested groups in an anchor pair, but the effect of such a group
anchor is not consistent across the loader, validator, and tree converter. Do not use that form
in newly authored files.

Composite figures under `data/Figures/` use the same `FigureList` syntax, with `Version: 3`.
They can be referenced by a dance like any other figure. To ensure predictable behavior, apply
addons only to atomic/simple figures, not composite figures.

## 5. Atomic/simple-figure format

An atomic figure describes the movement of one or more dancers. Its file must have `Version: 2`,
and include the required fields below. All per-dancer arrays use the same order: index `i` always
refers to the same dancer.

| Field | Requirement and meaning |
|---|---|
| `Name` | Required non-empty figure name; match the filename stem. |
| `Desc` | Required human-readable description. |
| `Formation` | Required descriptive formation/type label, for example `"turn"` or `"reel"`. |
| `Version` | Required integer `2`. |
| `Bars` | Required positive whole number of bars. |
| `StartPos` | Required non-empty list of local start-position pairs. |
| `EndPos` | Required list of local end-position pairs, one per `StartPos`. |
| `CriptDesc` | Required list of instruction templates, one per dancer. |
| `Partner` | Include when an instruction uses `{Partner}`; one local target-position pair per dancer. |
| `EndFacing` | Optional per-dancer list of target positions or symbolic entries from §3; empty/missing entries use the default facing. |
| `StartFacing` | Optional per-dancer list of target positions for isolated catalog preview only. |
| `StartDancers` | Optional per-dancer preview identities for isolated catalog preview only. |
| `Addons` | Required object mapping addon names to addon definitions; use `{}` when none exist. |

Example:

```json
{
  "Name": "1cRT",
  "Desc": "Two bar right-hand turn for one couple",
  "Formation": "turn",
  "Version": 2,
  "Bars": 2,
  "StartPos": [[0, -1], [0, 1]],
  "EndPos": [[0, -1], [0, 1]],
  "Partner": [[0, 1], [0, -1]],
  "CriptDesc": [
    "{Dancer} turns right hand with {Partner} and ends in own place.",
    "{Dancer} turns right hand with {Partner} and ends in own place."
  ],
  "Addons": {}
}
```

For `StartPos`, `EndPos`, `Partner`, and `EndFacing`, each coordinate is relative to the
occurrence anchor. In the example, the first dancer starts at local `[0, -1]` and the second at
`[0, 1]`; an occurrence anchor `[2, 0]` translates those to `[2, -1]` and `[2, 1]`.

`EndFacing` and `StartFacing` use one entry per dancer. An `EndFacing` entry is a target
coordinate pair, an empty array `[]`, or one of the symbols in §3. Missing `EndFacing` entries
and empty entries use the concrete default opposite-line target. `StartFacing` remains
coordinate-only: each entry is either a target coordinate pair or `[]`. Missing `StartFacing` is
equivalent to an all-empty list. `StartFacing` only sets up a standalone catalog preview; in a
dance, incoming facing comes from the actual floor state and `StartFacing` is ignored.

`StartDancers` is a preview-only list parallel to `StartPos`. Each non-empty ID has a positive
couple number followed by `m` or `w`, for example `"2m"` or `"1w"`. Empty strings use automatic
allocation in list order (`1m`, `1w`, `2m`, `2w`, ...). The final IDs must be unique. During dance
execution these IDs do not rename or select dancers; the floor must contain a dancer at every
declared start position.

Supported `CriptDesc` placeholders are:

| Placeholder | Replaced with |
|---|---|
| `{Dancer}` | Name of the dancer occupying this start position |
| `{StartPos}` | Display name of this dancer’s start position |
| `{EndPos}` | Display name of this dancer’s end position |
| `{Face}` | Display name of this dancer’s resolved `EndFacing` target, including symbolic notation and addon `null` resets |
| `{Partner}` | Name of the dancer at this entry’s `Partner` target |

Avoid other placeholder spellings: they are not part of this contract. Instruction templates
should be meaningful for their dancer and should not rely on a guessed dancer identity.

## 6. Addons

An atomic figure’s `Addons` object defines named modifications for that figure. An occurrence
selects addons by name in its figure target, for example:

```json
[[1, 0], ["1cLT", ["B4", "E1c"]]]
```

The selection is a list of unique strings. Each selected name must either be defined in that
figure’s `Addons` object or be a valid engine-reserved duration addon.

A named addon definition is an object containing `Name`, `Desc`, and `Version` metadata. It may
modify these fields:

| Addon field | Effect |
|---|---|
| `Bars` | Replaces the figure’s duration. |
| `StartPos` | Replaces selected per-dancer start positions. |
| `EndPos` | Replaces selected per-dancer end positions. |
| `EndFacing` | Replaces selected per-dancer ending-facing targets or symbolic entries, or resets them to the default as described below. |
| `Partner` | Replaces selected per-dancer partner target positions. |
| `CriptDesc` and `CriptReplace` | Replace text within instruction templates, index by index. |

For per-dancer addon arrays, use `[]` for entries that should remain unchanged. Keep array
indices aligned with the base figure’s dancers. An `EndFacing` addon entry may be a coordinate
target or one of the symbolic entries in §3. **In an addon’s `EndFacing` array only**, use JSON
`null` to explicitly reset that dancer’s ending facing to the default; `[]` continues to mean
“leave the base figure’s facing unchanged.” A symbolic value is a real write, so it conflicts
with another selected addon writing `EndFacing` for that dancer. For example:

```json
{
  "EndFacing": [null, []]
}
```

This resets dancer 1 to default facing and leaves dancer 2’s base facing as-is. The default is
computed from the dancer’s final position after the selected addons and anchor are applied:
`[row, column]` faces `[row, -column]`. A `null` reset is a real write to `EndFacing` and
conflicts with another selected addon that writes `EndFacing` for that same dancer. Do not use
`null` in other addon arrays.

For instruction text replacements, both
`CriptDesc[i]` (replacement text) and `CriptReplace[i]` (text to find) must be non-empty at an
index for that replacement to occur.

Multiple selected addons may modify different fields or different dancer indices. They must not
modify the same field for the same dancer. Such overlaps are errors; there is no later-addon-wins
rule. In particular, do not combine multiple duration changes.

`B<n>` is an engine-reserved duration addon, where `n` is a positive integer with no leading
zero, such as `"B3"` or `"B8"`. It sets `Bars` to `n` without changing the movement path and is
not declared in `Addons`. A named addon must not use a `B<n>` name. A single `B<n>` can be used
with other addons only if none of them also changes `Bars`.

## 7. Reading, resolving, and validating files

An upstream reader or writer should follow this sequence:

1. Parse the file as a JSON object and identify its kind by `Version` and presence of
   `FigureList`: version 2 without `FigureList` is atomic; version 3 with `FigureList` is
   composite or dance. A version 3 file in `data/Dances/subDances/` is normally a reusable
   fragment.
2. Resolve every figure reference by filename stem against the project data directories. Confirm
   that each reference resolves to exactly one definition. Do not invent a reference or addon
   name; use an existing definition or include a new definition as a separate figure file.
3. Check every group, figure call, anchor, coordinate, version, required field, and per-dancer
   array. Check that the selected addons exist, are unique, and do not conflict.
4. Compute duration recursively: series durations add; parallel branch durations must match.
5. Simulate the dance from the standard starting floor for the declared set size. Confirm that
   each figure’s required dancers are present at its start coordinates, that branch results
   merge without conflict, and that final positions and facing are valid.
6. Deliver valid `.json` files at the locations in §2 and include all newly referenced figure
   definitions. Preserve existing unrelated files; do not silently replace a figure with a
   different meaning under the same name.

For complete dances, `shape` is required by this contract even though the current
`schema/dance.schema.json` does not require it. Existing reusable fragments may omit it.

## 8. Compatibility and known validation gaps

The current JSON Schemas are not a complete substitute for this contract:

- `schema/dance.schema.json` describes the version 3 recursive group/call structure but does not
  require `shape`, and its `FigureTarget` definition is looser than the runtime format.
- `schema/figure.schema.json` does not accurately express all simple-figure array constraints
  and mixes version 2 atomic fields with version 3 composite fields.
- The figure and update-request schemas accept the agreed `EndFacing` symbols in base and addon
  arrays, and allow `null` only as an addon `EndFacing` entry. Runtime validation is still needed
  for identity-, anchor-, and incoming-floor-dependent errors; `M` passes notation validation but
  is explicitly unsupported during execution.
- Legacy files use some alternate nested-group wrappers; do not generate those.

Use this document’s authoring rules plus runtime/data validation. Do not use `Faceing`; the
supported key is `EndFacing`. Do not include an `Anchor` or `Anker` field in figure JSON:
placement is specified by the occurrence anchor in the containing `FigureList`.

## 9. Contract status, assumptions, and open points

The following behaviors are confirmed by the current data model or implementation: version 2
simple figures and version 3 compositions; recursive series/parallel groups; figure references
with local anchors and selected addons; series duration summation; equal-duration parallel
branches; centered-grid target coordinates and the symbolic `EndFacing` entries in §3; and addon
`EndFacing: null` resets using the final anchored position, with conflicts checked per dancer.
The writing rules above intentionally exclude legacy or ambiguous forms.

The following are explicit authoring assumptions or policies, rather than guarantees enforced by
every current validator:

- The first `shape` number is the number of dancing couples and the second is the number of
  couples in the set. A dance must not claim more dancing couples than couples in the set.
- `shape` is mandatory for a complete dance, based on the project API contract’s new-file rule.
  The current dance schema and request validator do not enforce this; reusable fragments may
  omit it.
- New addon definitions should use `Version: 1`. The addon version is metadata; runtime behavior
  is determined by the addon fields and the name-to-definition mapping.
- `Formation` is descriptive metadata. It is included because the figure schema requires it, not
  because movement execution reads it.

The following should be resolved in future schema/validator work, but do not prevent an upstream
author from following this contract: update `schema/dance.schema.json` and
`schema/figure.schema.json` to express these rules; clarify whether the first `shape` number is
always bounded by the second in all dance types; and decide whether composite-figure addons
should ever be supported. Until those changes are made, use the conservative rules in this
document and do not rely on schema validation alone.

## 10. Author deliverable checklist

- [ ] Every new dance, composite figure, and atomic figure is a standalone valid JSON file at the
  correct path and uses the correct version.
- [ ] Every full dance has `Name`, `Desc`, `shape`, `FigureList`, and `Version: 3`.
- [ ] Every reference and selected addon resolves; filenames are unique by stem.
- [ ] Every atomic figure has aligned start/end/instruction arrays and positive whole-bar timing.
- [ ] All positions, anchors, and partners use `[row, column]` coordinate pairs; `EndFacing`
  uses a coordinate pair or one of the symbols in §3 (`M` is not executable).
- [ ] Every parallel group has equal duration and compatible branch effects.
- [ ] Addon changes do not conflict; reserved duration addons follow the `B<n>` rules.
- [ ] The dance has been simulated for its declared set size and all referenced dancers are
  present at each figure’s start positions.
