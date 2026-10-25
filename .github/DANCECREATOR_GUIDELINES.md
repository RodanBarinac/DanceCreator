# DanceCreator repository guidelines

## Working directory and Python

- Work from the project root: `E:\Git\DanceCreator`. Relative paths for `Dances/` and
  `Figures/` depend on this.
- Always use `.\.venv\Scripts\python.exe` for Python. Do not use `python`, `python3`, or
  `python.exe`.
- Run tests with `.\.venv\Scripts\python.exe -m pytest <target> -v`.

## Project structure

- `tests/` contains pytest tests.
- `Dances/` and `Figures/` contain the current dance and figure data.
- `Archive/` is reference-only. Its contents are not expected to load or run.
- `.venv/` is the repository's Python virtual environment.
- `Experimental/` contains an unaccepted refactor; do not use it without tests showing it
  works better than the current implementation.

## Test-driven development

Write focused tests before implementation, use descriptive `test_*.py` names for Python
tests, and run the narrowest relevant suite while iterating. Use pytest for Python tests and
the existing Jest setup for frontend unit tests. Run the broader relevant suites when a
change crosses subsystem boundaries.

## Architecture and product decisions

- For first-release product behavior, follow `Documents/GUI_ENGINE_STRATEGY.md`.
- For implementation stages, file boundaries, and acceptance criteria, follow
  `Documents/IMPLEMENTATION_OUTLINE.md`.
- The canonical semantic dance model is the source of truth; GUI trees and diagrams are
  projections. Do not persist renderer state or calculated floor snapshots.
- Preserve stable figure-occurrence identity. Parallel branches share an incoming floor and
  produce isolated results; paths must have equal duration, and failed combinations must not
  yield a valid partial result.
- Invalid proposals must not replace the current model or execution trace. Add-on options
  come from the engine, and add-on combinations are validated by the engine.
- Incomplete drafts may be saved or transferred only when explicitly marked incomplete.
  Reject internally inconsistent complete packages transactionally.
- Do not prioritize deferred features unless the user explicitly changes scope.

## Dancefloor diagrams

Use the established literature orientation: the top of the set (row 1) is on the left;
the ladies' side (column 3) is at the top, and the men's side (column 1) is at the bottom.
Floor positions and facing targets are row-column coordinates. Facing points toward the
absolute target coordinate, not a direction vector.

## Compatibility and data safety

There is no production release, so strict backward compatibility is not required. Breaking
design decisions are acceptable when they simplify the codebase; do not add legacy shims.
Update applicable examples, tests, and documentation, and call out breaking changes in
`CHANGELOG.md` and examples when relevant.

Do not overwrite or delete user data without explicit confirmation. Import/export writes must
be transactional, and proposed edits must be validated before replacing the current model.
Preserve the last valid dance tree and execution trace when validation fails.
