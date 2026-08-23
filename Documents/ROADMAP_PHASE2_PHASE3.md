# DanceCreator Development Roadmap: Phase 2 & 3

> **Valid from version:** 0.1.0  
> **End of validity:** 1.0.0  
> **Last updated:** 2026-08-23  
> **Status:** PLANNING

---

## Overview

After Phase 1 established TDD foundation with 65 unit tests (40% coverage), we identified two critical bottlenecks:

1. **GUI is empty** - no dances/figures display
   - **Root cause:** Backend and GUI have no agreed-upon API contract
   - **Impact:** Users see blank interface despite working backend

2. **Test coverage not optimal** - 40% is baseline, edge cases untested
   - **Missing:** SimpleFigure edge cases, boundary conditions, error recovery
   - **Impact:** Production bugs may slip past tests

3. **GUI not tested** - no integration or end-to-end tests
   - **Missing:** Selenium/Playwright tests, user workflow validation
   - **Impact:** Can't detect GUI-backend mismatches automatically

---

## Phase 2: Test Coverage Expansion & GUI Integration Foundation

**Duration:** ~2-3 weeks | **Complexity:** Medium | **Risk:** Low

### 2.1 Define API Contracts (CRITICAL - Unblocks everything)

**Why:** Frontend and backend currently don't have a contract. GUI polls endpoints that don't exist or don't return the right format. This is THE reason the GUI is empty.

**Deliverables:**
- `Documents/API_CONTRACT.md` - Defines all endpoints, request/response formats, error codes
- `Documents/GUI_ARCHITECTURE.md` - Explains how frontend consumes the API

**API Endpoints to Define:**

```
GET /api/dances
  Response: { "dances": [ { "id": "Waltz", "name": "Waltz", "figureCount": 3 }, ... ] }

GET /api/dances/<name>
  Response: { "name": "Waltz", "figures": [ { "name": "FeatherStep", "moves": 4 }, ... ], "floor": { ... } }

GET /api/figures
  Response: { "figures": [ { "id": "FeatherStep", "name": "FeatherStep", "moveCount": 4 }, ... ] }

GET /api/figures/<name>
  Response: { "name": "FeatherStep", "moves": [{ "move": 1, "description": "..." }, ...], "crips": [...] }

GET /api/floor/<danceId>
  Response: { "danceId": "Waltz", "floorState": "ascii_visualization", "dancers": [...] }

GET /api/status
  Response: { "status": "healthy", "version": "0.1.0" }

Error Response (all endpoints):
  { "error": "not_found" | "invalid_request" | "server_error", "message": "...", "code": 400/404/500 }
```

**Test Coverage:** Unit tests for contract validation
- [ ] All endpoints documented
- [ ] Request/response schemas validated
- [ ] Error cases defined

### 2.2 Implement Backend API Endpoints

**Blocked by:** gui-api-contracts (above)

**Deliverables:**
- `app.py` - Flask endpoints for GET /api/dances, /api/figures, /api/dances/<name>, etc.
- `app/api/` - Modular endpoint handlers
- Tests: `tests/test_api_endpoints.py` (20+ tests)

**Test Coverage:**
- [ ] GET /api/dances returns correct JSON
- [ ] GET /api/figures/<name> matches contract
- [ ] Error responses match contract
- [ ] Endpoints handle missing files gracefully
- [ ] 200, 400, 404, 500 responses validated

**Success Criteria:**
```bash
# Should work without errors
.\.venv\Scripts\python.exe -m pytest tests/test_api_endpoints.py -v

# Should return valid JSON matching contract
curl http://localhost:5000/api/dances
curl http://localhost:5000/api/figures/FeatherStep
```

### 2.3 Fix Test Fixtures (High Priority)

**Deliverables:**
- Fixed `test_dancefloor.py` - 18 tests, all passing
- Documentation: DanceFloor valid position rules

**Current Status:** 8 tests failing due to fixture conflicts at position (1,1)

**What to investigate:**
- What positions are valid for 2-couple configuration?
- Does DanceFloor have automatic placement?
- Should fixture use different positions?

**Test Coverage:**
- [ ] 2-couple floor positions validated
- [ ] 3-couple floor positions validated
- [ ] Position boundary conditions tested
- [ ] Invalid positions rejected with clear errors

### 2.4 Phase 2 Edge Case Tests (20+ tests)

**Blocked by:** expand-test-coverage (Phase 1 complete)

**Deliverables:**
- `tests/test_simplefigure_execution.py` (15 tests)
- `tests/test_edge_cases.py` (15 tests)
- `tests/test_boundaries.py` (10 tests)
- **Target coverage:** 60%

**Test Coverage by Component:**
- [ ] SimpleFigure with 0 moves (edge case)
- [ ] SimpleFigure with 10+ moves (boundary)
- [ ] Dancers at floor boundaries
- [ ] Multiple simultaneous moves
- [ ] Invalid dancer references
- [ ] Memory/cleanup after moves
- [ ] Position format conversion edge cases
- [ ] Empty floor state handling

**Examples:**
```python
def test_simplefigure_no_moves():
    """Edge case: figure with empty move list"""
    pass

def test_floor_boundary_top_left():
    """Boundary: dancer at position (0,0)"""
    pass

def test_multiple_couples_positioning():
    """Edge case: 4+ couples, ensure no position conflicts"""
    pass
```

### 2.5 GUI Figure Display (Depends on api-endpoints)

**Blocked by:** api-endpoints (Section 2.2)

**Deliverables:**
- Update `public/js/main.js` to fetch from /api/figures
- Display figure list in UI
- Display figure details (moves, crips) when selected
- Tests: `tests/test_gui_figures.py` (10 tests)

**Expected GUI Behavior:**
1. Page loads
2. Fetch GET /api/figures → display list
3. User clicks figure → Fetch GET /api/figures/<name> → display details
4. Handle errors gracefully

**Test Coverage:**
- [ ] GUI makes correct API call
- [ ] Figure list rendered
- [ ] Clicking figure loads details
- [ ] Errors handled (404, 500)
- [ ] Loading states visible

### 2.6 GUI Dance Display (Depends on api-endpoints)

**Blocked by:** api-endpoints (Section 2.2)

**Deliverables:**
- Update `public/js/main.js` to fetch from /api/dances
- Display dance list in UI
- Display dance sequence (figures in order)
- Show floor state visualization
- Tests: `tests/test_gui_dances.py` (10 tests)

**Expected GUI Behavior:**
1. Page loads
2. Fetch GET /api/dances → display list
3. User clicks dance → Fetch GET /api/dances/<name> → display sequence
4. Show dancer positions on floor
5. Handle errors gracefully

### 2.7 Documentation: API & GUI Architecture

**Deliverables:**
- `Documents/API_CONTRACT.md` (5-10 pages)
  - All endpoints documented
  - Request/response schemas
  - Error handling guide
  - Version compatibility notes

- `Documents/GUI_ARCHITECTURE.md` (5 pages)
  - Frontend-backend communication flow
  - Data loading sequence
  - Error handling strategy
  - Performance considerations

- `Documents/TESTING_STRATEGY_PHASE2.md` (3 pages)
  - Test categories (unit, integration, end-to-end)
  - How to write API tests
  - How to write GUI tests
  - Coverage targets by phase

---

## Phase 3: GUI Integration, End-to-End Testing & Performance

**Duration:** ~2-3 weeks | **Complexity:** High | **Risk:** Medium

### 3.1 GUI Integration Tests (End-to-End)

**Deliverables:**
- `tests/test_gui_integration.py` (15+ tests)
- Selenium/Playwright for browser automation
- Tests: load page, interact with UI, verify backend was called

**Test Cases:**
- [ ] Page loads with valid HTML
- [ ] Figure list displays after API call
- [ ] Clicking figure shows details
- [ ] Dance sequence renders correctly
- [ ] Floor visualization updates
- [ ] Error messages displayed when API fails
- [ ] Mobile responsiveness

**Example:**
```python
def test_user_loads_waltz_dance():
    """Complete user workflow: open page → select dance → see floor"""
    driver.get("http://localhost:5000")
    assert "Welcome" in driver.page_source
    
    # Dropdown with dances populated
    dances = driver.find_elements(By.CLASS_NAME, "dance-item")
    assert len(dances) > 0
    
    # Click Waltz
    waltz = next(d for d in dances if "Waltz" in d.text)
    waltz.click()
    
    # Floor should be visible
    floor = driver.find_element(By.ID, "floor-visualization")
    assert floor.is_displayed()
```

### 3.2 Complete Workflow Test

**Deliverables:**
- `tests/test_end_to_end_workflow.py` (10+ tests)
- Tests entire flow: backend → API → GUI → user interaction

**Test Scenario:**
1. Start app
2. Load dance from file (backend)
3. Calculate moves (backend)
4. Generate floor state (backend)
5. Expose via API (backend)
6. GUI fetches data (frontend)
7. GUI renders visualization (frontend)
8. Verify all data matches

**Example:**
```python
def test_workflow_load_execute_display():
    """Dance file → execution → API → GUI visualization"""
    # Backend: Load dance
    dance = Dance.getDance("Waltz")
    floor = DanceFloor("Waltz", 2)
    # ... execute moves ...
    
    # API: Expose floor state
    response = client.get("/api/dances/Waltz")
    assert response.status_code == 200
    assert "dancers" in response.json["floor"]
    
    # GUI: Load and verify
    driver.get("/")
    waltz_card = driver.find_element_by_xpath("//div[@data-dance='Waltz']")
    assert "dancer" in waltz_card.text.lower()
```

### 3.3 Performance & Load Tests

**Deliverables:**
- `tests/test_performance.py` (8+ tests)
- Baseline metrics: API response time, GUI render time, memory usage

**Test Cases:**
- [ ] GET /api/dances completes in <100ms
- [ ] GET /api/figures/<name> completes in <200ms
- [ ] Floor visualization renders in <500ms
- [ ] Handles 1000 dancers without crashing
- [ ] Memory usage stays under 100MB
- [ ] API handles 10 concurrent requests

**Example:**
```python
def test_api_dances_response_time():
    """API should respond within 100ms"""
    start = time.time()
    response = client.get("/api/dances")
    elapsed = time.time() - start
    assert elapsed < 0.1, f"Took {elapsed}s, expected <0.1s"
```

### 3.4 Extended Error Handling

**Deliverables:**
- `tests/test_error_handling_phase3.py` (15+ tests)
- Graceful degradation when backend fails

**Test Cases:**
- [ ] API returns 404 for missing dance
- [ ] API returns 500 on internal error
- [ ] GUI displays error message to user
- [ ] GUI remains functional after error
- [ ] Network timeout handled (5s timeout)
- [ ] Corrupted JSON handled
- [ ] Missing required fields handled

### 3.5 Performance Optimization (If needed)

**Deliverables:**
- Caching layer for API responses
- Database indexing for large datasets
- Frontend code splitting/lazy loading
- Documentation: performance tuning guide

---

## Summary: What Gets Unblocked When

```
PHASE 2 CRITICAL PATH:
gui-api-contracts (1 day) 
  ↓
api-endpoints (2-3 days) 
  ↓
gui-figure-display (1 day) + gui-dance-display (1 day)
  ↓
end-to-end-workflow (1-2 days)

PHASE 2 PARALLEL:
test-coverage-phase2 (2-3 days)
fix-test-fixtures (1 day)
documentation-phase2 (1 day)

PHASE 3 BUILDS ON:
All Phase 2 work done
  ↓
gui-integration-tests (3-4 days)
performance-tests (2 days)
error-handling-extended (2 days)
```

---

## Success Criteria

### Phase 2 Success:
- ✅ GUI displays 5+ dances and 20+ figures (no longer empty)
- ✅ 60% code coverage (up from 40%)
- ✅ API contract documented and stable
- ✅ 50+ new tests created
- ✅ All Phase 1 tests still passing

### Phase 3 Success:
- ✅ 75% code coverage
- ✅ Complete end-to-end tests (backend → frontend)
- ✅ Performance baselines established
- ✅ GUI fully responsive and error-tolerant
- ✅ 30+ new tests created

---

## Effort Estimate

| Phase | Duration | Credits | Complexity |
|-------|----------|---------|------------|
| 2.1 (Contracts) | 1 day | 3 | Low |
| 2.2 (Endpoints) | 3 days | 8 | Medium |
| 2.3 (Fix fixtures) | 1 day | 2 | Low |
| 2.4 (Edge cases) | 2-3 days | 6 | Medium |
| 2.5-2.6 (GUI) | 2-3 days | 6 | Medium |
| 2.7 (Docs) | 1 day | 3 | Low |
| **Phase 2 Total** | **~2 weeks** | **28** | **Medium** |
| Phase 3 (Integration) | 2-3 weeks | 24 | High |
| **TOTAL** | **~4-5 weeks** | **52** | - |

---

## Next Steps

1. **This session:** Create comprehensive todo list (✓ DONE)
2. **Next session:** Start with gui-api-contracts (1-2 credits)
3. **Session after:** Implement api-endpoints (4-5 credits)
4. **Then:** Wire up GUI to API (2-3 credits)

**Recommendation:** Focus on Phase 2 critical path first. Get GUI working (contracts → endpoints → UI display) before investing in advanced tests.
