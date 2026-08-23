# Versioning Guide

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23

This project uses **Semantic Versioning** (SemVer) as defined at [semver.org](https://semver.org/).

## Version Format

```
MAJOR.MINOR.PATCH
  1  .  2  .  3
```

### Definition
- **MAJOR** - Increment when making incompatible changes to the API
- **MINOR** - Increment when adding functionality in a backwards-compatible manner
- **PATCH** - Increment when making backwards-compatible bug fixes

## Current Version

**0.1.0** - Initial Release

See `VERSION` file in project root for the current version.

## Release Process

### Step 1: Update CHANGELOG
Edit `CHANGELOG.md`:
- Move items from `[Unreleased]` to a new version section
- Add date in format `YYYY-MM-DD`
- List changes under: Added, Changed, Deprecated, Removed, Fixed, Security

**Example:**
```markdown
## [0.2.0] - 2026-09-01

### Added
- New feature X
- New feature Y

### Fixed
- Bug fix for issue #123
```

### Step 2: Update VERSION File
Edit `VERSION` and set to new version:
```bash
echo "0.2.0" > VERSION
```

### Step 3: Update pyproject.toml
Update the `version` field:
```toml
[project]
version = "0.2.0"
```

### Step 4: Create Git Tag
```bash
git add VERSION CHANGELOG.md pyproject.toml
git commit -m "Release version 0.2.0"
git tag v0.2.0
git push origin master
git push origin v0.2.0
```

### Step 5: Create GitHub Release
- Go to GitHub repository Releases
- Click "Draft a new release"
- Select the tag created in Step 4
- Copy the CHANGELOG section as release notes
- Publish

## Viewing Version History

### View all releases
```bash
git tag -l
```

### View specific release
```bash
git show v0.2.0
```

### View CHANGELOG
```bash
cat CHANGELOG.md
```

## Version Bump Decision Tree

```
Did you make incompatible API changes?
  ├─ YES → Increment MAJOR (e.g., 1.0.0 → 2.0.0)
  └─ NO
      Did you add new backwards-compatible features?
      ├─ YES → Increment MINOR (e.g., 1.0.0 → 1.1.0)
      └─ NO
          Did you fix bugs?
          ├─ YES → Increment PATCH (e.g., 1.0.0 → 1.0.1)
          └─ NO → No release needed
```

## Files Involved in Versioning

| File | Purpose |
|------|---------|
| `VERSION` | Single source of truth for current version |
| `pyproject.toml` | Python package metadata and version |
| `CHANGELOG.md` | Human-readable change history |
| `git tags` | Immutable release markers |

## Next Release Plan

Current version: **0.1.0**

When ready for next release:
1. Ensure all tests pass: `.\.venv\Scripts\python.exe -m pytest tests/ -v`
2. Follow the release process above
3. Document breaking changes clearly in CHANGELOG

## Questions?

Refer to:
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) - Changelog format standard
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html) - Version numbering spec
- `CHANGELOG.md` - This project's change history
