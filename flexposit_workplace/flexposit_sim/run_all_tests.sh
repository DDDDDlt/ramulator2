#!/bin/bash

# Run all accelerator test scripts
# Usage: bash run_all_tests.sh [--is_generation]

echo "=========================================="
echo "Start running all accelerator tests"
echo "=========================================="
echo ""

# Check --is_generation flag
if [ "$1" == "--is_generation" ]; then
    GEN_FLAG="--is_generation"
    echo "Mode: Generation"
else
    GEN_FLAG=""
    echo "Mode: Prefill"
fi
echo ""

# Create log directory if not exists
mkdir -p ./log

# Test list
# tests=("baseline" "olive" "ant" "flexposit" "bitmod")
tests=("baseline" "olive" "flexposit" "bitmod")


# Run each test
for test in "${tests[@]}"; do
    echo "=========================================="
    echo "Running: test_${test}.py"
    echo "=========================================="
    python test_${test}.py $GEN_FLAG > ./log/test_${test}.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ test_${test}.py succeeded"
    else
        echo "✗ test_${test}.py failed"
    fi
    echo ""
done

echo "=========================================="
echo "All tests finished!"
echo "Logs saved under ./log/"
echo "=========================================="
echo ""

# Show generated logs
echo "Generated log files:"
ls -lh ./log/test_*.log

