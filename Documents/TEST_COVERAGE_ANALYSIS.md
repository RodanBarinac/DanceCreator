# Test Coverage Analysis - Python Components

> **Valid from version:** 0.1.0  
> **End of validity:** (current)  
> **Last updated:** 2026-08-23

## Current Status

❌ **Test coverage is INSUFFICIENT** to prevent regressions.

**Current:** 6 tests covering ~15% of core functionality  
**Needed:** 30-50+ tests for minimum regression protection

## Test Inventory

### ✓ Existing Tests (6 total)

#### test_dance.py (4 tests)
1. `test_get_figure()` - Loading a figure by name
2. `test_get_dance()` - Loading a dance by name  
3. `test_dancefloor_creation()` - Creating a dance floor
4. `test_figure_dance_move()` - DanceMove method existence

#### test_frontend.py (2 tests)
1. `test_index_served()` - HTML index page loads
2. `test_static_js()` - Static JS file loads

---

## Coverage Gaps - Critical Untested Components

### 🔴 Core Dance/Figure Logic (HIGH RISK)
| Component | Status | Why Important |
|-----------|--------|---------------|
| SimpleFigure.DanceMove() | ❌ UNTESTED | Core feature - executes dancer moves |
| SimpleFigure.getCrips() | ❌ UNTESTED | Core feature - generates move descriptions |
| ComplexFigure.DanceMove() | ❌ UNTESTED | Complex sequences may have bugs |
| ComplexFigure.getCrips() | ❌ UNTESTED | May return incorrect descriptions |
| Dance.showCrips() | ❌ UNTESTED | User-facing output |
| Figure.loadFigure() | ❌ UNTESTED | File loading errors not caught |

### 🔴 DanceFloor Management (HIGH RISK)
| Component | Status | Why Important |
|-----------|--------|---------------|
| DanceFloor.addDancer() | ❌ UNTESTED | Core positioning logic |
| DanceFloor.DancerbyPos() | ❌ UNTESTED | Position lookup - may throw errors |
| DanceFloor.combineDanceFloor() | ❌ UNTESTED | Parallel moves need conflict detection |
| Position validation | ❌ UNTESTED | Invalid positions not caught |
| Dancer placement conflicts | ❌ UNTESTED | Multiple dancers same position |

### 🔴 Error Handling (HIGH RISK)
| Scenario | Status | Impact |
|----------|--------|--------|
| Missing dance file | ❌ UNTESTED | Silent failure or crash |
| Missing figure file | ❌ UNTESTED | Silent failure or crash |
| Invalid position format | ❌ UNTESTED | May corrupt floor state |
| Malformed JSON | ❌ UNTESTED | Bad data silently accepted |
| No dancers on floor | ❌ UNTESTED | Errors not caught early |
| Dancer in invalid position | ❌ UNTESTED | State corruption |

### 🟡 Edge Cases (MEDIUM RISK)
| Scenario | Status | Impact |
|----------|--------|--------|
| Empty dance | ❌ UNTESTED | May crash or behave oddly |
| Single couple vs 3 couples | ❌ UNTESTED | Boundary conditions |
| Circular reference in figures | ❌ UNTESTED | Stack overflow possible |
| Very long dance sequences | ❌ UNTESTED | Performance degradation |
| Sequential vs parallel execution | ❌ UNTESTED | Different behavior not verified |

### 🟡 Frontend (MEDIUM RISK)
| Component | Status | Impact |
|-----------|--------|--------|
| API endpoints | ⏸️ DISABLED | Features not tested |
| Dance visualization | ❌ UNTESTED | Visual bugs not caught |
| Figure selection UI | ❌ UNTESTED | Interaction issues |
| Floor state display | ❌ UNTESTED | Display not verified |

---

## Recommended Test Plan

### Phase 1: CRITICAL (Prevent Core Breaks)
**Target: 20 new tests**

1. **SimpleFigure Tests (5 tests)**
   - Test DanceMove with valid input
   - Test getCrips output format
   - Test position calculations
   - Test error on missing file
   - Test error on invalid JSON

2. **ComplexFigure Tests (5 tests)**
   - Test sequential figure execution
   - Test parallel figure execution
   - Test nested complex figures
   - Test getCrips with nested figures
   - Test error handling

3. **DanceFloor Tests (5 tests)**
   - Test addDancer and position retrieval
   - Test DancerbyPos exceptions
   - Test position conflicts
   - Test floor state after moves
   - Test initialization with different couple counts

4. **Dance Module Tests (5 tests)**
   - Test getFigure with all figure types
   - Test getDance with various dances
   - Test showCrips output
   - Test dance execution flow
   - Test error handling for missing files

### Phase 2: ENHANCED (Catch Common Regressions)
**Target: 15-20 additional tests**

- Edge cases (empty dances, single couples, long sequences)
- Error conditions (malformed JSON, invalid positions)
- Integration tests (full dance execution flow)
- State consistency (dancers don't duplicate/disappear)

### Phase 3: COMPLETE (Production Ready)
**Target: 10-15 additional tests**

- Performance tests (large dances)
- Backwards compatibility tests
- API endpoint tests
- Frontend integration tests

---

## Test Coverage Measurement

To measure current coverage:

```bash
# Install coverage tool
.\.venv\Scripts\python.exe -m pip install pytest-cov

# Run tests with coverage
.\.venv\Scripts\python.exe -m pytest tests/ --cov=. --cov-report=html

# View results
# Open htmlcov/index.html in browser
```

**Expected current coverage:** ~15% (6 simple tests)  
**Target coverage:** 70%+ (production-ready)

---

## Risk Assessment

| Risk Level | Without Tests | With Current Tests | With Phase 1 Tests |
|-----------|---------------|-------------------|-------------------|
| **Core breaks** | ⚠️ HIGH | ⚠️ MEDIUM | ✓ LOW |
| **Regressions** | ⚠️ HIGH | ⚠️ MEDIUM | ✓ LOW |
| **Error handling** | 🔴 CRITICAL | 🔴 CRITICAL | ⚠️ MEDIUM |
| **Edge cases** | ⚠️ HIGH | ⚠️ HIGH | ⚠️ MEDIUM |

---

## Next Steps

### Immediate (This Sprint)
- ✅ Understand current gaps (THIS DOCUMENT)
- ⏭️ Write Phase 1 tests (20 tests)
- ⏭️ Implement features to pass tests (TDD approach)
- ⏭️ Run coverage report

### Short Term
- Write Phase 2 tests (15-20 tests)
- Achieve 50%+ coverage
- Set up CI/CD to run tests automatically

### Long Term
- Write Phase 3 tests (10-15 tests)
- Achieve 70%+ coverage
- Maintain tests as code evolves

---

## Conclusion

**The project is VULNERABLE to regressions.** Switching to TDD (test-first development) is critical. Before implementing any new features, write tests that fail, then implement code to pass them.

**Recommendation:** Start with Phase 1 tests to protect core functionality from unexpected breaks.
