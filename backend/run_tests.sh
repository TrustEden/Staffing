#!/bin/bash
# Test runner script for Healthcare Staffing Bridge backend

# Set PYTHONPATH to include the parent directory
export PYTHONPATH=/home/user/Connected:$PYTHONPATH

echo "========================================="
echo "Healthcare Staffing Bridge - Test Suite"
echo "========================================="
echo ""

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest tests/ \
    -v \
    --cov=backend/app \
    --cov-report=term-missing \
    --cov-report=html \
    --tb=short \
    "$@"

EXIT_CODE=$?

echo ""
echo "========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Some tests failed (exit code: $EXIT_CODE)"
fi
echo "========================================="
echo ""
echo "Coverage report saved to htmlcov/index.html"

exit $EXIT_CODE
