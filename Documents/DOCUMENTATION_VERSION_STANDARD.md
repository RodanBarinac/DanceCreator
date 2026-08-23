# Documentation Version Metadata Standard

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23

## Overview

All documentation must include version metadata to indicate which versions of DanceCreator they apply to. This ensures users and developers know if the documentation is current for their version.

## Version Metadata Format

Every document **must** include this header immediately after the title:

```markdown
# Document Title

> **Valid from version:** X.Y.Z  
> **End of validity:** X.Y.Z or (current)  
> **Last updated:** YYYY-MM-DD
```

### Field Definitions

| Field | Format | Example | Meaning |
|-------|--------|---------|---------|
| **Valid from version** | Semantic version or `-` | `0.1.0` | The first version this document applies to |
| **End of validity** | Semantic version, `(current)`, or `-` | `(current)` | The last version the doc is valid for; `(current)` = still valid |
| **Last updated** | ISO date (YYYY-MM-DD) | `2026-08-23` | When the document was last updated |

## Version Scenarios

### Active Documentation
Currently valid and regularly maintained:
```
Valid from version: 0.1.0
End of validity: (current)
```
**Meaning:** Valid from 0.1.0 through current releases.

### Obsolete Documentation
No longer valid after a specific version:
```
Valid from version: -
End of validity: 0.0.5
```
**Meaning:** Legacy documentation; not applicable to version 0.1.0+.

### Legacy Reference Documentation
Design or historical documents with no version scope:
```
Valid from version: -
End of validity: -
Status: LEGACY - Design reference document
```
**Meaning:** Reference material; not version-specific but archived.

### Version-Specific Documentation
Only valid for a specific version range:
```
Valid from version: 0.2.0
End of validity: 0.2.9
```
**Meaning:** Document applies only to 0.2.x releases.

## When to Update Version Metadata

### Update "Last updated" if:
- Content is changed
- Information is clarified
- Examples are added/corrected

### Update "End of validity" if:
- The document becomes obsolete
- Information is no longer applicable
- A replacement document is created

### Create new documentation if:
- Breaking changes affect how features work
- New features require new documentation
- Multiple versions need different instructions

## Examples

### Example 1: Current Testing Guide
```markdown
# Testing Guide

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23
```

### Example 2: Deprecated Feature Guide (ends at v0.5.9)
```markdown
# Old Figure Format (Deprecated)

> **Valid from version:** 0.1.0  
> **End of validity:** 0.5.9  
> **Last updated:** 2026-08-15
```

### Example 3: Legacy Design Document
```markdown
# Original System Design

> **Valid from version:** -  
> **End of validity:** -  
> **Status:** LEGACY - Architecture reference  
> **Last updated:** 2026-06-01
```

## Document Location

Version metadata must appear **immediately after the document title** (H1 heading):

✅ **Correct:**
```markdown
# Document Title

> **Valid from version:** 0.1.0
> **End of validity:** (current)
```

❌ **Incorrect:**
```markdown
# Document Title

Some text here...

> **Valid from version:** 0.1.0
```

## Version Check Template

When updating documentation for a new release, use this checklist:

- [ ] Does this document still apply to the new version?
- [ ] Does the content need any updates?
- [ ] Should "Last updated" date be changed?
- [ ] Should "End of validity" be set (if no longer current)?
- [ ] Are version numbers in examples still correct?
- [ ] Do code samples work with the new version?

## Viewing Documentation for Your Version

To find documentation valid for version X.Y.Z:

1. Check the "Valid from version" ≤ X.Y.Z
2. Check the "End of validity":
   - If "(current)" → document applies
   - If ≥ X.Y.Z → document applies
   - If < X.Y.Z → document is obsolete

## Questions?

- For version-specific issues, check version metadata first
- See `CHANGELOG.md` for breaking changes between versions
- See `VERSIONING_GUIDE.md` for release process
