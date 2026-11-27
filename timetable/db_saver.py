"""Save solved timetable entries back to the database.

Usage:
    from timetable.db_saver import save_run
    run_id = save_run(conn, problem, entries, solver_name, hard, soft, created_by_user_id)
"""
from .models import Problem, Entry


def save_run(conn, problem: Problem, entries: list[Entry],
             solver: str, hard: list, soft: list,
             created_by: int | None = None) -> int:
    """Insert a timetable_run row and all entry rows. Returns the new run_id."""
    status = "failed" if entries is None else ("draft" if hard else "draft")

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO timetable_runs
               (created_by, solver, status, hard_violations, soft_warnings)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (created_by, solver, status, len(hard), len(soft))
        )
        run_id = cur.fetchone()[0]

        if entries:
            # Resolve DB integer ids
            sec_ids   = _lookup(cur, "sections",  "name",      "id")
            tea_ids   = _lookup(cur, "teachers",  "name",      "id")
            room_ids  = _lookup(cur, "rooms",     "name",      "id")
            course_ids= _lookup(cur, "courses",   "code",      "id")
            asg_ids   = _lookup_assignments(cur)

            rows = []
            for i, e in enumerate(entries):
                sec_name  = problem.sections[e.section_id].name
                tea_name  = problem.teachers[e.teacher_id].name
                room_name = problem.rooms[e.room_id].name
                course_code = e.course_id

                sec_id_db  = sec_ids.get(sec_name)
                tea_id_db  = tea_ids.get(tea_name)
                room_id_db = room_ids.get(room_name)
                cid_db     = course_ids.get(course_code)
                asg_key    = (sec_id_db, cid_db)
                asg_id_db  = asg_ids.get(asg_key)

                if None in (sec_id_db, tea_id_db, room_id_db, cid_db, asg_id_db):
                    continue  # skip unresolvable (should not happen with valid data)

                for k in range(e.block):
                    rows.append((run_id, i, asg_id_db, sec_id_db,
                                 tea_id_db, room_id_db, e.day, e.slot + k))

            cur.executemany(
                """INSERT INTO timetable_entries
                   (run_id, session_no, assignment_id, section_id,
                    teacher_id, room_id, day, slot)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                rows
            )

    conn.commit()
    return run_id


def publish_run(conn, run_id: int):
    with conn.cursor() as cur:
        cur.execute("UPDATE timetable_runs SET status='published' WHERE id=%s", (run_id,))
    conn.commit()


# ── helpers ──────────────────────────────────────────────────────────────────

def _lookup(cur, table, name_col, id_col):
    cur.execute(f"SELECT {name_col}, {id_col} FROM {table}")
    return {r[0]: r[1] for r in cur.fetchall()}


def _lookup_assignments(cur):
    cur.execute("SELECT section_id, course_id, id FROM assignments")
    return {(r[0], r[1]): r[2] for r in cur.fetchall()}
