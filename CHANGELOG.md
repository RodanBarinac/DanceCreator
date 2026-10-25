# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dance-figure inspector now shows the incoming floor from the execution trace and, when the anchor or add-ons change, refreshes the outgoing floor and instruction list through a debounced (250 ms) `POST /api/dances/<dance-id>/nodes/<node-id>/preview` call. Stale responses are ignored (latest request wins); catalog selections are unchanged.
- Failed dance-node and catalog previews retain and dim the last valid outgoing floor, show the backend error above it, and mark affected dancers and instruction lines; Apply stays disabled until the matching node preview succeeds. Start-position errors map by floor order, while selected dancers retain their selection stroke.

### Changed
- Replaced the inspector's propose-anchor, propose-add-ons, Apply and Cancel buttons with a single Apply button in the inspector's upper right. It is disabled for catalog figures and enabled for a dance figure only while the anchor/add-ons differ from its current values; clicking it creates the proposal and applies it as one step. Selecting another figure silently discards pending edits.
- Kept incoming and outgoing inspector dancefloor previews side by side at equal widths and aspect ratios, including during inspector resizing.
- Moved the Instructions list to the full inspector width below the preview status and above both dancefloor snapshots; catalog and dance-node highlighting behavior is unchanged.

### Removed
- Retired `tests/Test_Comparison.py`; its legacy Archive comparison fails collection because `Archive/Dance.py` imports `SimpleFigure`.

### Breaking Changes

- **Preview dancer identity and facing (C18, C19, Q8, decided Q1c):** `StartDancers` and `StartFacing` are optional per-`StartPos` declarations. Empty/missing dancer IDs use automatic preview allocation; identifiers are format-checked and unique after allocation. Empty/missing facing entries use the same-row opposite-line target. Both declarations affect isolated catalog preview only. The H1DR pilot declares `2m, 1w, 1m, 3w` with its incoming facing targets; within dances actual floor dancer identity and facing are preserved.
- **Figure data/facing contract:** only `data/Figures/` and `data/Dances/` (including `data/Dances/subDances/`) are canonical; root-level folders and fallback loading are removed. Figure/addon `Faceing` is renamed to `EndFacing` with no shim; `Facing` alone is not a key/property. Optional `StartFacing` and `StartDancers` declarations are available for isolated previews only; dance execution ignores them for incoming facing and dancer naming.
- **Centered dance-floor coordinates:** columns now use `-1` for the men's line, `0` for the centre, and `+1` for the ladies' line; rows remain 1-based. Figure offsets and dance anchors were migrated, and old-coordinate compatibility shims were not added. Default facing targets the same row on the opposite side of the centre line (for example `[2,-1]` faces `[2,1]`); facing values remain target positions, not vectors.
- **Figure composition/addons:** removed the duplicate `1cLT1c` figure. The engine-reserved `B<n>` addon (positive integer) sets bars on any simple figure without a figure-file definition and may shorten or lengthen it; it changes bars only. `E1c` changes `1cLT` end positions, end facing, and ending text, but not bars. Conflicts on the same field/dancer and multiple duration addons are errors. Two half reels with `B3` each make a six-bar reel; no separate 6- or 8-bar reel figures are added.
- **Half-reel preview catalog data:** declared `StartDancers` and the requested `StartFacing` targets for H2DR and all four half-reel figures, and corrected the four reel `Name` fields to match their filenames.

### Fixed
- Numbered file backups with monotonically increasing per-file counters and prune by counter, preserving the newest five even when timestamps collide.
- Rotated square and fallback-diamond dancer shapes with their facing arrows, and removed the incoming and outgoing catalog-preview labels that overlapped the Ladies heading.
- Corrected the second dancer's `1cLT` starting/ending/partner offsets and enabled addon instruction-text replacement.

### Added
- **Read-only inspector previews (Q10):** added `POST /api/dances/<dance-id>/nodes/<node-id>/preview`, using trace incoming floors and proposed anchor/addons without applying edits; preview and rejected-proposal errors expose affected dancers and have shared/request/response schemas.
- **Structured crips (Q9):** added a non-printing engine data function that returns figure reference, dancer, inclusive bar range and instruction text without a repeated leading dancer name; position references use possessive wording. Preview responses use the generated incoming floor; dance detail/trace responses use each node's traced incoming floor. Duration addons and serial/parallel timing are reflected, and API schemas/contracts document the response.
- **Crips inspector (Q9):** renders structured instruction lines beside the incoming floor for catalog previews and selected dance occurrences. Selecting a line highlights its dancer; selecting an incoming-floor dancer selects its line.
- **Full API Surface Implementation** (2026-08-31)
  - Figure List API (`GET /api/figures`) with filtering, pagination, and sorting
  - Dance List API (`GET /api/dances`) with metadata (EstimatedBars, Couples)
  - Dance Tree API (`GET /api/dances/<id>/tree`) with jsTree-compatible output
  - Request validators for all query parameters (formation, bars, couples, search, pagination)
  - Response validators using jsonschema for all endpoints
  - Comprehensive test suite (68 new tests, all passing)
  - Schema validation for API contracts (`/schema/*.json`)
  - Recursion protection in tree building (max depth: 50 levels)
  - API Quick Reference documentation (`Documents/API_QUICK_REFERENCE.md`)
- **Dance Write API Documentation** (2026-09-27)
  - Documented dance write endpoints: `POST /api/dances`, `PUT /api/dances/<id>`, `PUT /api/dances/<id>/tree`, and `DELETE /api/dances/<id>`
  - Documented schema validation, automatic `.bak` backups, jsTree-to-`FigureList` conversion, and soft delete behavior in `data\Dances\.deleted\`
  - Read-only APIs unchanged and fully backward compatible
- TDD (Test-Driven Development) workflow established
- Test suite with 6 passing core tests
- Comprehensive documentation in `/Documents/`
- Project organization (tests, experimental code)
- `.github/copilot-instructions.md` for AI agent guidelines

### Changed
- **Breaking: API Response Format Changes**
  - All list endpoints now return structured responses with `status`, `version`, `timestamp`, `count`, `total`, `offset`, `limit`, and `filters_applied`
  - Dance tree endpoint returns metadata envelope instead of raw tree
  - Figure and dance summaries include required `Version` field
  - Dance summaries include calculated `EstimatedBars` and `Couples` metadata
- Dancefloor endpoints now validate responses against contract schema
- Switched from experimental new system to proven old system (Archive)
- Reorganized project structure for clarity

### Fixed
- API endpoints now properly handle pagination, filtering, and sorting
- Tree builder now prevents infinite recursion with circular references
- Query parameter validation prevents invalid inputs

### Deprecated
- Experimental refactored system (moved to `/Experimental/`)

### Testing
- Fixed `npm run test:unit` for Jest ES modules on Windows by enabling Node VM modules without extra dependencies.
- Replaced the obsolete static-page browser check with a local Flask + Playwright test of the current catalog preview and dancer-facing rotation.
- 68 new API tests passing
- Schema validation tests for all endpoint responses
- Request validation tests for error handling
- End-to-end tests for dancefloor execution

## [0.1.0] - 2026-08-23

### Initial Release
- DanceCreator with Dance, DanceFloor, and Figure classes
- Support for Scottish Country Dancing choreography
- Flask web application for dance visualization
- Dance and Figure JSON-based configuration
- Core functionality:
  - Load dances and figures from JSON
  - Execute dance moves on a dance floor
  - Display dancer positions and movements
  - Generate "crips" (crisp descriptions of moves)

### Known Issues
- Some API endpoints returning 404 (routes need verification)
- Conflict detection in parallel moves not yet implemented
- Figure data format inconsistencies between old and new system

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
  - **MAJOR** - Breaking changes to core functionality
  - **MINOR** - New features (backwards compatible)
  - **PATCH** - Bug fixes

## How to Create a Release

1. Update this CHANGELOG with new version and date
2. Create a git tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
3. Create a GitHub Release with release notes

## Release History

| Version | Date | Status |
|---------|------|--------|
| [0.1.0](#010---2026-08-23) | 2026-08-23 | Initial Release |
| [Unreleased](#unreleased) | - | In Development |
