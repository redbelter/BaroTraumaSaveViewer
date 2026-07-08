#!/bin/bash
# Check reverse-baro for changes and append results to log

cd /c/Users/red/Desktop/code/reverse-baro || exit 0

STATE_FILE="/tmp/reverse-baro-schtask-state"
LOG_FILE="/c/Users/red/Desktop/code/reverse-baro/.watcher_log.txt"

# Diff current state
DIFF_OUTPUT=$(git diff --stat 2>/dev/null)
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)
BRANCH=$(git branch --show-current 2>/dev/null)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Read last state
LAST_DIFF=$(cat "$STATE_FILE" 2>/dev/null)

if [[ "$DIFF_OUTPUT" == "$LAST_DIFF" ]]; then
    exit 0
fi

# Save current state
echo "$DIFF_OUTPUT" > "$STATE_FILE"

# Run tests
TESTS=$(.venv/Scripts/python -m pytest tests/ -q 2>&1)
TEST_EXIT=$?

# Append to log
{
    echo "========== $TIMESTAMP | Branch: $BRANCH ="
    if [ $TEST_EXIT -eq 0 ]; then
        echo "✅ Tests: PASSED"
    else
        echo "🚨 Tests: FAILED"
    fi
    echo "Modified files:"
    echo "$DIFF_OUTPUT"
    if [ -n "$UNTRACKED" ]; then
        echo "Untracked:"
        echo "$UNTRACKED"
    fi
    echo "Last test count:"
    echo "$TESTS" | grep -E '[0-9]+ passed' || echo "$TESTS" | tail -2
    echo "=========="
    echo ""
} >> "$LOG_FILE"