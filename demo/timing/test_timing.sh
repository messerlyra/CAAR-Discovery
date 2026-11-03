#!/bin/bash

# Exit on error
set -e

# Setup paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_BIN="/home/99r/para/projects/ALF/src/.venv/bin/python"
LOG_FILE="$SCRIPT_DIR/timings_test.csv"
SERVER_SCRIPT="$SCRIPT_DIR/timing_server.py"
TEST_SCRIPT="$SCRIPT_DIR/simple_task_test.py"

# Clean up old log
rm -f "$LOG_FILE"

echo "Starting timing server..."
"$PYTHON_BIN" "$SERVER_SCRIPT" --log "$LOG_FILE" &
SERVER_PID=$!

# Give the server a moment to start
sleep 2

echo "Running test tasks..."
for i in {1..15}; do
    "$PYTHON_BIN" "$TEST_SCRIPT"
done

# Give the background sender threads a moment to flush
sleep 2

echo "Stopping timing server..."
kill $SERVER_PID

# Count lines in log file (excluding header)
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    # Subtract 1 for the header
    ACTUAL_COUNT=$((LINE_COUNT - 1))
    echo "Logged $ACTUAL_COUNT events."
    
    if [ "$ACTUAL_COUNT" -gt 10 ]; then
        echo "Test PASSED"
        exit 0
    else
        echo "Test FAILED: Only $ACTUAL_COUNT events logged."
        exit 1
    fi
else
    echo "Test FAILED: Log file not created."
    exit 1
fi
