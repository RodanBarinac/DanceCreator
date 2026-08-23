# Todo Quick Reference

> **Valid from version:** 0.1.0  
> **End of validity:** 1.0.0  
> **Last updated:** 2026-08-23  
> **Status:** PLANNING

---

## At a Glance

### 📊 Total Planned Work
- **Phase 1:** ✅ COMPLETE (65 tests, 40% coverage)
- **Phase 2:** 📋 PLANNED (14 todos, ~28 credits)
- **Phase 3:** 🔮 PENDING (end-to-end tests, performance)
- **Total todos:** 20 (6 done, 14 pending)

### 🔴 Critical Blockers (Unblock everything)
1. **gui-api-contracts** ← START HERE (1-2 credits)
2. **api-endpoints** ← Depends on #1 (4-5 credits)

Once these 2 are done, GUI will no longer be empty.

### 🟡 High Priority (Can run in parallel)
- **fix-test-fixtures** - Resolves 8 failing tests (1 credit)
- **test-coverage-phase2** - Edge cases & boundaries (6 credits)
- **documentation-phase2** - API & GUI docs (3 credits)

### 🟢 Implementation (Depends on api-endpoints)
- **gui-figure-display** - Wire GUI to figures (2 credits)
- **gui-dance-display** - Wire GUI to dances (2 credits)
- **gui-floor-visualization** - SVG/Canvas rendering (2 credits)

### 🔵 Testing & Quality (Depends on everything above)
- **gui-integration-tests** - Selenium/Playwright (6 credits)
- **end-to-end-workflow** - Backend→API→GUI (4 credits)
- **error-handling-extended** - GUI error cases (3 credits)
- **performance-tests** - Response times & load (3 credits)

---

## Critical Path

```
Session 1: gui-api-contracts (1-2 credits)
    ↓
Session 2-3: api-endpoints (4-5 credits)
    ↓
Session 3-4: gui-figure-display + gui-dance-display (4 credits)
    ↓
Session 5: gui-integration-tests begin (2-3 credits)
    
PARALLEL (can overlap):
Session 1-2: fix-test-fixtures (1 credit)
Session 2-4: test-coverage-phase2 (6 credits)
```

---

## Current Status by Category

### Test Coverage
| Item | Status | Tests | Coverage |
|------|--------|-------|----------|
| Phase 1 Core | ✅ DONE | 65 | 40% |
| Phase 2 Edge Cases | ❌ PENDING | 0 | 0% |
| Phase 3 Integration | ❌ PENDING | 0 | 0% |
| **Total** | **~60%** | **65** | **40%** |

### GUI / Frontend
| Item | Status | Impact |
|------|--------|--------|
| Loads | ✅ YES | Can open in browser |
| Shows dances | ❌ NO | Empty list |
| Shows figures | ❌ NO | Empty list |
| Displays floor | ❌ NO | No visualization |
| **Root cause** | **No API contract** | **Everything blocked** |

### Backend / API
| Item | Status | Impact |
|------|--------|--------|
| Core logic | ✅ WORKING | Dances execute correctly |
| API endpoints | ❌ MISSING | Frontend has nothing to call |
| Error handling | ⚠️ PARTIAL | 31+ tests passing |
| Documentation | ⚠️ PARTIAL | Contracts undefined |

---

## What Each Todo Accomplishes

### 🎯 Highest Impact (Unblocks everything)

**gui-api-contracts** (1-2 credits)
- Define what /api/dances, /api/figures return
- Document request/response formats
- Unblocks: 5 other todos

**api-endpoints** (4-5 credits)
- Implement Flask endpoints
- Connect to Python backend
- Test with 20+ unit tests
- Unblocks: GUI display, integration tests

### 🎨 Frontend (Depends on api-endpoints)

**gui-figure-display** (2 credits)
- Fetch /api/figures
- Render list in UI
- Show figure details

**gui-dance-display** (2 credits)
- Fetch /api/dances
- Show dance sequences
- Display floor state

**gui-floor-visualization** (2 credits)
- Create SVG/Canvas of floor
- Show dancer positions
- Update on move

### ✅ Testing (Can overlap)

**fix-test-fixtures** (1 credit)
- Fix DanceFloor position conflicts
- Resolve 8 failing tests
- Understand valid positions

**test-coverage-phase2** (6 credits)
- 20+ edge case tests
- Boundaries, error conditions
- Target: 60% coverage

**gui-integration-tests** (6 credits)
- Selenium/Playwright
- Full user workflow tests
- Unblocks: end-to-end tests

**end-to-end-workflow** (4 credits)
- Backend → API → GUI complete flow
- Verify all data matches
- Catch integration bugs

**error-handling-extended** (3 credits)
- GUI behaves gracefully when API fails
- 404, 500, timeout handling
- User sees helpful messages

**performance-tests** (3 credits)
- API response time baselines
- GUI rendering speed
- Load testing

### 📚 Documentation

**documentation-phase2** (3 credits)
- API_CONTRACT.md
- GUI_ARCHITECTURE.md
- TESTING_STRATEGY_PHASE2.md

---

## Recommended Session Sequence

### Session 1 (Today): Planning ✅ DONE
- [x] Create comprehensive todo list
- [x] Create roadmap with phases
- [x] Identify critical blockers
- [x] Set priorities

### Session 2 (Next): Contracts & Baseline
- Define gui-api-contracts (1-2 credits)
- Fix test fixtures (1 credit)
- Remaining: 1-2 credits flexibility

### Session 3-4: Backend Integration
- Implement api-endpoints (4-5 credits)
- Write API tests
- Verify endpoints work

### Session 5-6: Frontend Wiring
- gui-figure-display (2 credits)
- gui-dance-display (2 credits)
- Test in browser

### Session 7+: Testing & Polish
- gui-integration-tests
- end-to-end-workflow
- performance-tests
- error-handling-extended

---

## How to Track Progress

### View all todos
```bash
# This will be displayed at start of each session
cd e:\Git\DanceCreator
# Query: SELECT * FROM todos WHERE status = 'pending'
```

### Update a todo
```bash
# When starting work
UPDATE todos SET status = 'in_progress' WHERE id = 'gui-api-contracts'

# When complete
UPDATE todos SET status = 'done' WHERE id = 'gui-api-contracts'
```

### View dependencies
```bash
# What blocks this todo?
SELECT depends_on FROM todo_deps WHERE todo_id = 'api-endpoints'

# What does this todo unblock?
SELECT todo_id FROM todo_deps WHERE depends_on = 'gui-api-contracts'
```

---

## Success Indicators

### Phase 2 Complete When:
- ✅ GUI shows 5+ dances
- ✅ GUI shows 20+ figures
- ✅ 60% code coverage (up from 40%)
- ✅ 50+ new tests pass
- ✅ All Phase 1 tests still pass

### Phase 3 Complete When:
- ✅ 75% code coverage
- ✅ End-to-end tests pass
- ✅ Performance baselines set
- ✅ GUI handles all errors gracefully

---

## Quick Reference: Commands

```bash
# Run all tests
.\.venv\Scripts\python.exe -m pytest tests/ -v

# Run one test file
.\.venv\Scripts\python.exe -m pytest tests/test_dancefloor.py -v

# Run with coverage
.\.venv\Scripts\python.exe -m pytest tests/ --cov=. -v

# Start Flask app (for testing)
.\.venv\Scripts\python.exe app.py

# View plan
cat C:/Users/gero/.copilot/session-state/472bbe2e-870b-4ee6-b03a-a20f124ec53e/plan.md

# View roadmap
cat Documents/ROADMAP_PHASE2_PHASE3.md
```

---

## Why This Order?

1. **gui-api-contracts FIRST** - Until we know what format GUI expects, everything else is guesswork
2. **api-endpoints SECOND** - Can't wire GUI to nothing
3. **fix-test-fixtures PARALLEL** - Low risk, unblocks test suite
4. **GUI wiring** - Only after endpoints exist and are tested
5. **Integration tests LAST** - Test the full stack only after components work

This order minimizes wasted work and rework.
