# Copilot Session Instructions for DanceCreator

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23

## Critical: Python Executable
**ALWAYS use `.\.venv\Scripts\python.exe` for this repository.**

DO NOT use:
- `python`
- `python3`
- `python.exe`

This repo has a virtual environment at `.venv` and all work must use its Python executable.

### Examples:
```bash
# Correct
.\.venv\Scripts\python.exe -m pytest tests/ -v
.\.venv\Scripts\python.exe tests/test_new_system_only.py
.\.venv\Scripts\python.exe script.py

# Wrong - do not use these
python -m pytest tests/ -v
python3 script.py
python.exe tests/test_new_system_only.py
```

## Working Directory
Always work from the project root: `e:\Git\DanceCreator`

Relative paths for `Dances/` and `Figures/` depend on this.

## Key Directories
- `/tests` - pytest test files
- `/Dances` - Dance JSON files
- `/Figures` - Figure JSON files
- `/Archive` - Old system for comparison
- `/.venv` - Virtual environment with dependencies

## Test-Driven Development (TDD)

This project uses **Test-Driven Development**. Follow these principles:

### TDD Workflow
1. **Write the test first** - Define what you want to build with a failing test
2. **Make it pass** - Write minimal code to make the test pass
3. **Refactor** - Improve the code while keeping tests passing

### When Writing Code
- ✅ **Always write tests BEFORE implementation**
- ✅ **Run tests frequently** to ensure nothing breaks
- ✅ **Keep tests focused** - one assertion per test when possible
- ✅ **Use descriptive test names** - `test_dance_move_updates_floor` not `test_1`

### Testing Standards
- Test location: `/tests/` directory
- Test framework: **pytest**
- Naming convention: `test_*.py` files
- Run tests with: `.\.venv\Scripts\python.exe -m pytest tests/ -v`

### Before Any Implementation
Ask yourself:
1. What should this code do?
2. How will I test it?
3. What's the minimal code to pass the test?

### Current Test Files
- `test_dance.py` - Dance and Figure functionality
- `test_api.py` - Flask API endpoints
- `test_combine_conflict.py` - DanceFloor conflict resolution
- `test_new_system_only.py` - Demo of new system features
- `test_archive_old_system.py` - Comparison with old system

### Experimental Code
The `/Experimental/` folder contains the refactored new system that did not pass TDD review. Do not use without tests demonstrating it works better than the current system.

### More Information
- See `tests/README_HOW_TO_TEST.md` for detailed test running instructions
