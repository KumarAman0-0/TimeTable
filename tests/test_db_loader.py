"""Tests for timetable/db_loader.py — verifies DB → Problem conversion logic.

These tests use mock DB data (no real PostgreSQL needed).

Run:
    python -m unittest tests.test_db_loader -v
"""
import unittest
from unittest.mock import MagicMock, patch, call
from timetable.models import Branch, Section, Teacher, Room, Course, Assignment, Problem


def _mock_cursor(fetch_map: dict):
    """Return a mock cursor whose fetchall/fetchone returns depend on the SQL query."""
    cur = MagicMock()
    call_count = [0]

    # We capture execute() calls and return appropriate data
    fetchall_results = iter(fetch_map.get("fetchall", [[]]))
    fetchone_results = iter(fetch_map.get("fetchone", [None]))

    cur.fetchall.side_effect = lambda: next(fetchall_results, [])
    cur.fetchone.side_effect = lambda: next(fetchone_results, None)
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    return cur


class TestDbLoader(unittest.TestCase):
    """Unit-test the db_loader module with injected mock connections."""

    def _build_mock_conn(self, branch_rows, section_rows, teacher_rows, unavail_rows,
                          room_rows, course_rows, assignment_rows):
        """Build a mock psycopg2 connection that returns fixture data."""
        conn = MagicMock()
        cur  = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__  = MagicMock(return_value=False)

        results = iter([
            branch_rows,
            section_rows,
            teacher_rows,
            unavail_rows,
            room_rows,
            course_rows,
            assignment_rows,
        ])
        cur.fetchall.side_effect = lambda: next(results, [])
        conn.cursor.return_value = cur
        return conn

    def test_branches_loaded(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn(
            branch_rows=[("CSE", "CS Engg", 0, 8, 4)],
            section_rows=[], teacher_rows=[], unavail_rows=[],
            room_rows=[], course_rows=[], assignment_rows=[]
        )
        p = load_problem(conn)
        self.assertIn("CSE", p.branches)
        b = p.branches["CSE"]
        self.assertEqual(b.name, "CS Engg")
        self.assertEqual(b.first_slot, 0)
        self.assertEqual(b.last_slot, 8)
        self.assertEqual(b.lunch_slot, 4)

    def test_sections_loaded(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn(
            branch_rows=[("CSE", "CS", 0, 8, 4)],
            section_rows=[(1, "CSE", "3rd Yr - A", 60)],
            teacher_rows=[], unavail_rows=[],
            room_rows=[], course_rows=[], assignment_rows=[]
        )
        p = load_problem(conn)
        self.assertEqual(len(p.sections), 1)
        sid = "CSE-3rd Yr - A"
        self.assertIn(sid, p.sections)
        self.assertEqual(p.sections[sid].strength, 60)

    def test_teachers_loaded(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn(
            branch_rows=[], section_rows=[],
            teacher_rows=[(1, "Dr. Sharma", 2, 5)],
            unavail_rows=[],
            room_rows=[], course_rows=[], assignment_rows=[]
        )
        p = load_problem(conn)
        self.assertIn("T1", p.teachers)
        t = p.teachers["T1"]
        self.assertEqual(t.name, "Dr. Sharma")
        self.assertEqual(t.min_per_day, 2)
        self.assertEqual(t.max_per_day, 5)

    def test_teacher_unavailability_loaded(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn(
            branch_rows=[], section_rows=[],
            teacher_rows=[(7, "Dr. Tiwari", 2, 5)],
            unavail_rows=[(7, 5, 0), (7, 5, 1)],   # Saturday slot 0 and 1 blocked
            room_rows=[], course_rows=[], assignment_rows=[]
        )
        p = load_problem(conn)
        t = p.teachers["T7"]
        self.assertIn((5, 0), t.unavailable)
        self.assertIn((5, 1), t.unavailable)

    def test_rooms_loaded(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn(
            branch_rows=[], section_rows=[], teacher_rows=[], unavail_rows=[],
            room_rows=[(1, "Room 101", "classroom", 70)],
            course_rows=[], assignment_rows=[]
        )
        p = load_problem(conn)
        self.assertIn("R1", p.rooms)
        self.assertEqual(p.rooms["R1"].capacity, 70)
        self.assertEqual(p.rooms["R1"].tag, "classroom")

    def test_courses_loaded(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn(
            branch_rows=[], section_rows=[], teacher_rows=[], unavail_rows=[],
            room_rows=[],
            course_rows=[(1, "DSA", "Data Structures", "theory", 4, 1, "classroom")],
            assignment_rows=[]
        )
        p = load_problem(conn)
        self.assertIn("DSA", p.courses)
        c = p.courses["DSA"]
        self.assertEqual(c.weekly, 4)
        self.assertEqual(c.kind, "theory")

    def test_empty_db_returns_empty_problem(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn([], [], [], [], [], [], [])
        p = load_problem(conn)
        self.assertIsInstance(p, Problem)
        self.assertEqual(len(p.branches),   0)
        self.assertEqual(len(p.sections),   0)
        self.assertEqual(len(p.teachers),   0)
        self.assertEqual(len(p.rooms),      0)
        self.assertEqual(len(p.courses),    0)
        self.assertEqual(len(p.assignments),0)

    def test_problem_type_returned(self):
        from timetable.db_loader import load_problem
        conn = self._build_mock_conn([], [], [], [], [], [], [])
        p = load_problem(conn)
        self.assertIsInstance(p, Problem)


if __name__ == "__main__":
    unittest.main(verbosity=2)
