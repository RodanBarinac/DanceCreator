# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TDD (Test-Driven Development) workflow established
- Test suite with 6 passing core tests
- Comprehensive documentation in `/Documents/`
- Project organization (tests, experimental code)
- `.github/copilot-instructions.md` for AI agent guidelines

### Changed
- Switched from experimental new system to proven old system (Archive)
- Reorganized project structure for clarity

### Deprecated
- Experimental refactored system (moved to `/Experimental/`)

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
