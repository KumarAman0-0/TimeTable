#!/usr/bin/env bash
# Start the Timetable Generator web application
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "========================================================"
echo "⚡ Starting College Timetable Generator Web Application"
echo "🌐 URL: http://localhost:5000"
echo "🔑 Default Admin: admin@college.edu / admin123"
echo "========================================================"
python3 app.py
