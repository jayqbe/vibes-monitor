#!/bin/bash
# Token Telemetry Final Validation Script
# This script validates all acceptance criteria for the token-telemetry package

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print error messages
error_msg() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED=$((FAILED + 1))
}

# Function to print success messages
success_msg() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED=$((PASSED + 1))
}

# Function to print warning messages
warning_msg() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

# Function to print info messages
info_msg() {
    echo "[INFO] $1"
}

echo "=========================================="
echo "Token Telemetry Final Validation"
echo "=========================================="
echo ""

# Test 1: Package can be imported
info_msg "Test 1: Verifying package can be imported..."
if python3 -c "import token_telemetry; print('OK')" 2> /dev/null; then
    success_msg "Package import test passed"
else
    error_msg "Package import test failed"
fi

# Test 2: Package has correct version
info_msg "Test 2: Verifying package version..."
VERSION=$(python3 -c "import token_telemetry; print(token_telemetry.__version__)" 2> /dev/null)
if [ -n "$VERSION" ]; then
    success_msg "Package version is set: $VERSION"
else
    error_msg "Package version is not set or not accessible"
fi

# Test 3: Entry points are available
info_msg "Test 3: Verifying entry points..."
if command -v token-telemetry &> /dev/null; then
    success_msg "token-telemetry entry point is available"
else
    error_msg "token-telemetry entry point is not available"
fi

if command -v telemetry-proxy &> /dev/null; then
    success_msg "telemetry-proxy entry point is available"
else
    warning_msg "telemetry-proxy entry point is not available"
fi

if command -v telemetry-report &> /dev/null; then
    success_msg "telemetry-report entry point is available"
else
    warning_msg "telemetry-report entry point is not available"
fi

# Test 4: CLI help works
info_msg "Test 4: Verifying CLI help..."
if token-telemetry --help &> /dev/null; then
    success_msg "token-telemetry --help works"
else
    error_msg "token-telemetry --help failed"
fi

if token-telemetry proxy --help &> /dev/null; then
    success_msg "token-telemetry proxy --help works"
else
    error_msg "token-telemetry proxy --help failed"
fi

if token-telemetry report --help &> /dev/null; then
    success_msg "token-telemetry report --help works"
else
    error_msg "token-telemetry report --help failed"
fi

# Test 5: Dependencies are installed
info_msg "Test 5: Verifying dependencies..."
if python3 -c "import requests; print('OK')" 2> /dev/null; then
    success_msg "requests library is installed"
else
    error_msg "requests library is not installed"
fi

if python3 -c "import yaml; print('OK')" 2> /dev/null; then
    success_msg "pyyaml library is installed"
else
    error_msg "pyyaml library is not installed"
fi

# Test 6: Core modules can be imported
info_msg "Test 6: Verifying core modules..."
MODULES=("token_telemetry.config" "token_telemetry.database" "token_telemetry.cost_calculator" "token_telemetry.proxy" "token_telemetry.reporter" "token_telemetry.models" "token_telemetry.cli")

for module in "${MODULES[@]}"; do
    if python3 -c "import $module; print('OK')" 2> /dev/null; then
        success_msg "Module $module can be imported"
    else
        error_msg "Module $module cannot be imported"
    fi
done

# Test 7: Database module works
info_msg "Test 7: Verifying database module..."
TEST_DB=$(mktemp /tmp/test_telemetry_XXXXXX.db)
trap "rm -f $TEST_DB" EXIT

if python3 -c "
import sys
sys.path.insert(0, 'src')
from token_telemetry.database import Database
db = Database('$TEST_DB')
print('OK')
" 2> /dev/null; then
    success_msg "Database module initialization works"
else
    error_msg "Database module initialization failed"
fi

# Test 8: Cost calculator works
info_msg "Test 8: Verifying cost calculator..."
if python3 -c "
import sys
sys.path.insert(0, 'src')
from token_telemetry.cost_calculator import CostCalculator
cc = CostCalculator()
cost = cc.calculate_cost('mistral-medium', 100, 200)
print(f'Cost: {cost}')
" 2> /dev/null; then
    success_msg "Cost calculator works"
else
    error_msg "Cost calculator failed"
fi

# Test 9: Models work
info_msg "Test 9: Verifying models..."
if python3 -c "
import sys
sys.path.insert(0, 'src')
from token_telemetry.models import CallRecord, SummaryStats
record = CallRecord('2026-01-01T00:00:00', 'test-model', '/api/test', 'user', 100, 200, 1.5, 200, 0.01)
print(f'Total tokens: {record.total_tokens()}')
" 2> /dev/null; then
    success_msg "Models work correctly"
else
    error_msg "Models failed"
fi

# Test 10: Reporter works
info_msg "Test 10: Verifying reporter..."
if python3 -c "
import sys
sys.path.insert(0, 'src')
from token_telemetry.reporter import Reporter
r = Reporter(db_path='$TEST_DB')
summary = r.generate_summary()
print('OK')
" 2> /dev/null; then
    success_msg "Reporter works"
else
    error_msg "Reporter failed"
fi

# Test 11: Configuration loading works
info_msg "Test 11: Verifying configuration loading..."
if python3 -c "
import sys
sys.path.insert(0, 'src')
from token_telemetry.config import load_config
config = load_config()
print(f'Proxy host: {config.proxy.host}')
" 2> /dev/null; then
    success_msg "Configuration loading works"
else
    error_msg "Configuration loading failed"
fi

# Test 12: Run unit tests
info_msg "Test 12: Running unit tests..."
if PYTHONPATH=src python3 -m pytest tests/unit/test_models.py tests/unit/test_cost_calculator.py tests/unit/test_database.py -q --no-cov 2>&1 | grep -q "passed"; then
    success_msg "Core unit tests passed"
else
    error_msg "Core unit tests failed"
fi

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Warnings: $WARNINGS"
echo ""

if [ $FAILED -gt 0 ]; then
    error_msg "Validation failed with $FAILED error(s)"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    warning_msg "Validation passed with $WARNINGS warning(s)"
    exit 0
else
    success_msg "All validation tests passed!"
    exit 0
fi
