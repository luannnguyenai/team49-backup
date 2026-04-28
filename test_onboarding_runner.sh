#!/bin/bash
# Comprehensive test runner for onboarding and assessment flow

set -e

echo "========================================"
echo "ONBOARDING & ASSESSMENT FLOW TEST SUITE"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TEST_RESULTS=()

run_test() {
    local test_name="$1"
    local test_file="$2"

    echo "${YELLOW}[TEST]${NC} Running: $test_name"
    echo "  File: $test_file"

    if python3 -m pytest "$test_file" -v --tb=short 2>&1 | tee /tmp/test_output.log; then
        echo "${GREEN}[PASS]${NC} $test_name"
        TEST_RESULTS+=("PASS: $test_name")
    else
        echo "${RED}[FAIL]${NC} $test_name"
        TEST_RESULTS+=("FAIL: $test_name")
    fi
    echo ""
}

# Test 1: Basic router registration
echo "${YELLOW}=== TEST 1: Router Registration ===${NC}"
run_test "Placement Assessment Router" "tests/test_placement_assessment_router.py"

# Test 2: Onboarding endpoints
echo "${YELLOW}=== TEST 2: Onboarding Schema & Service ===${NC}"
run_test "Onboarding Endpoints" "tests/test_onboarding_endpoints.py"

# Test 3: Placement Assessment Service
echo "${YELLOW}=== TEST 3: Placement Assessment Service ===${NC}"
if [ -f "tests/services/test_placement_assessment_service.py" ]; then
    run_test "Placement Assessment Service" "tests/services/test_placement_assessment_service.py"
else
    echo "${YELLOW}[SKIP]${NC} Placement Assessment Service test file not found"
fi

# Test 4: Placement Assessment Repository
echo "${YELLOW}=== TEST 4: Placement Assessment Repository ===${NC}"
if [ -f "tests/repositories/test_placement_assessment_repo.py" ]; then
    run_test "Placement Assessment Repository" "tests/repositories/test_placement_assessment_repo.py"
else
    echo "${YELLOW}[SKIP]${NC} Placement Assessment Repository test file not found"
fi

# Test 5: E2E Onboarding Flow (new)
echo "${YELLOW}=== TEST 5: End-to-End Onboarding Flow ===${NC}"
run_test "E2E Onboarding Flow" "tests/integration/test_onboarding_flow_e2e.py"

# Print summary
echo ""
echo "========================================"
echo "TEST SUMMARY"
echo "========================================"
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done
echo "========================================"
