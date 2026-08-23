# DanceCreator Documentation Index

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23

Welcome to the DanceCreator documentation. All project documentation is organized here.

## Core Documentation

### 🚀 [COPILOT_INSTRUCTIONS.md](COPILOT_INSTRUCTIONS.md)
**Critical guidelines for Copilot agents working on this project**
- Python executable requirement (`.\.venv\Scripts\python.exe`)
- Working directory setup
- Test-Driven Development (TDD) workflow
- TDD best practices and standards

### 🧪 [TDD_READINESS_REPORT.md](TDD_READINESS_REPORT.md)
**Current test suite status and readiness assessment**
- All passing/disabled tests listed
- Test folder organization explained
- Next steps for TDD development
- Run commands for different test scenarios

### 📚 [TESTING_GUIDE.md](TESTING_GUIDE.md)
**Comprehensive testing guide for developers**
- How to run tests (all, specific files, specific functions)
- Test file descriptions
- Demo/exploration scripts
- Common issues and troubleshooting
- How to write your own tests

## Quick Start

### Setup
1. Use the Python in `.venv`: `.\.venv\Scripts\python.exe`
2. Always work from project root: `e:\Git\DanceCreator`
3. Read [COPILOT_INSTRUCTIONS.md](COPILOT_INSTRUCTIONS.md) first

### Documentation Version Compatibility

**All documentation includes version metadata:**
- **Valid from version:** First version this applies to
- **End of validity:** Last version it applies to (or current)
- **Last updated:** When the document was last updated

See [DOCUMENTATION_VERSION_STANDARD.md](DOCUMENTATION_VERSION_STANDARD.md) for details.

To find docs for your version, check the metadata at the top of each file.

### Running Tests
```bash
cd e:\Git\DanceCreator
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### TDD Workflow
1. **Write test first** - Define what you want to build
2. **Make it fail** - Ensure the test catches the missing feature
3. **Write minimal code** - Make the test pass with minimal implementation
4. **Refactor** - Improve while keeping tests passing

## Project Structure

```
/Documents/          ← All documentation (you are here)
/tests/              ← All test files and demos
/Experimental/       ← Refactored system (not used)
/Archive/            ← Old system versions for reference
/Dances/             ← Dance JSON files
/Figures/            ← Figure JSON files
ComplexFigure.py     ← Main system (active)
Dance.py
DanceFloor.py
...
```

## Key Decisions

- **Active System:** Old system from /Archive (proven working)
- **Test Framework:** pytest
- **Development Method:** Test-Driven Development (TDD)
- **Python Executable:** `.\.venv\Scripts\python.exe` (always)

## Additional Resources

- Project README: [../Readme.md](../Readme.md)
- GitHub Copilot Instructions: [../.github/copilot-instructions.md](../.github/copilot-instructions.md)
- Experimental Code: [../Experimental/](../Experimental/)

---

**Last Updated:** 2026-08-23

For questions about any documentation, refer to the specific file listed above.
