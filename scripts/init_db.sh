#!/usr/bin/env bash
# Reset and re-seed the SQLite/PostgreSQL database with standard demo data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "========================================================"
echo "📦 Initializing and Seeding Database..."
echo "========================================================"
python3 -c '
from database import get_db, query
conn = get_db()
conn.close()
print("✓ Database tables verified and seeded successfully.")
b_count = query("SELECT COUNT(*) FROM branches", one=True)[0]
s_count = query("SELECT COUNT(*) FROM sections", one=True)[0]
t_count = query("SELECT COUNT(*) FROM teachers", one=True)[0]
r_count = query("SELECT COUNT(*) FROM rooms", one=True)[0]
c_count = query("SELECT COUNT(*) FROM courses", one=True)[0]
a_count = query("SELECT COUNT(*) FROM assignments", one=True)[0]
print(f"✓ Stats: {b_count} branches, {s_count} sections, {t_count} teachers, {r_count} rooms, {c_count} courses, {a_count} assignments.")
'
