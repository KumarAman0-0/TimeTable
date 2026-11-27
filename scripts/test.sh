#!/usr/bin/env bash
# Run the automated unit test suite (51 tests)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "========================================================"
echo "🧪 Running Automated Test Suite..."
echo "========================================================"
python3 -m unittest discover -s tests -v
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "========================================================"
    echo "✅ All tests passed successfully!"
    echo "========================================================"
else
    echo "========================================================"
    echo "❌ Some tests failed. Please review output above."
    echo "========================================================"
fi

exit $EXIT_CODE
