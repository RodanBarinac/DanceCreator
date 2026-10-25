# How to Use Tests in DanceCreator

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-10-25

## Overview
The `/tests` directory contains **pytest-based tests** for the DanceCreator project.

## Test Files

| File | Purpose |
|------|---------|
| `test_dance.py` | Tests core Dance and Figure functionality |
| `test_api.py` | Tests Flask API endpoints |
| `test_frontend.py` | Tests GUI/frontend functionality |
| `test_combine_conflict.py` | Tests DanceFloor conflict resolution |
| `test_new_system_only.py` | Simple demo: shows Crips and DanceFloor for one dance |

---

## Frontend interaction tests

The Jest unit suite covers structured crips rendering (with the dancer name shown once), catalog-preview and dance-occurrence instruction selection, and two-way highlighting between instruction lines and dancers on the incoming floor. It also verifies that failed dance-node and catalog previews preserve and dim the last valid outgoing floor, display the backend error above it, mark affected dancers and instruction lines by name/start-position index, disable Apply until a matching node preview succeeds, and clear the error markers after recovery. Run the unit suite with:

```cmd
npm.cmd run test:unit
```

## Running Tests

### 1. **Run ALL tests**
```bash
cd e:\Git\DanceCreator
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
- `-v` = verbose output (shows each test)

### 2. **Run a SPECIFIC test file**
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_dance.py -v
```

### 3. **Run a SPECIFIC test function**
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_dance.py::test_get_dance -v
```

### 4. **Run with detailed output**
```bash
.\.venv\Scripts\python.exe -m pytest tests/ -vv -s
```
- `-vv` = extra verbose
- `-s` = show print statements

### 5. **Run and stop at first failure**
```bash
.\.venv\Scripts\python.exe -m pytest tests/ -x
```

### 6. **Run only failed tests (after first run)**
```bash
.\.venv\Scripts\python.exe -m pytest tests/ --lf
```

---

## Demo/Exploration Scripts

### Simple Demo: Show Dance Output
This is NOT a test, just a demo script that shows the output:
```bash
.\.venv\Scripts\python.exe tests/test_new_system_only.py
```
Shows:
- Initial DanceFloor
- ShowCrips output
- Final DanceFloor after dance moves

---

## Understanding Test Output

### Successful test:
```
tests/test_dance.py::test_get_dance PASSED
```

### Failed test:
```
tests/test_dance.py::test_get_dance FAILED
AssertionError: assert None is not None
```

### Test Summary:
```
============ 3 passed, 1 failed in 0.42s ============
```

---

## Key Test Functions

### `test_dance.py`
```python
test_get_figure()        # Load a figure by name
test_get_dance()         # Load a dance by name
test_simple_move_no_error()  # Execute a figure move
```

### `test_api.py`
```python
test_figures()           # GET /api/figures
test_dance()             # GET /api/dances/<name>
test_init_floor()        # POST /api/dancefloor/init
```

---

## Quick Start Commands

| What you want | Command |
|---|---|
| Run all tests | `.\.venv\Scripts\python.exe -m pytest tests/ -v` |
| Check if tests pass | `.\.venv\Scripts\python.exe -m pytest tests/` |
| See which tests failed | `.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short` |
| Run only dance tests | `.\.venv\Scripts\python.exe -m pytest tests/test_dance.py -v` |
| Run only API tests | `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -v` |
| Demo new system | `.\.venv\Scripts\python.exe tests/test_new_system_only.py` |

---

## Common Issues

**Issue:** `ModuleNotFoundError: No module named 'pytest'`
- **Fix:** Install pytest: `.\.venv\Scripts\python.exe -m pip install pytest`

**Issue:** Tests can't find Figures/Dances
- **Fix:** Run tests from project root (`cd e:\Git\DanceCreator`)

**Issue:** Unicode errors in output
- **Fix:** Use `.\.venv\Scripts\python.exe` instead of plain `python`

---

## Writing Your Own Test

Create a new file `tests/test_myfeature.py`:

```python
import Dance
import DanceFloor as DF

def test_my_feature():
    # Arrange
    floor = DF.DanceFloor('test', 2)
    
    # Act
    dance = Dance.getDance('Marries Wedding_all')
    result = dance.DanceMove(floor)
    
    # Assert
    assert result is not None
    assert result.name == 'test'
```

Then run it:
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_myfeature.py -v
```

---

## Useful pytest Options

```bash
-v          Verbose
-vv         Extra verbose
-s          Show print statements
-x          Stop at first failure
-k "pattern" Run only tests matching pattern
--tb=short  Shorter error tracebacks
--tb=long   Longer error tracebacks
--lf        Run last failed tests
```

Example:
```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v -k "dance" --tb=short
```


## JavaScript and browser integration tests

Run both JavaScript suites from the repository root with:

```bash
npm test
```

`npm test` runs Jest unit tests and then a Playwright integration test of the current `templates/index.html` UI. The browser test starts the real Flask application with `\.venv\Scripts\python.exe` (on Windows), selects the H1DR catalog figure, and checks that the incoming-floor SVG contains a circle and a rotated woman shape whose transform matches its facing arrow. The browser is restricted to requests to the local Flask origin; no external network services or APIs are used.

The integration runner always closes the browser and terminates the Flask process in a `finally` block, including when startup or an assertion fails. Chromium must be available to Playwright. To run only the JavaScript tests:

```bash
npm run test:unit
npm run test:integration
```
