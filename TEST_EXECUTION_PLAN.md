# Test Execution Plan - Detailed Instructions

**Created:** 2026-04-27
**Status:** Ready for environment setup and execution

---

## 🔧 Environment Setup

### Prerequisites Check

```bash
# 1. Verify Python version (3.8+)
python3 --version
# Expected: Python 3.8.x or 3.9.x

# 2. Verify project structure
ls -la /Users/binluan/A20-App-049/
# Should have: src/, tests/, alembic/, requirements.txt, pyproject.toml

# 3. Check if virtual environment is active
which python3
# Should show: /path/to/venv/bin/python3
```

### Install Dependencies

```bash
cd /Users/binluan/A20-App-049

# Create virtual environment (if not exists)
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Install project dependencies
pip install -r requirements.txt

# Verify key packages installed
pip list | grep -E "fastapi|sqlalchemy|pytest|asyncpg"
# Should show: fastapi, sqlalchemy, pytest, pytest-asyncio, asyncpg
```

### Database Setup

```bash
cd /Users/binluan/A20-App-049

# Create .env if not exists
cp .env.example .env

# Edit .env with your database credentials
nano .env
# Required: DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Apply migrations
alembic upgrade head

# Verify migrations applied
alembic current
# Should show latest revision
```

---

## 📊 Test Execution Strategy

### Phase 1: Basic Syntax Validation (No DB Required)

```bash
cd /Users/binluan/A20-App-049

# Validate Python syntax
python3 -m py_compile tests/test_placement_assessment_router.py
python3 -m py_compile tests/test_onboarding_endpoints.py
python3 -m py_compile tests/integration/test_onboarding_flow_e2e.py

# Validate imports (compile only)
python3 -c "import ast; ast.parse(open('tests/integration/test_onboarding_flow_e2e.py').read())"
# Expected: No output (success) or error message
```

### Phase 2: Unit Tests (No DB Required)

```bash
cd /Users/binluan/A20-App-049

# Run router registration tests
python3 -m pytest tests/test_placement_assessment_router.py -v

# Expected Output:
# tests/test_placement_assessment_router.py::PlacementAssessmentRouterRegistrationTests::test_router_importable PASSED
# tests/test_placement_assessment_router.py::PlacementAssessmentRouterRegistrationTests::test_router_has_four_routes PASSED
# tests/test_placement_assessment_router.py::PlacementAssessmentRouterRegistrationTests::test_router_registered_in_app PASSED
# ================================ 3 passed in 0.15s =================================
```

### Phase 3: Schema & Service Tests (No DB Required)

```bash
cd /Users/binluan/A20-App-049

# Run onboarding endpoint tests
python3 -m pytest tests/test_onboarding_endpoints.py -v

# Expected: 10+ tests passing for schema validation and service logic
```

### Phase 4: Integration Tests (Requires DB)

```bash
cd /Users/binluan/A20-App-049

# Ensure database is running
# Check connection
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import Settings

async def test_db():
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute('SELECT 1')
        print('✓ Database connection OK')
    except Exception as e:
        print(f'✗ Database error: {e}')
    finally:
        await engine.dispose()

asyncio.run(test_db())
"

# Run new E2E tests
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -v --tb=short

# Expected: 8 tests passing (or skipping if test data missing)
```

---

## 📈 Expected Test Results

### Phase 1: Syntax Validation
```
Status: PASS ✅
Output: (no output = success)
Time: <1 second
```

### Phase 2: Router Tests
```
tests/test_placement_assessment_router.py::PlacementAssessmentRouterRegistrationTests::test_router_importable PASSED
tests/test_placement_assessment_router.py::PlacementAssessmentRouterRegistrationTests::test_router_has_four_routes PASSED
tests/test_placement_assessment_router.py::PlacementAssessmentRouterRegistrationTests::test_router_registered_in_app PASSED

3 passed in 0.15s ✅
```

### Phase 3: Schema & Service Tests
```
tests/test_onboarding_endpoints.py::TestGoalsRequestSchema::test_valid_single_goal PASSED
tests/test_onboarding_endpoints.py::TestGoalsRequestSchema::test_valid_multiple_goals PASSED
tests/test_onboarding_endpoints.py::TestGoalsRequestSchema::test_invalid_goal_raises PASSED
tests/test_onboarding_endpoints.py::TestGoalsRequestSchema::test_empty_list_raises PASSED
tests/test_onboarding_endpoints.py::TestGoalsRequestSchema::test_mixed_valid_invalid_raises PASSED
tests/test_onboarding_endpoints.py::TestGoalsRequestSchema::test_all_valid_goal_ids PASSED
tests/test_onboarding_endpoints.py::TestKnownTopicsRequestSchema::test_valid_uuids PASSED
tests/test_onboarding_endpoints.py::TestKnownTopicsRequestSchema::test_empty_list_is_valid PASSED
tests/test_onboarding_endpoints.py::TestKnownTopicsRequestSchema::test_invalid_uuid_raises PASSED
tests/test_onboarding_endpoints.py::TestGoalsResponseSchema::test_round_trip PASSED
tests/test_onboarding_endpoints.py::TestTopicsResponseSchema::test_empty_courses PASSED
tests/test_onboarding_endpoints.py::TestTopicsResponseSchema::test_nested_structure PASSED

12+ passed in 0.25s ✅
```

### Phase 4: Integration Tests (with test data)
```
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step1_set_goals PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step2_get_topics PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step3_set_known_topics PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step4_set_experience_level PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step5_start_placement_assessment PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step6_submit_placement_answers PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_complete_journey PASSED
tests/integration/test_onboarding_flow_e2e.py::test_placement_assessment_with_mixed_answers PASSED

8 passed in 2.35s ✅
```

### Phase 4: Integration Tests (without test data - expected skips)
```
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step1_set_goals PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step2_get_topics PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step3_set_known_topics PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step4_set_experience_level PASSED
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step5_start_placement_assessment SKIPPED (No learning units with canonical_unit_id)
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step6_submit_placement_answers SKIPPED (No learning unit with canonical_unit_id)
tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_complete_journey PASSED (partial - skips placement due to missing data)
tests/integration/test_onboarding_flow_e2e.py::test_placement_assessment_with_mixed_answers SKIPPED (No learning unit with canonical_unit_id)

4 passed, 4 skipped in 0.85s ⚠️
```

---

## 🧪 Running Tests by Category

### **All Tests at Once**
```bash
cd /Users/binluan/A20-App-049
python3 -m pytest tests/ -v --tb=short

# Summary: Should see ~25+ passed tests
```

### **Only Onboarding Tests**
```bash
python3 -m pytest tests/ -k "onboarding or placement" -v --tb=short

# Filters to: onboarding_*, placement_*
```

### **Only New E2E Tests**
```bash
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -v --tb=short

# Just the 8 new integration tests
```

### **Individual Test Case**
```bash
# Test goal setting only
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_step1_set_goals -v

# Test complete journey only
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_complete_journey -v
```

### **With Coverage Report**
```bash
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py \
  -v \
  --cov=src/routers \
  --cov=src/services \
  --cov=src/schemas \
  --cov-report=term-missing \
  --cov-report=html

# Creates htmlcov/index.html with coverage report
```

---

## 🚨 Troubleshooting

### Issue 1: asyncpg not installed
```bash
# Error: ModuleNotFoundError: No module named 'asyncpg'

# Solution: Install dependencies
pip install -r requirements.txt
pip install asyncpg

# Verify
python3 -c "import asyncpg; print('✓ asyncpg OK')"
```

### Issue 2: Database connection failed
```bash
# Error: could not connect to server

# Check connection string
python3 -c "from src.config import Settings; print(Settings().database_url)"

# Expected format: postgresql+asyncpg://user:password@localhost:5432/dbname

# Test connection
python3 << 'EOF'
import asyncio
from sqlalchemy import text
from src.database import get_async_engine

async def test():
    engine = await get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT NOW()"))
        print(f"✓ Database OK: {result.scalar()}")

asyncio.run(test())
EOF
```

### Issue 3: Migrations not applied
```bash
# Error: Table 'sessions' does not exist

# Solution: Apply migrations
alembic upgrade head

# Verify
alembic current
# Should show latest revision

# Rollback if needed
alembic downgrade -1
alembic upgrade head
```

### Issue 4: Tests skip due to missing data
```bash
# Output: SKIPPED (No learning units with canonical_unit_id)

# This is expected if database doesn't have test data
# Tests will still run but some will skip

# To populate test data:
python3 << 'EOF'
# Run data seeding script or load fixtures
# See tests/conftest.py for fixture definitions
EOF
```

### Issue 5: Import errors
```bash
# Error: ModuleNotFoundError: No module named 'src'

# Solution: Add to PYTHONPATH
export PYTHONPATH=/Users/binluan/A20-App-049:$PYTHONPATH

# Or run from project root
cd /Users/binluan/A20-App-049
python3 -m pytest tests/...
```

---

## ✅ Complete Test Checklist

### Pre-Test Setup
- [ ] Python 3.8+ installed: `python3 --version`
- [ ] Virtual environment active: `which python3`
- [ ] Dependencies installed: `pip list | grep pytest`
- [ ] .env configured: `cat .env | grep DATABASE_URL`
- [ ] Database running: `psql -c "SELECT 1"`
- [ ] Migrations applied: `alembic current`

### Phase 1: Syntax
- [ ] test_placement_assessment_router.py compiles
- [ ] test_onboarding_endpoints.py compiles
- [ ] test_onboarding_flow_e2e.py compiles

### Phase 2: Unit Tests
- [ ] Router tests pass (3/3)
- [ ] Schema tests pass (10+/10+)
- [ ] Service tests pass (existing tests)

### Phase 3: Integration Tests
- [ ] Step 1 test passes (goal setting)
- [ ] Step 2 test passes (topics)
- [ ] Step 3 test passes (known topics)
- [ ] Step 4 test passes (experience)
- [ ] Step 5 test passes or skips gracefully (placement start)
- [ ] Step 6 test passes or skips gracefully (submit)
- [ ] Journey test passes (all steps)
- [ ] Edge case test passes or skips gracefully (mixed answers)

### Post-Test
- [ ] All tests passed or skipped with reason
- [ ] No error messages in output
- [ ] Coverage report generated (if using --cov)
- [ ] Results documented

---

## 📋 Test Results Template

Save this to document your test run:

```markdown
# Test Execution Results

**Date:** [YYYY-MM-DD]
**Environment:** [OS, Python version, Database]
**Executed By:** [Your name]

## Phase 1: Syntax Validation
- Router registration tests: ✅ PASS
- Onboarding endpoints tests: ✅ PASS
- E2E integration tests: ✅ PASS

## Phase 2: Unit Tests
- Router registration (3): ✅ 3/3 PASSED
- Schema validation (10+): ✅ 10+/10+ PASSED
- Service logic: ✅ X/X PASSED

## Phase 3: Integration Tests
- Step 1 (Set Goals): ✅ PASSED
- Step 2 (Get Topics): ✅ PASSED
- Step 3 (Known Topics): ✅ PASSED
- Step 4 (Experience Level): ✅ PASSED
- Step 5 (Start Assessment): ✅ PASSED [or ⚠️ SKIPPED - reason]
- Step 6 (Submit Answers): ✅ PASSED [or ⚠️ SKIPPED - reason]
- Complete Journey: ✅ PASSED
- Edge Cases: ✅ PASSED [or ⚠️ SKIPPED - reason]

## Summary
**Total Tests:** 25+
**Passed:** XX
**Failed:** 0
**Skipped:** X
**Duration:** X seconds

## Coverage
**Routers:** XX%
**Services:** XX%
**Schemas:** XX%

## Issues/Notes
- None

## Sign-off
✅ All tests ready for production
```

---

## 🎯 Success Criteria

Tests are ready when:

- ✅ All syntax validation passes
- ✅ All unit tests pass (3+ router tests, 10+ schema tests)
- ✅ All integration tests pass OR skip with clear reason
- ✅ No error messages
- ✅ Coverage ≥80% for modified files
- ✅ Database operations work correctly
- ✅ Decision logic validated

---

## 📞 Getting Help

### Documentation
1. **TESTING_ONBOARDING_FLOW.md** - Comprehensive test reference
2. **MANUAL_TESTING_GUIDE.md** - Curl examples and scenarios
3. **TEST_STATUS_REPORT.md** - Status and setup guide
4. **ONBOARDING_TESTING_SUMMARY.md** - Quick start and summary

### Commands

```bash
# Run this script for complete test execution
bash test_onboarding_runner.sh

# Or run tests individually
python3 -m pytest tests/ -v --tb=short -k onboarding
```

### Debug Info

```bash
# Show all test names (without running)
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py --collect-only

# Run with full output
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -vv --tb=long

# Show local variables on failure
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -l

# Stop on first failure
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -x

# Show print statements
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -s
```

---

**Ready to execute! Follow Phase 1 → Phase 2 → Phase 3 → Phase 4**
