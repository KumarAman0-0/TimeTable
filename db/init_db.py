"""Run once to initialise the database: creates all tables, admin user, and demo data.

Usage:
    cd timetable_project
    python db/init_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_db

if __name__ == "__main__":
    conn = get_db()
    conn.close()
    print("✅ Database initialised successfully (admin created & demo college data seeded).")
    print("👉 Login credentials: admin@college.edu / admin123")
