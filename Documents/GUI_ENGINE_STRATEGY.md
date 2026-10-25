# GUI and Engine Strategy

> **Status:** STRATEGY BASELINE  
> **Last updated:** 2026-09-29

## Purpose

This document preserves the strategic conclusions for designing the DanceCreator GUI and
engine together. It is the baseline for future feature and architecture decisions.

## Product Direction

DanceCreator should become a **visual dance editor and execution inspector**, not only a
viewer or a collection of API endpoints.

The central user question is:

> What happens at this exact occurrence in this exact dance context?

The GUI must therefore support both:

- editing a dance's recursive choreography; and
- inspecting the dancefloor state before and after each figure occurrence.

## Core User Workflow

1. Browse and search available figures.
2. Inspect a figure's definition, metadata, and movement details.
3. Build or edit a dance through its hierarchical tree.
4. Select a specific figure occurrence in that tree.
5. View the incoming and outgoing dancefloor states for that occurrence.
6. Adjust anchors, addons, or other supported parameters and preview the result.
7. Validate and save the dance.
8. Import or export a complete dance without losing its meaning.

## Architectural Principles

### Canonical model

The recursive dance model is the source of truth. The jsTree representation is a GUI
projection and must not become the domain model.

### Figure occurrences

A tree node is a **figure occurrence**, not merely a reference to a figure definition. An
occurrence has its own:

- stable identity within the dance;
- figure reference;
- tree path and parent group;
- anchor and addon parameters;
- bar range;
- execution result and validation status.

The same figure definition may occur multiple times with different contextual states.
When a referenced figure definition is itself a Version 3 composite, preserve its outer
figure occurrence and embed the resolved recursive groups and child occurrences beneath it.
The composite and every embedded child/group have their own stable IDs, persisted in canonical
dance data. The composite anchor is inherited by its descendants as an offset, matching legacy
execution; nested composite anchors add to the inherited offset.

### Execution semantics

- Series children execute in order.
- Parallel children all receive the same incoming floor.
- Parallel children execute independently.
- Their results are combined into one outgoing floor.
- Any parallel branches writing to the same floor position conflict, even when the resulting
  dancer and facing values are identical; all overlapping writes are explicit
  validation/execution errors.
- Every executable occurrence has an incoming and outgoing floor state.
- Trace bar ranges use one-based bar numbers with inclusive start and end.
- If parallel combination conflicts, return a failed execution result with the isolated child
  traces and conflict details. The failed group has no valid outgoing floor; preserve the
  last valid floor separately for inspection.

“Before a figure” means the floor resulting from all applicable preceding execution steps in
the canonical execution order.

### Editing semantics

Edits are explicit validated operations, such as insert, move, reorder, delete, duplicate,
anchor update, addon update, and group update. Invalid edits must not modify the working
dance.

The first release should support only operations for which validation and rollback behavior
are clear.

### Persistence

Persist semantic dance data:

- metadata;
- recursive group structure;
- figure references;
- occurrence parameters;
- anchors and addons;
- transfer/schema version.

Do not persist renderer-only state such as tree expansion, CSS state, temporary errors, or
calculated floor snapshots.

Import must validate completely before replacing or creating a dance. Failure must leave the
existing dance unchanged.

## Engine Capabilities Required by the GUI

The engine should provide:

1. A canonical occurrence-aware dance model.
2. Deterministic recursive execution for series and parallel groups.
3. An execution trace containing occurrence ID, figure reference, group path, bar range,
   incoming floor, outgoing floor, and execution status.
4. Structured validation errors with tree paths.
5. Structured parallel-conflict details, including affected positions and occurrence IDs.
6. Validated editing commands rather than arbitrary JSON mutation.
7. A stable floor-state read model for renderers.

The frontend must not independently reproduce dance execution logic.

## Recommended Delivery Order

### Foundation

1. Define the canonical dance and occurrence model.
2. Define series, parallel, anchor, and bar semantics.
3. Define execution traces and floor snapshots.
4. Define validation and conflict behavior.

### Minimum useful GUI

5. Load a dance and display its recursive tree.
6. Select an occurrence and show incoming/outgoing floor states.
7. Display figure metadata and parameters.
8. Add, reorder, delete, and save supported edits.
9. Show structured validation and conflict errors.

### Later capabilities

10. Full drag-and-drop editing and advanced parameter editing.
11. Import/export and transactional replacement.
12. Undo/redo, playback, bar scrubbing, PDF export, and video rendering.
13. Caching, virtualization, and performance optimization.

## How Open Questions Are Resolved

Open questions are answered in this order:

1. **User scenario:** what is the user trying to accomplish?
2. **Product decision:** what should the user be allowed to do?
3. **Domain invariant:** what must always be true?
4. **Canonical example:** what exact input and output demonstrate the rule?
5. **Executable contract:** what test, data shape, and GUI behavior prove it?
6. **Technical implementation:** which engine, API, and UI components realize it?

Product and domain decisions come before technical decisions.

Every important decision should produce:

- a short decision statement;
- a representative JSON/data example;
- an automated test;
- the corresponding GUI behavior.

## Scenario Set

The first scenarios to define are:

1. A single figure.
2. A simple series of two figures.
3. A parallel group.
4. A nested series containing a parallel group.
5. The same figure used twice with different anchors.
6. A figure with addons.
7. An invalid parallel conflict.
8. An unresolved figure reference.
9. Adding and reordering a figure in the tree.
10. Importing and validating a complete dance.

Each scenario should specify the user intent, visible GUI state, allowed action, expected
engine result, invalid behavior, and required persisted data.

## Foundational Technical Decisions

These decisions resolve the open risks identified while planning implementation. They are
binding for the first release.

### Occurrence and group identity

IDs are opaque, randomly generated identifiers (UUID/ULID-style), assigned once when an
occurrence or group is created and never regenerated by reorder, move, or parameter edits.
IDs are internal engine identity only. The GUI does not display raw IDs to the user; it
identifies occurrences by figure name, anchor, and bar range as already decided in Scenario 5.

### Legacy loading and ID persistence

When the engine loads an existing legacy `Dances/*.json` file, it assigns occurrence and group
IDs only in memory for that session. The legacy file on disk is not rewritten. Canonical IDs
and the canonical document format are persisted only when the user explicitly saves in the new
format. Loading a file must never silently migrate or mutate it.

When a legacy figure reference resolves to a Version 3 composite definition, loading preserves
the referenced composite as a figure occurrence and recursively embeds its definition's
groups/child occurrences in that occurrence. Assign IDs to the composite and all embedded
nodes in memory; persist them only on explicit canonical save.

### Formation and position naming

The external position-naming contract (for example `"1m"`, `"1w"`, couple-oriented grid
naming) is fixed by stakeholder requirements and must remain stable at the API and GUI
boundary. The engine's internal coordinate representation is not constrained by this and may
be redesigned during implementation, provided it maps losslessly to and from the required
external position names.

### Archive replacement and backup

Replacing an existing dance through import requires one explicit user confirmation before the
write. The write itself is atomic via stage-then-swap. Before a replace-import overwrites a
dance, the previous version is preserved in a dedicated, timestamp-versioned backup location.
This is separate from and must not be confused with the existing top-level `/Archive` folder,
which holds old-system reference code, not dance backups.

### Incomplete-draft confirmation

A dance transitions to an explicitly incomplete/draft state (see Scenario 8) only when it
contains unresolved references. The user confirms this transition once, at the moment it first
occurs. Subsequent saves while the dance remains incomplete do not re-prompt for confirmation.
The GUI must keep the incomplete status visibly marked at all times regardless of prompting.

### Concurrency and revisions

The first release includes optimistic concurrency. Every dance document carries a revision
identifier (ETag-style). Apply and Save operations must include the revision they were based
on; if it no longer matches the current document, the operation is rejected as a structured
conflict rather than silently overwriting concurrent changes. This applies even though the
first release is desktop-only and single-user-oriented, because it is inexpensive to implement
now and prevents silent data loss across tabs or sessions.

### Addon-combination validators

Addon-combination validation logic is co-located with each figure's own definition and
capability metadata, not centralized in a separate registry and not left solely to incidental
rejection during execution. Each figure's capability data supplies both its list of
individually valid addons (already decided in Scenario 6) and, where the figure requires it,
its own combination validator.

Each figure has an independent positive-integer `CapabilityVersion`, defaulting to `1` for
legacy definitions and incremented when its capability or validation behavior changes.
Combination rules are declarative `AddonCombinationValidator.allowedCombinations` lists in
the figure definition. Each allowed combination is an unordered set; the engine preserves the
submitted selection order, rejects duplicate addon selections, and validates combinations
without rewriting the user's selection.

Version 3 composite occurrences currently have no capability metadata for outer addon
selections. Until that metadata and execution behavior are defined, non-empty addon selections
on a composite occurrence are unsupported; addons on embedded atomic occurrences remain
independently validated.

## Scenario 1: Inspect and Preview a Single Figure

### User intent

The user browses the figure catalog, selects one figure, and wants to understand what it
does before placing it in a dance.

### Initial state

- No dance is being edited, or the user is in figure-inspection mode.
- The figure catalog contains a resolvable figure definition.
- The engine can construct a standard set large enough for the figure's active dancers.

### Expected interaction

1. The user selects a figure card.
2. The GUI loads the complete figure definition.
3. The GUI displays the figure's name, description, bars, positions, addons, and cript data.
4. The GUI shows incoming and outgoing dancefloor diagrams in the inspector's floor snapshot
   area.
5. The incoming preview responds to the anchor and supported addon selections; the outgoing
   preview reflects the same temporary parameters.
6. The GUI distinguishes definition data from preview/execution data.

### Engine result

The engine must be able to:

- resolve the figure definition;
- validate its structure and supported parameters;
- create the smallest standard set that accommodates the figure's active dancers;
- execute the figure without mutating the stored definition;
- return incoming and outgoing floors containing only active dancers;
- report invalid setup or execution conflicts in structured form.

For catalog previews, the incoming floor uses the figure's effective starting positions and
facing after anchor and addon application. The outgoing floor uses its effective ending positions
and facing. If a dancer has no defined facing, they face the opposite place in their couple
(for example, `1m` faces `1w`). Addons that modify starting positions or facing affect the
incoming floor; addons that modify ending positions or facing affect the outgoing floor.

### Occurrence boundary

At this stage the preview may use a temporary occurrence context. Once the figure is inserted
into a dance, it receives a stable occurrence ID and its floor state is calculated from the
dance execution trace instead of from an isolated preview.

### Resolved product decisions

- Selecting a catalog figure shows its definition and incoming/outgoing dancefloor diagrams
  immediately in the inspector's floor snapshot area.
- Preview controls may change supported parameters without modifying the stored figure or any
  dance.
- Preview changes become persistent only when the figure is inserted into a dance and the
  resulting dance is saved.
- The isolated preview uses the smallest standard set that accommodates the figure's active
  dancers; only those active dancers are drawn.
- The anchor and addon controls update the temporary preview without changing the stored figure
  or a dance. The preview does not expose a separate couple-count control.

## Scenario 2: Execute and Inspect a Two-Figure Series

### User intent

The user creates or opens a dance containing figure A followed by figure B, then selects each
figure to understand how the first movement affects the second.

### Expected behavior

- The tree displays both figure occurrences in order inside a series group.
- Selecting figure A shows its incoming floor and its outgoing floor.
- Selecting figure B shows the outgoing floor of A as its incoming floor and its own resulting
  floor as its outgoing floor.
- Selecting the same figure definition in another occurrence does not reuse A's snapshots.
- The engine calculates the sequence once and exposes occurrence-specific trace records.

### Resolved product decision

The GUI shows incoming and outgoing states for the selected figure. Intermediate states are
not additional timeline nodes; each figure occurrence in the tree is itself selectable.

### Group selection decision

Selecting a series group shows:

- the group's incoming floor;
- the group's outgoing floor;
- the group's total bar range; and
- a summary of its child occurrences.

The GUI does not automatically replace the selection with the first child.

## Scenario 3: Inspect a Parallel Group

### User intent

The user selects a parallel group to understand what several figures do simultaneously and
which result is passed to the next part of the dance.

### Engine semantics

- The parallel group has one incoming floor.
- Every child receives the same incoming floor.
- Children execute independently.
- The child results are combined deterministically.
- A successful combination produces one outgoing floor for the group.
- A conflicting combination produces a structured conflict result and no partial group result.

### Expected normal GUI behavior

The selected parallel group should show its incoming floor, outgoing floor, total bar range,
and child summary. A child occurrence can be selected to inspect its own incoming and outgoing
state, while retaining the group's parallel context.

### Conflict behavior

The GUI must identify:

- the affected floor position;
- the competing writes;
- the responsible child occurrence IDs;
- the parallel group containing the conflict.

The user should be able to jump to an affected child and edit its parameters without losing
the rest of the dance.

### Resolved inspection decision

Selecting a child inside a parallel group shows that child's own incoming floor and isolated
outgoing result. The combined outgoing floor is shown only on the parallel group node.

### Resolved conflict decision

When combination fails, the GUI keeps the last valid floor state visible and displays a
prominent conflict panel. The panel identifies affected positions, competing writes, child
occurrences, and navigation targets for correction. No partial parallel result is presented
as valid.

## Scenario 4: Nested Series Containing a Parallel Group

### User intent

The user inspects a dance shaped like:

```text
Series
├─ Figure A
├─ Parallel
│  ├─ Figure B
│  └─ Figure C
└─ Figure D
```

The user needs to understand both the overall choreography and the exact context of every
occurrence.

### Expected execution order

- Figure A executes first.
- Figures B and C receive the floor produced by A.
- B and C execute independently.
- The parallel group combines their results.
- Figure D receives the combined result.

### Expected trace

Every node has a stable occurrence path, parent group identity, bar range, incoming floor,
outgoing floor, and execution status. The nested path must distinguish B and C from any other
occurrence of the same figure elsewhere in the dance.

### Expected group behavior

- The outer series shows its complete incoming and outgoing floor.
- The nested parallel group shows its incoming and combined outgoing floor.
- Figure B and Figure C show their own isolated child results.
- Figure D shows the combined parallel result as its incoming floor.

### Resolved bar-duration rule

Bar ranges are calculated from execution duration:

- series duration is the sum of its child durations;
- every path in a parallel group must have the same duration;
- a valid parallel group's duration is that shared path duration.

A parallel group is therefore not valid merely because one path is the longest. The engine must
detect unequal parallel-path durations and report them as a structural validation error.

If parallel paths have unequal durations, the engine rejects the group. The user must add an
explicit wait/padding operation to the shorter path before the group can execute or be saved.

## Scenario 5: Repeated Figure with Different Anchors

### User intent

The user places the same figure definition more than once in a dance, with different anchors,
and needs to distinguish the occurrences while inspecting their contextual states.

### Resolved identity decision

Occurrences share the figure definition's name but remain distinct through their stable
occurrence IDs, tree paths, anchors, bar ranges, and execution snapshots. The tree displays
the shared figure name together with occurrence-specific anchor and bar data. Custom labels are
not required for identity.

### Engine consequence

The execution trace must never key snapshots only by figure name. It must key them by occurrence
identity, so repeated references can have different incoming floors, outgoing floors, and
validation results.

## Scenario 6: Figure with Addons

### User intent

The user selects a figure that supports addons, chooses an addon for a placed occurrence or
preview, and wants the engine to execute the exact supported variant.

### Resolved addon decision

The engine is the sole source of addon capabilities. It provides the list of valid addons for
each figure. The GUI displays and allows selection only from that engine-provided list; it must
not invent, accept, or infer arbitrary addon names.

The engine remains authoritative when validating preview, edit, import, and save requests. A
request containing an addon not supplied for that figure is invalid and must identify the
figure, occurrence, and parameter path in its structured error.

### Occurrence consequence

An addon selection belongs to the figure occurrence or temporary preview context, not to the
shared figure definition. Two occurrences of the same figure may therefore use different valid
addons.

### Addon-combination decision

The GUI may combine any addons that are individually listed as valid for the figure. The
engine validates the resulting combination during preview or execution because combination
validity may depend on execution context that cannot be determined from the individual addon
list alone.

The GUI must present a failed combination as a validation result and must not persist or treat
it as executable until the engine accepts it.

If combination validation fails, the GUI keeps the selected addon values, marks the occurrence
invalid, and lets the user correct them. It must not silently remove or replace the user's
selection.

## Scenario 7: Add and Reorder Figures in the Dance Tree

### User intent

The user drags a figure from the catalog into a dance tree, places it at a specific position,
and reorders existing occurrences without editing JSON manually.

### Required behavior

- Dropping a catalog figure creates a new occurrence, not a new figure definition.
- Dropping a Version 3 composite creates a `CompositeOccurrence` with its recursively resolved
  groups and children embedded in the canonical tree. The inserted wrapper and embedded nodes
  receive fresh stable IDs; unresolved nested references are preserved and mark the candidate
  incomplete.
- The drop location determines the target parent and sibling order.
- The GUI updates the tree immediately only after the engine accepts the proposed edit.
- The engine validates the resulting structure and relevant execution semantics.
- A failed edit leaves the previous valid tree and floor trace unchanged.
- The user receives a specific reason when a drop is not allowed.

### Initial editing scope

The first editor should support:

- inserting a figure into a series;
- reordering siblings within a series;
- deleting an occurrence;
- editing occurrence anchor and addons;
- saving a validated tree.

Moving occurrences into or out of parallel groups, changing group types, and moving complete
groups should follow once their validation and timing semantics are explicitly defined.

### Resolved edit-application decision

Dragging creates a proposed tree change. The GUI displays the proposed structure and offers
Apply and Cancel. Apply sends the edit to the engine; the engine validates and commits it only
if valid. Cancel discards the proposal. Rejected edits leave the current tree and execution
trace unchanged.

The proposal view shows the changed tree structure but does not calculate or display a new
floor trace. The engine recalculates floor states only after the proposal is applied and
accepted.

When a proposal is rejected, the GUI shows the first blocking error prominently and provides
the complete validation report in a detailed view.

## Scenario 8: Unresolved Figure Reference

### User intent

The user opens a dance containing a figure reference that cannot currently be resolved from
the available figure catalog.

### Required behavior

- The tree preserves the unresolved occurrence and its original reference.
- The GUI marks the occurrence as unresolved and identifies the missing reference.
- The engine does not execute the unresolved occurrence.
- The user can inspect the rest of the dance and its valid occurrences where possible.
- Saving behavior must be explicit and must not silently discard or rewrite the unresolved node.

### Resolved persistence decision

A dance with unresolved references may be saved as an explicitly incomplete draft after
confirmation. It is not executable while unresolved. The unresolved reference remains intact,
and the GUI clearly marks the draft status and blocking issue.

## Scenario 9: Save and Export a Dance

### User intent

The user edits a dance and either saves the work in the current project or transfers the
dance to another session or installation.

### Resolved operation boundary

**Save** persists the validated or explicitly incomplete dance tree in the current project.
It preserves the semantic tree structure, figure references, occurrence parameters, metadata,
and draft status.

**Export** creates a portable package. The package contains the dance plus the referenced
figure definitions needed to reconstruct it in another session. Export is not merely a dump of
the current GUI tree or a list of file paths.

The package must preserve:

- dance metadata;
- recursive series and parallel structure;
- figure references and definitions;
- occurrence anchors and addons;
- schema/format version;
- incomplete-draft and unresolved-reference status where applicable.

The portable format is a single archive package. It may contain the dance document, referenced
figure definitions, package metadata, thumbnails, and future transfer assets without requiring
the user to manage several files.

### Import behavior

Import validates the complete archive before writing anything. Dance names are unique without
case sensitivity. If the dance name already exists, the user may either create a new copy under
a caller-provided unique name or replace the existing dance. Copy imports do not invent a name
or suffix. Replacement requires explicit confirmation and is transactional: a failed import
cannot partially modify the existing dance.

An archive that is internally inconsistent is rejected before import. This includes malformed
structure, invalid versions, missing required package members, unresolved references that the
package claims to provide, and invalid occurrence parameters. No partial dance is created or
replaced.

An intentionally incomplete draft may be exported and imported when the package explicitly
declares its incomplete status and preserves each unresolved reference. Such a package is
non-executable after import and remains visibly incomplete. It must not be confused with a
complete package that fails validation.

On import, the package's referenced figure definitions remain in a per-dance namespace and are
resolved for that dance without replacing or mutating the shared figure catalog. This preserves
the imported dance's exact definitions and prevents same-reference collisions from changing
other dances.

### Import validation feedback

Import errors must identify both the package location and the semantic tree path whenever
possible. For example:

```text
archive: figures/H1DR.json
tree path: children[1].children[0]
field: addons
error: addon is not supported by the packaged figure definition
```

Validation should report the first blocking error prominently and provide the complete report
for inspection. Import must not write any content before validation completes.

### Package versioning decision

Until the first distributed release, import accepts only the current package format. Older,
unknown, or newer package versions are rejected clearly rather than interpreted heuristically.

After the first distributed release, explicit migrations may be added for known older versions.
Unknown and newer versions remain rejected until a compatible application version is available.

## Scenario 10: Playback and Bar Scrubbing

### User intent

The user wants to step through a dance and inspect how the floor changes over time.

### Resolved playback decision

The first playback version uses discrete, deterministic states:

- initial dancefloor;
- figure occurrence boundaries;
- group boundaries;
- bar positions when snapshots are available.

The user can step forward and backward and scrub to a figure or bar state. Continuous
interpolation between positions is deferred until the discrete execution and snapshot model is
stable.

Playback consumes engine-produced trace data. The renderer does not independently execute
figures or infer intermediate states.

The first playback milestone exposes the initial floor and figure/group boundaries. Per-bar
scrubbing is added only when the engine provides authoritative per-bar snapshots; the GUI must
not fabricate intermediate states by repeating a nearest known snapshot.

## Scenario 11: Undo and Redo Editing

### User intent

The user wants to experiment with tree structure, anchors, and addons without fear of losing a
valid dance.

### Resolved history decision

Undo and redo are included in the first editor for accepted semantic edits, including:

- insertion;
- deletion;
- reordering;
- anchor changes;
- addon changes;
- supported group edits.

Uncommitted proposals do not enter history. Apply creates one history entry only after the
engine accepts the edit and recalculates the execution trace. Undo and redo restore the
semantic dance model and its corresponding trace, not only the visible GUI tree.

### Parallel editing decision

The editor supports building parallel groups and moving figures into or out of them. A
proposal may temporarily violate timing, reference, or conflict rules. Validation occurs when
the user selects Apply. If validation fails, the proposal is rejected and the previous semantic
model and execution trace remain unchanged.

When an occurrence moves into a different group, its existing anchor is preserved initially.
The engine validates that anchor in the new context during Apply. If it is invalid or causes a
conflict, the proposal is rejected with an actionable error and the user may edit the anchor
before applying again.

The first editor allows creation of new series and parallel groups, but does not convert an
existing group from series to parallel or vice versa. Existing group types remain stable until
explicit conversion semantics are defined.

## Scenario 12: Dancefloor Rendering

### User intent

The user needs to understand the spatial result of a figure or group without interpreting raw
engine data.

### Resolved renderer decision

The first renderer displays:

- a 2D dancefloor;
- dancer identity;
- couple information;
- coordinates;
- facing direction;
- the selected occurrence or group context.

Movement vectors, continuous animation, and decorative visualization are deferred until the
static state renderer is reliable. The renderer consumes the stable floor-state contract and
does not calculate positions itself.

### Initial layout decision

The first GUI is desktop-only while the editor workflow stabilizes. Responsive tablet and
mobile layouts are deferred and must not complicate the initial interaction model.

Video rendering and asynchronous render jobs are deferred until the core editor, execution
inspection, and export workflow are stable. They are presentation features, not prerequisites
for the canonical dance or execution model.

### Performance decision

The first implementation may use simple, explicit caching for stable figure definitions,
dance metadata, and read-only tree data. Cache invalidation must be understandable and must not
return stale results after an accepted edit.

Virtualized lists, virtualized trees, aggressive prefetching, and load optimization are
deferred until measured data demonstrates a need.

## First-Release Scope

The first release should provide a reliable desktop editor and execution inspector with:

- engine-provided figure catalog and addon capabilities;
- figure details and isolated preview using configurable project defaults;
- recursive dance tree with stable occurrence identities;
- creation of series and parallel groups;
- insertion, deletion, reordering, and movement of occurrences;
- anchor and addon editing;
- proposal-based edits with Apply/Cancel;
- validation on Apply;
- undo/redo for accepted edits;
- execution trace with incoming/outgoing occurrence and group states;
- equal-duration validation for parallel paths;
- structured conflict reporting;
- 2D static floor rendering with dancer identity, couples, coordinates, and facing;
- figure/group-boundary playback;
- saving validated dances;
- saving explicitly incomplete drafts;
- portable archive export/import;
- strict current-format package validation;
- simple correctness-first caching.

## Explicitly Deferred

The following are not first-release requirements:

- automatic migration of old package formats before the first distributed version;
- continuous movement interpolation and animation;
- per-bar playback when authoritative per-bar snapshots are unavailable;
- conversion of existing groups between series and parallel;
- custom occurrence labels;
- virtualized lists or trees;
- responsive tablet/mobile editing;
- video rendering and asynchronous render jobs;
- PDF and advanced presentation export;
- aggressive performance optimization and prefetching.

## Engine-First Implementation Sequence

1. Define the canonical occurrence-aware dance model.
2. Define figure capability metadata, including engine-provided addon lists.
3. Implement deterministic series and parallel execution.
4. Enforce equal parallel-path durations.
5. Produce occurrence and group execution traces with incoming/outgoing floors.
6. Implement structured validation and conflict reports.
7. Implement validated semantic edit commands and history.
8. Define and validate the current portable archive format.
9. Expose stable API read/write models for the GUI.
10. Build the desktop tree editor and static renderer on those contracts.
