# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
  - Documented schema validation, automatic `.bak` backups, jsTree-to-`FigureList` conversion, and soft delete behavior in `Dances\.deleted\`
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
