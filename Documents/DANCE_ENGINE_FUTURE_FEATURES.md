# DanceCreator: Future Feature List

> **Valid from version:** -  
> **End of validity:** -  
> **Status:** PLANNING  
> **Last updated:** 2026-09-29

## Purpose

This document records user-facing functionality that is wanted but is not available as a
complete feature yet. It focuses on editing a dance through its tree, seeing the dancefloor
state at each figure, and transferring a dance tree between files and the application.

For the current engine and API behavior, see
[`DANCE_ENGINE_FLOW.md`](DANCE_ENGINE_FLOW.md).

## Feature List

### 1. Drag and drop figures in the dance tree

**Goal:** Let users build and edit a dance by dragging figures into, out of, and around the
dance tree.

**Expected behavior:**

- Drag a figure from the available-figures list into a valid location in the dance tree.
- Move a figure or group to a different location in the tree.
- Reorder siblings by dragging them before or after one another.
- Move a figure into or out of a series or parallel group where the target location permits it.
- Make the resulting order and group structure visible immediately in the tree.
- Save the edited dance and preserve figure references, group type, order, anchors, and addons.
- Give clear feedback when a drop is not allowed or saving fails.

The interaction should make it easy to place figures both **in** groups and **around** existing
tree entries without requiring users to edit the underlying JSON structure.

**Acceptance criteria:**

- A user can add a figure to a dance by dragging it from the figure list to the tree.
- A user can reorder figures and move them between valid groups using drag and drop.
- The tree's displayed structure and order reflect each successful drop.
- Saving and reopening the dance preserves the edited tree.
- Invalid drops and save errors are communicated without silently losing the user's edits.

### 2. Show the dancefloor state at each figure in the dance tree

**Goal:** When a user selects or steps through a figure in the dance tree, show the dancefloor
as it is immediately before that figure executes. This is the state left by the preceding figure
in the dance's execution flow.

**Expected behavior:**

- The starting floor is shown before the first figure.
- Selecting a figure shows the floor state immediately before that figure, after all preceding
  applicable figures have executed.
- The user can also view the selected figure's resulting floor state.
- Moving to another figure updates the displayed floor to that figure's incoming state.
- The selected tree occurrence and its bar range are identifiable in the UI.
- Repeated occurrences of the same figure definition show their own correct states.
- Nested series and parallel groups use the dance's execution order when determining the state
  shown at each figure.

The key behavior is contextual: a figure node does not show a generic or freshly initialized
floor. It shows the floor produced by the dance up to that occurrence.

**Acceptance criteria:**

- The first figure shows the configured starting floor as its incoming state.
- Each later figure shows the result of its preceding execution context as its incoming state.
- Selecting a figure can display both its incoming floor and its resulting floor.
- Two tree nodes referring to the same figure can display different floor states.
- The floor shown for every figure agrees with executing the dance in order.

### 3. Import and export a dance tree

**Goal:** Let users load a dance tree from a file and save or export the tree to a file.

**Expected behavior:**

- Export a selected dance/tree as a downloadable file.
- Import a tree file as a new dance or use it to replace the tree of an existing dance.
- Preserve the recursive structure and order of series (`"s"`) and parallel (`"p"`) groups,
  figure references, anchors, addons, and dance metadata needed to reconstruct the dance.
- Validate the imported content before saving; report invalid structures or unresolved figure
  references with actionable errors.
- Preview or confirm the target dance before replacing existing content.
- Ensure exporting then importing a valid dance produces an equivalent `FigureList` and
  executable choreography.

**Current distinction:** The API already supports retrieving a dance/tree and updating a dance
or tree through `GET` and `PUT` endpoints. Those operations are not the same as user-facing file
import/export: dedicated file download/upload, validation/preview UX, and a documented transfer
format are still needed.

**Acceptance criteria:**

- A user can export a dance and import it in a separate session to recreate an equivalent dance.
- Import validates the complete tree before writing and does not leave a partially updated dance
  after failure.
- The user can choose whether import creates a dance or replaces an existing one, with a clear
  confirmation before replacement.
- Validation feedback identifies the relevant tree path and problem.
- The selected transfer format and its versioning rules are documented.
