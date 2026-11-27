"""Load a Problem object from the PostgreSQL database.

Usage:
    from timetable.db_loader import load_problem
    problem = load_problem(conn)   # conn = psycopg2 connection
"""
from typing import List, Optional
from .models import Branch, Section, Teacher, Room, Course, Assignment, Problem


def load_problem(conn, branch_ids: Optional[List[int]] = None) -> Problem:
    """Read master data from DB and return a Problem ready for the solver.
    
    If branch_ids is provided, loads only branches, sections, and assignments
    belonging to those branches, while ensuring shared teachers and rooms
    respect constraints.
    """
    with conn.cursor() as cur:

        # --- Branches ---
        if branch_ids:
            ph = ",".join(["%s"] * len(branch_ids))
            cur.execute(f"SELECT code, name, first_slot, last_slot, lunch_slot FROM branches WHERE id IN ({ph}) ORDER BY id", tuple(branch_ids))
        else:
            cur.execute("SELECT code, name, first_slot, last_slot, lunch_slot FROM branches ORDER BY id")
        branches = [Branch(r[0], r[1], r[2], r[3], r[4]) for r in cur.fetchall()]

        # --- Sections ---
        if branch_ids:
            ph = ",".join(["%s"] * len(branch_ids))
            cur.execute(f"""
                SELECT s.id, b.code, s.name, s.strength
                FROM sections s JOIN branches b ON b.id = s.branch_id
                WHERE b.id IN ({ph})
                ORDER BY s.id
            """, tuple(branch_ids))
        else:
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

        # Prevent clashes with other already published branch timetables
        if branch_ids:
            try:
                ph = ",".join(["%s"] * len(branch_ids))
                cur.execute(f"""
                    SELECT te.teacher_id, te.day, te.slot
                    FROM timetable_entries te
                    JOIN timetable_runs tr ON tr.id = te.run_id
                    JOIN sections s ON s.id = te.section_id
                    WHERE tr.status = 'published' AND s.branch_id NOT IN ({ph})
                """, tuple(branch_ids))
                for brow in cur.fetchall():
                    tid = tea_db_id.get(brow[0])
                    if tid and tid in teachers_map:
                        teachers_map[tid].unavailable.add((brow[1], brow[2]))
            except Exception:
                pass

        teachers = list(teachers_map.values())

        # --- Rooms ---
        cur.execute("""
            SELECT r.id, r.name, r.room_type, r.capacity, b.code, r.department
            FROM rooms r
            LEFT JOIN branches b ON b.id = r.branch_id
            ORDER BY r.id
        """)
        rooms = []
        room_db_id = {}
        for row in cur.fetchall():
            db_id = row[0]
            name  = row[1]
            rtype = row[2]
            cap   = row[3]
            bcode = row[4] if len(row) > 4 else None
            dept  = row[5] if len(row) > 5 else None
            rid = f"R{db_id}"
            room_db_id[db_id] = rid
            rooms.append(Room(rid, name, rtype, cap, bcode, dept))

        # --- Courses ---
        cur.execute("SELECT id, code, name, kind, weekly_sessions, block_periods, room_type FROM courses ORDER BY id")
        courses = []
        course_db_id = {}
        for row in cur.fetchall():
            db_id, code, name, kind, weekly, block, rtype = row
            course_db_id[db_id] = code
            courses.append(Course(code, name, kind, weekly, block, rtype))

        # --- Assignments ---
        if branch_ids:
            ph = ",".join(["%s"] * len(branch_ids))
            cur.execute(f"""
                SELECT a.section_id, a.course_id, a.teacher_id
                FROM assignments a
                JOIN sections s ON s.id = a.section_id
                WHERE s.branch_id IN ({ph})
                ORDER BY a.id
            """, tuple(branch_ids))
        else:
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
