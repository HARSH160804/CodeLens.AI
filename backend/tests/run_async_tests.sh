#!/bin/bash
# Test runner for async ingestion components

echo "========================================="
echo "Running Async Ingestion Tests"
echo "========================================="
echo ""

# Run IdempotencyManager tests
echo "1. Testing IdempotencyManager..."
python -m pytest tests/test_idempotency_manager.py -v
IDEMPOTENCY_RESULT=$?

echo ""
echo "2. Testing ProgressTracker..."
python -m pytest tests/test_progress_tracker.py -v
PROGRESS_RESULT=$?

echo ""
echo "3. Testing ProcessRepoWorker..."
python -m pytest tests/test_process_repo_worker.py -v
WORKER_RESULT=$?

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "IdempotencyManager: $([ $IDEMPOTENCY_RESULT -eq 0 ] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "ProgressTracker: $([ $PROGRESS_RESULT -eq 0 ] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "ProcessRepoWorker: $([ $WORKER_RESULT -eq 0 ] && echo '✅ PASSED' || echo '❌ FAILED')"
echo ""

# Exit with failure if any test failed
if [ $IDEMPOTENCY_RESULT -ne 0 ] || [ $PROGRESS_RESULT -ne 0 ] || [ $WORKER_RESULT -ne 0 ]; then
    echo "❌ Some tests failed"
    exit 1
else
    echo "✅ All tests passed!"
    exit 0
fi
