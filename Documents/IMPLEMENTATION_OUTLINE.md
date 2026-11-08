# DanceCreator implementation outline

This outline is derived from `Documents/GUI_ENGINE_STRATEGY.md`, which is authoritative.
The existing JSON files, schemas, implementation notes, and GUI are treated as legacy
inputs or projections until the stages below replace them.

## 1. Gap analysis

### Canonical dance and occurrence identity

**Reusable:** the recursive `FigureList` grammar (`s`/`p`, anchor, figure reference and
addon list), `TreeConverter`, and the file lookup code in `Dance.py` and
`GUI_DanceCreator_App.py` are useful legacy adapters. Existing tree traversal also provides
the basic group/leaf projection.

**Change:** `ComplexFigure._FigureObjs` and the current jsTree nodes are not a canonical
model. They identify content by position/name and generate transient IDs. Introduce a
`DanceDocument` with explicit group and occurrence nodes. Persist opaque occurrence IDs,
figure references, anchors, addon selections, metadata, draft status, and format version.
Tree paths are diagnostic paths, not identity.

**Missing:** occurrence-level parent/group IDs, stable IDs across reorder and parameter
edits, unresolved-reference status, revision, and a lossless canonical serializer.

**Contradictions to flag:** `schema/dance.schema.json`, `api_dance_create_request.schema.json`,
`api_dance_update_request.schema.json`, `API_CONTRACT.md`, `DANCE_TREE_API_CONTRACT.md`, and
`DANCE_ENGINE_FLOW.md` describe Version 3 arrays or jsTree/`ComplexFigure` as the model and
do not represent occurrence identity.

### Figure capabilities and addons

**Reusable:** `SimpleFigure` loads Version 2 figure definitions and `FigureAddon` applies
legacy positional/cript overrides. `figure_summary()` already normalizes addon dictionaries
for catalog display.

**Change:** addon capabilities must be exposed by the engine, not inferred or accepted from
the browser. Addons belong to occurrences or temporary previews, not shared definitions.
The misspelled legacy `Faceing` field and mutable class attributes should be isolated behind
an adapter.

**Missing:** a capability object, valid addon list with parameter metadata, and a validator
for addon combinations and context-dependent validity.

**Contradictions to flag:** `figure.schema.json` permits broad additional properties and only
describes addon shape; old GUI/backend documents describe arbitrary key/value editing.

### Series, parallel, and duration

**Reusable:** `ComplexFigure.subDanceMove()` expresses the intended series/parallel control
flow, and `Bars` recursively sums series children.

**Change:** parallel children must receive the exact same incoming floor and their results
must be merged by a conflict-aware write-set operation. `combineDanceFloor()` currently
blindly inserts maps and can overwrite/raise incidental exceptions. `Bars` raises a generic
exception and is not a structured pre-execution validation.

**Missing:** deterministic branch result objects, explicit write sets, equal-duration
validation for every parallel path, and explicit wait/padding semantics.

**Contradictions to flag:** `test_combine_conflict.py` is disabled; `DANCE_ENGINE_FLOW.md`
documents generic exceptions rather than the strategy's structured rejection.

### Execution trace and floor snapshots

**Reusable:** `DanceFloor` contains positions, facing, dancer identity, and `AktBar`;
`_serialize_floor()` is a starting API adapter.

**Change:** the mutable legacy floor must be wrapped by a stable read model and copied
without sharing mutable maps. Trace production must be part of engine execution, not inferred
by the GUI or reconstructed from names.

**Missing:** occurrence/group trace records, incoming/outgoing snapshots, branch results,
bar ranges, execution status, writes, and an explicit representation for a failed group.

### Validation and conflicts

**Reusable:** JSON Schema validation helpers and `ApiRequestValidator` can remain transport
guards. Existing `TreeConversionError`/`FileManagerError` are adapter-level exceptions.

**Change:** validation must be domain-level, ordered by structural, reference/capability,
duration, and execution checks. Errors need canonical tree paths and node/occurrence IDs.
Parallel conflict reports must identify position, competing writes, dancers, and branch
occurrences. A rejected operation must leave model and trace unchanged.

**Missing:** `ValidationReport`, stable error codes, structured conflict details, and
first-blocking/all-errors behavior.

### Semantic editing, proposal/Apply, undo/redo

**Reusable:** current tree conversion and route plumbing can be retained temporarily as
read-only projection code.

**Change:** PUT of arbitrary jsTree JSON is incompatible with the strategy. Add semantic
commands for insertion, deletion, reorder, move, anchor/addon update, and group creation.
Proposals show structural changes only; Apply validates and commits document plus trace.
Only accepted Apply operations enter history.

**Missing:** command objects, immutable candidate copies, base revision checks, proposal
state, transactional commit, and history that restores both semantic data and trace.

### Archive persistence

**Reusable:** `FileManager`, JSON loading, filename sanitization, and existing dance/figure
resolvers provide filesystem primitives.

**Change:** a portable export is one archive containing the canonical dance, all referenced
figure definitions, manifest/version, and optional assets. Import must validate every member
and semantic reference before writing, then stage and atomically replace/create. Incomplete
drafts are valid only when explicitly declared and unresolved references are preserved.

**Missing:** package manifest, current-only package validator, staging/rollback boundary, and
copy-versus-confirmed-replace policy.

### API read/write contracts

**Reusable:** Flask routes for catalog/list/detail/tree, response envelopes, and floor
serialization. Existing schemas provide naming and pagination precedents.

**Change:** return canonical dance data plus a tree projection, trace, validation, revision,
and capability metadata. Writes must submit commands/proposals or canonical save payloads,
not make jsTree authoritative. Use structured 400/409 responses and invalidate caches only
after accepted commits.

**Missing:** proposal/apply, trace, capabilities, archive, history, revision/ETag, and
explicit incomplete-draft contracts.

**Contradictions to flag:** `api_dance_tree_update_request.schema.json` explicitly accepts
jsTree as the update source; `api_dancefloor_execute.schema.json` permits unstructured
conflicts; `API_CONTRACT.md` and `DANCE_TREE_API_CONTRACT.md` describe direct tree writes.

### Desktop tree editor and static renderer

**Reusable:** `templates/index.html`, `static/app.js`, existing catalog/tree panels, CSS,
and frontend test scaffolding establish the desktop shell.

**Change:** the tree must render canonical IDs and issue proposals; it must not execute
figures or calculate floors. Selection must distinguish group incoming/combined state from
child isolated results. Addon controls must be capability-driven. The renderer consumes
floor snapshots and displays dancer identity, couples, coordinates, facing, and context.

**Missing:** Apply/Cancel workflow, occurrence inspector, validation/conflict panel,
undo/redo UI, and authoritative boundary playback.

**Contradictions to flag:** `IMPLEMENTIERUNG_GUI.md` proposes responsive layouts, local
execution, video/PDF and continuous animation that are deferred; current canvas is a
placeholder.

### Caching

**Reusable:** global figure catalog and existing read-only list/detail calls are candidates
for a small cache.

**Change:** cache immutable figure definitions/capabilities, dance read models, and tree
projections keyed by reference and document revision. Proposals must not poison caches;
accepted Apply/import invalidates affected dance and trace entries.

**Missing:** explicit cache ownership, revision keys, and invalidation tests. Virtualization,
prefetching, and aggressive optimization are intentionally deferred.

## 2. Proposed technical design

### Domain model

Place canonical types in `src/engine/domain/dance_model.py`:

```python
from typing import Tuple, Union

@dataclass(frozen=True)
class FigureOccurrence:
    id: str
    figure_ref: str
    anchor: Tuple[Union[int, float], Union[int, float]]
    addons: tuple[str, ...]

@dataclass(frozen=True)
class CompositeOccurrence:
    id: str
    figure_ref: str
    anchor: Tuple[Union[int, float], Union[int, float]]
    addons: tuple[str, ...]
    root: GroupNode

@dataclass
class GroupNode:
    id: str
    kind: Literal["series", "parallel"]
    children: list["DanceNode"]

DanceNode = Union[FigureOccurrence, CompositeOccurrence, GroupNode]

@dataclass
class DanceDocument:
    format_version: int
    metadata: dict[str, object]
    root: GroupNode
    incomplete: bool
    unresolved_references: list[str]
    revision: int
```

Canonical JSON uses `formatVersion`, `metadata`, `status`, and recursive `root`; it never
stores renderer expansion state or calculated snapshots. IDs are opaque UUID/ULID-like values
generated once on insertion/import and persisted thereafter. Legacy import assigns IDs once;
reordering never regenerates them. `OccurrencePath` is a tuple of child indexes used only in
diagnostics.
diagnostics. A `CompositeOccurrence` retains its outer figure-reference identity and embeds
the referenced Version 3 definition's groups and child occurrences under `root`; all embedded
IDs are persisted with the dance. Composite anchors are inherited offsets during execution;
nested composite offsets add, preserving legacy behavior.

Key signatures:

```python
DanceDocument.from_json(data, repository) -> DanceDocument
DanceDocument.to_json() -> dict
DanceDocument.find_node(node_id) -> DanceNode
validate_structure(document) -> ValidationReport
```

### Capabilities and floor model

Add repository/domain adapters under `src/engine/figures/` and `src/engine/domain/`:

```python
@dataclass(frozen=True)
class FigureCapabilities:
    figure_ref: str
    bars: int
    formation: str | None
    valid_addons: tuple[dict[str, object], ...]
    supports_preview: bool

class FigureRepository:
    def get_definition(self, figure_ref: str) -> FigureDefinition: ...
    def get_capabilities(self, figure_ref: str) -> FigureCapabilities: ...
    def validate_addons(self, figure_ref, addons, path, occurrence_id=None) -> None: ...
```

`validate_addons()` raises `AddonValidationError` with a stable code, field path, and
occurrence ID when a selection is invalid.

Use `FloorState` as the stable read model:

```json
{
  "couples": 2,
  "tick": 4,
  "positions": {
    "1m": {"coord": [1, 1], "dancer": {"id": "1m", "name": "1m", "gender": "M"}, "facing": [1, 3]}
  }
}
```

Keep legacy `SimpleFigure`/`DanceFloor` execution behind adapters until the new executor is
complete. Addon combination validators may be figure-specific; if no validator exists,
individual capability checks still apply, but the occurrence remains executable only after
the engine accepts the combination.

### Execution and trace

Add `src/engine/execution/executor.py`, `combine.py`, `duration.py`, and `trace.py`:

```python
execute_document(document, initial_floor, repository) -> ExecutionResult
execute_node(node, incoming, path, context) -> NodeExecution
```

`NodeExecution` carries outgoing state, duration, trace records, writes, and diagnostics.
Series feeds each child’s output to the next and sums durations. Parallel executes every
child from the same incoming snapshot, validates equal child durations, compares writes
deterministically, then merges. A parallel conflict returns a failed `ExecutionResult` with
child traces and conflict diagnostics; the failed group has `outgoingFloor: null`, while the
last valid floor is retained separately for inspection. A duration error rejects before
execution and has no result.

Each `TraceRecord` contains `nodeId`, `kind`, `figureRef` when applicable, `groupPath`,
`barRange`, `incomingFloor`, `outgoingFloor`, `status`, `writes`, and branch summaries.
`barRange` uses one-based inclusive start/end bar numbers. The engine produces each record
once using immutable `FloorState` snapshots; the API serializes it; the GUI only selects and
renders it. Do not introduce a separate wire position-key convention in this stage.
Per-bar snapshots are emitted only when the engine actually has authoritative states.

### Validation and errors

Use `src/engine/validation/errors.py`:

```json
{
  "code": "parallel_conflict",
  "severity": "error",
  "path": "root.children[1].children[0]",
  "nodeId": "g-2",
  "occurrenceId": "o-b",
  "field": "execution",
  "message": "Parallel branches write different dancers to position 1m.",
  "details": {
    "groupId": "g-2",
    "position": [1, 1],
    "competingWrites": [
      {"occurrenceId": "o-b", "dancerId": "1m", "to": [1, 1]},
      {"occurrenceId": "o-c", "dancerId": "2m", "to": [1, 1]}
    ]
  }
}
```

`validate_document(document, initial_floor, repository)` returns a report with `errors`,
`warnings`, `is_valid`, and `first_blocking`; the explicit floor/repository inputs provide the
execution context required to report conflicts and durations. Structural paths remain stable
even when IDs are opaque. Validation order is structure, reference/capability, duration, then
executable conflicts. A report containing unresolved references remains invalid and identifies
the first one as blocking even when the document is explicitly marked incomplete. The save
workflow may separately permit a confirmed incomplete draft; this does not make it executable
or change the validation report.

### Editing and history

Place commands in `src/engine/editing/`:

```python
apply_command(document, command, repository=None) -> DanceDocument
create_proposal(document, command, base_revision, repository=None) -> Proposal
apply_proposal(state, proposal) -> CommitResult
cancel_proposal(proposal) -> None
history.undo() -> State
history.redo() -> State
```

Commands include `InsertOccurrence`, `DeleteNode`, `ReorderNode`, `MoveNode`,
`UpdateAnchor`, `UpdateAddons`, and `CreateGroup`. A proposal contains a candidate semantic
document and structural tree projection, but no new trace. Apply validates, executes, commits
document plus trace atomically, and creates exactly one history entry. Undo/redo restores both.
Every accepted Apply, undo, and redo advances the document revision monotonically; restoring an
older semantic snapshot must not re-use a revision that could let stale proposals apply.
`InsertOccurrence` requires repository context so it can distinguish atomic Version 2 figures
from Version 3 composites. Composite insertion recursively embeds the resolved tree with fresh
IDs; nested unresolved references remain preserved and mark the candidate incomplete.

### Archive and API

`src/engine/persistence/archive.py` defines a ZIP package:

```text
package.json
dance.json
figures/<stable-reference>.json
assets/                # optional
```

`package.json` declares exact current `formatVersion`, package identity, referenced figures,
and `incomplete`. The importer validates all members in memory/staging, including that every
claimed figure exists and supports each occurrence addon, before atomic replacement. Imported
packages remain in a per-dance namespace; that dance resolves its bundled definitions there,
and import never writes to or replaces the shared figure catalog. Resource checks run before
member materialization: 160 MiB compressed archive, 128 MiB total uncompressed data, 64 MiB
per member, at most 512 members, and a 1000:1 maximum expansion ratio. Dance names are unique
case-insensitively; a copy collision requires an explicit unique name from the caller, while
replacement continues to target the existing unique dance name.

The API should expose read-only catalog/capability/dance/tree/trace endpoints and semantic
proposal/apply/save, archive export/import, and history operations. Every write includes a
document revision or ETag. Errors use the validation shape above; parallel conflicts are 409,
malformed requests 400, and stale revisions 409.

### GUI and cache

Refactor `static/app.js` into catalog, tree projection, proposal state, inspector, playback,
and renderer modules; retain `templates/index.html` as the desktop shell. Tree IDs come from
the engine. The SVG/HTML renderer accepts `FloorState` only and draws static positions,
identity, couple information, coordinates, facing, and selected occurrence/group context.
Playback steps through initial, occurrence, and group boundaries.

Cache at the service layer by `(figure_ref, capability_version)` and `(dance_id, revision)`.
Accepted commits/imports invalidate the affected dance, trace, tree projection, and metadata;
Cancel/rejected proposals do not change cache state.

## 3. Staged implementation sequence

1. **Canonical occurrence-aware model** — add `src/engine/domain/dance_model.py` and a
   legacy adapter. First tests: `tests/test_canonical_dance_model.py` for stable duplicate
   IDs, recursive round-trip, unresolved references, metadata, and Version 3 composite
   embedding with stable child IDs/anchor offsets. Depends on the canonical gap/design. Done
   means no jsTree identity and lossless legacy loading. Do not touch GUI, schemas, or
   execution.
2. **Capability/addon metadata** — add repository capability types and
   `tests/test_figure_capabilities.py`. Assert exact engine-provided addon lists,
   occurrence-specific selections, invalid paths, and preserved failed combinations. Figure
   definitions carry an independent `CapabilityVersion`; optional declarative
   `AddonCombinationValidator.allowedCombinations` are unordered sets. Depends on stage 1. Do
   not alter execution or frontend.
3. **Series/parallel execution** — add execution executor/combine modules and
   `tests/test_execution_engine.py`. Assert same-input branches, nested execution,
   deterministic merges, repeated references, and input immutability. Shared writes are
   allowed when one branch vacates a position and another uniquely occupies it; competing
   final occupants or a retained incoming dancer competing with a peer write conflict.
   Depends on stage 2. Do not add routes or editing.
4. **Equal-duration validation** — add duration validation and
   `tests/test_parallel_duration_validation.py`. Assert series sums, equal paths, unequal
   rejection, and explicit wait/padding. Depends on stage 3. Do not coerce to longest path.
5. **Trace and snapshots** — add trace/read-model serialization and
   `tests/test_execution_trace.py`. Assert IDs, paths, ranges, incoming/outgoing states,
   group/child semantics, conflict handling, and no fabricated per-bar states. Depends on
   stages 3–4. Do not wire UI/API yet.
6. **Structured validation/conflicts** — add validation/report modules, replace the disabled
   conflict test with `tests/test_structured_validation.py`. Assert stable codes/paths,
   complete reports, conflict details, unresolved refs, and no mutation. Depends on stage 5.
   Do not accept raw jsTree writes.
7. **Semantic commands/proposals/history** — add `src/engine/editing/` and
   `tests/test_edit_commands.py`, `tests/test_proposal_history.py`. Assert all supported
   commands, Apply/Cancel, rejection rollback, one history entry, and trace restoration.
   Depends on stage 6. Do not wire drag/drop.
8. **Archive and transactional import/export** — add archive service and
   `tests/test_archive_format.py`, `tests/test_archive_transaction.py`. Assert self-contained
   references, status/IDs, strict current format, copy/replace, staging rollback, and
   incomplete drafts. Depends on stage 7. Do not rewrite existing data in place.
9. **API contracts/endpoints** — refactor Flask route/service boundary and add
   `tests/test_api_canonical_contracts.py`. Assert capabilities, canonical projection,
   trace, proposal/apply, revisions, errors, save drafts, and archive operations. Depends on
   stage 8. Replace the legacy `/api/...` dance/tree contracts in place; no compatibility
   shim or separately versioned duplicate contract. Do not implement browser editing here.
10. **Desktop tree editor** — refactor `static/app.js`, `static/style.css`, and
    `templates/index.html`; add frontend tests where the existing runner supports them.
    Assert canonical IDs, inspector, capability controls, Apply/Cancel, undo/redo, and
    incomplete warnings. Depends on stage 9. Do not add responsive/video/PDF scope.
11. **Static renderer and boundary playback** — add/refactor renderer modules and tests for
    identity, coordinates, facing, selected context, isolated parallel children, combined
    groups, conflicts, and discrete stepping. Depends on stages 9–10. Do not implement
    interpolation or invent per-bar snapshots.

## 4. Risks and open decisions

### Resolved (see `GUI_ENGINE_STRATEGY.md` § Foundational Technical Decisions)

The following were open when this outline was written and are now decided in the strategy
document. Implementation must follow the strategy's resolved wording, not the original framing
below, which is kept only for traceability:

- ~~Choose opaque ID format~~ → Opaque random (UUID/ULID-style) IDs, assigned once, never
  regenerated, and hidden from the GUI.
- ~~Decide whether legacy loading assigns IDs only in memory or immediately persists~~ →
  In-memory only; legacy files are never rewritten implicitly; canonical persistence happens
  only on explicit save in the new format.
- ~~Define the canonical formation/position model~~ → External position naming (e.g. `"1m"`,
  `"1w"`) is fixed by stakeholders and must remain stable at the API/GUI boundary; the internal
  coordinate representation may be redesigned as needed.
- ~~Decide archive replacement confirmation and transaction boundary~~ → One explicit
  confirmation before an atomic stage-then-swap write; the previous version is preserved in a
  dedicated, timestamp-versioned backup location (not the legacy `/Archive` reference folder).
- ~~Decide whether unresolved drafts require confirmation on every save~~ → Confirm once, on
  the first transition to incomplete status; subsequent saves while still incomplete do not
  re-prompt; incomplete status remains visibly marked at all times.
- ~~Define revision/ETag behavior~~ → In scope for the first release: every document carries a
  revision identifier; Apply/Save must match it or fail as a structured conflict.
- ~~Decide where addon-combination validators live~~ → Co-located with each figure's own
  definition/capability metadata, not a central registry, and not left to incidental execution
  rejection alone.
- ~~Decide validator versioning and combination representation~~ → Each figure carries an
  independent positive-integer `CapabilityVersion` (legacy default `1`); JSON definitions may
  declare `AddonCombinationValidator.allowedCombinations` as unordered sets. Validation
  preserves submitted selection order and rejects duplicate selections.
- ~~Define parallel writes to vacated positions~~ → A shared position may be merged when one
  branch vacates it and exactly one branch supplies a different final occupant. Competing final
  occupants and a retained incoming dancer competing with a peer write remain conflicts.
- ~~Decide trace bar-range boundaries~~ → Use one-based inclusive start and end bar numbers.
- ~~Decide how parallel-conflict traces are exposed~~ → Return a failed `ExecutionResult`
  containing isolated child traces and conflict details, with no group outgoing floor and the
  last valid floor preserved separately.
- ~~Define validation validity for explicitly incomplete drafts~~ → Unresolved references
  remain errors and the first one is blocking; an explicit incomplete-draft save policy is
  separate from validation validity and execution remains unavailable.
- ~~Define addon support on Version 3 composite occurrences~~ → Non-empty outer composite addon
  selections are unsupported until composite capability metadata and execution behavior exist;
  addons on embedded atomic occurrences remain independently validated.
- ~~Choose storage for imported bundled figure definitions~~ → Retain definitions in a
  per-dance package namespace and resolve them for that dance only; never overwrite the shared
  figure catalog.
- ~~Define archive resource limits~~ → Maximum compressed archive size 160 MiB, maximum total
  uncompressed data 128 MiB, maximum member size 64 MiB, at most 512 members, and maximum
  expansion ratio 1000:1. Check ZIP metadata before reading members and bound actual streaming
  decompression to handle inconsistent metadata.
- ~~Define canonical tree nesting depth~~ → Archive input may not exceed 128 DanceNode levels,
  counting the root group, group children, and embedded composite roots; reject deeper trees
  before recursive model parsing and convert any other recursion exhaustion to `ArchiveError`.
- ~~Define archive copy naming and replacement target~~ → Dance names are unique case-insensitively.
  A copy collision requires a caller-provided unique name; no automatic suffix is added.
  Replacement targets the existing unique dance name and retains explicit confirmation.
- ~~Choose canonical API route migration~~ → Replace legacy `/api/...` dance/tree contracts
  in place with the first-release canonical contracts; do not preserve jsTree writes through a
  compatibility endpoint or add a second versioned namespace.
- ~~Define Version 3 composite catalog insertion~~ → Insert as `CompositeOccurrence`, recursively
  embed resolved groups/children with fresh IDs, and preserve unresolved nested references while
  marking the candidate incomplete.
- ~~Decide how Version 3 composite references are represented~~ → Keep a first-class composite
  figure occurrence and embed its resolved group/child tree under it with persisted IDs;
  inherit and add composite anchor offsets to descendants, matching legacy execution.

### Still open

- Existing data uses Version 2/3 legacy fields, `Faceing`, mixed `data/` versus root paths,
  and addon arrays/dictionaries. Use adapter-first dual-read migration and explicit canonical
  export; do not edit `Figures/*.json` or `Dances/*.json` during these stages.
- Current mutable class attributes, shallow floor copies, generic exceptions, global catalog
  state, transient tree IDs, and loose schemas are direct implementation risks.
