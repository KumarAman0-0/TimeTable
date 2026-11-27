"""Load a Problem object from the PostgreSQL database.

Usage:
    from timetable.db_loader import load_problem
    problem = load_problem(conn)   # conn = psycopg2 connection
"""
from .models import Branch, Section, Teacher, Room, Course, Assignment, Problem


def load_problem(conn) -> Problem:
    """Read all master data from DB and return a Problem ready for the solver."""
    with conn.cursor() as cur:

        # --- Branches ---
        cur.execute("SELECT code, name, first_slot, last_slot, lunch_slot FROM branches ORDER BY id")
        branches = [Branch(r[0], r[1], r[2], r[3], r[4]) for r in cur.fetchall()]

        # --- Sections ---
        cur.execute("""
            SELECT s.id, b.code, s.name, s.strength
            FROM sections s JOIN branches b ON b.id = s.branch_id
            ORDER BY s.id
        """)
        sections = []
        sec_db_id = {}  # db int id -> str code (we use "BRANCH-name" as id)
        for row in cur.fetchall():
            db_id, branch_code, name, strength = row
            sid = f"{branch_code}-{name}"
            sec_db_id[db_id] = sid
            sections.append(Section(sid, branch_code, name, strength))

        # --- Teachers ---
        cur.execute("SELECT id, name, min_per_day, max_per_day FROM teachers ORDER BY id")
        raw_teachers = cur.fetchall()
        tea_db_id = {}  # db int id -> str id ("T<id>")
        teachers_map = {}
        for row in raw_teachers:
            db_id, name, mn, mx = row
            tid = f"T{db_id}"
            tea_db_id[db_id] = tid
            teachers_map[tid] = Teacher(tid, name, mn, mx)

        # Teacher unavailability
        cur.execute("SELECT teacher_id, day, slot FROM teacher_unavailability")
        for row in cur.fetchall():
            tid = tea_db_id.get(row[0])
            if tid and tid in teachers_map:
                teachers_map[tid].unavailable.add((row[1], row[2]))

        teachers = list(teachers_map.values())

        # --- Rooms ---
        cur.execute("SELECT id, name, room_type, capacity FROM rooms ORDER BY id")
        rooms = []
        room_db_id = {}
        for row in cur.fetchall():
            db_id, name, rtype, cap = row
            rid = f"R{db_id}"
            room_db_id[db_id] = rid
            rooms.append(Room(rid, name, rtype, cap))

        # --- Courses ---
        cur.execute("SELECT id, code, name, kind, weekly_sessions, block_periods, room_type FROM courses ORDER BY id")
        courses = []
        course_db_id = {}
        for row in cur.fetchall():
            db_id, code, name, kind, weekly, block, rtype = row
            course_db_id[db_id] = code
            courses.append(Course(code, name, kind, weekly, block, rtype))

        # --- Assignments ---
        cur.execute("""
            SELECT a.section_id, a.course_id, a.teacher_id
            FROM assignments a ORDER BY a.id
        """)
        assignments = []
        for row in cur.fetchall():
            sec_id = sec_db_id.get(row[0])
            cid    = course_db_id.get(row[1])
            tid    = tea_db_id.get(row[2])
            if sec_id and cid and tid:
                assignments.append(Assignment(sec_id, cid, tid))

    return Problem(branches, sections, teachers, rooms, courses, assignments)
