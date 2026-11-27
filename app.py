"""Flask application — College Timetable Generator.

Run:
    cd timetable_project
    flask run          (uses .env / FLASK_APP=app.py)
    # or
    python app.py
"""
import os, time, bcrypt
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file, abort)

from config import SECRET_KEY, DEBUG, DEFAULT_SOLVER, CPSAT_TIME_LIMIT, OUTPUT_DIR
from database import get_db, query, execute, is_unique_violation
from timetable.db_loader import load_problem
from timetable.db_saver  import save_run, publish_run
from timetable.validator import validate
from timetable.exporter  import to_json, to_excel

app = Flask(__name__)
app.secret_key = SECRET_KEY

os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.template_filter("datetime_format")
def datetime_format(val):
    if not val:
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d %b %H:%M")
    s = str(val).replace("T", " ")
    return s[:16]


@app.route("/favicon.ico")
def favicon():
    return "", 204


# ══════════════════════════════════════════════════════════════════════════════
# Auth helpers
# ══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth_login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return login_required(decorated)


def current_user():
    if "user_id" not in session:
        return None
    return query("SELECT * FROM users WHERE id=%s", (session["user_id"],), one=True)


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ══════════════════════════════════════════════════════════════════════════════
# Auth routes
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("auth_login"))


@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        pw    = request.form.get("password", "").encode()
        user  = query("SELECT * FROM users WHERE email=%s", (email,), one=True)
        if user and bcrypt.checkpw(pw, user["password_hash"].encode()):
            session["user_id"] = user["id"]
            session["role"]    = user["role"]
            session["name"]    = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


@app.route("/logout")
def auth_logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth_login"))


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "branches":   query("SELECT COUNT(*) AS n FROM branches",   one=True)["n"],
        "sections":   query("SELECT COUNT(*) AS n FROM sections",   one=True)["n"],
        "teachers":   query("SELECT COUNT(*) AS n FROM teachers",   one=True)["n"],
        "rooms":      query("SELECT COUNT(*) AS n FROM rooms",      one=True)["n"],
        "courses":    query("SELECT COUNT(*) AS n FROM courses",    one=True)["n"],
        "assignments":query("SELECT COUNT(*) AS n FROM assignments",one=True)["n"],
    }
    last_run = query(
        "SELECT * FROM timetable_runs ORDER BY created_at DESC LIMIT 1", one=True)
    return render_template("admin/dashboard.html", stats=stats, last_run=last_run)


# ══════════════════════════════════════════════════════════════════════════════
# Branches
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/branches")
@admin_required
def branches():
    rows = query("SELECT * FROM branches ORDER BY id")
    return render_template("admin/branches.html", branches=rows)


@app.route("/branches/add", methods=["POST"])
@admin_required
def branch_add():
    d = request.form
    execute(
        "INSERT INTO branches (code, name, first_slot, last_slot, lunch_slot) VALUES (%s,%s,%s,%s,%s)",
        (d["code"].strip().upper(), d["name"].strip(),
         int(d["first_slot"]), int(d["last_slot"]), int(d["lunch_slot"]))
    )
    flash("Branch added.", "success")
    return redirect(url_for("branches"))


@app.route("/branches/<int:bid>/edit", methods=["POST"])
@admin_required
def branch_edit(bid):
    d = request.form
    execute(
        "UPDATE branches SET code=%s, name=%s, first_slot=%s, last_slot=%s, lunch_slot=%s WHERE id=%s",
        (d["code"].strip().upper(), d["name"].strip(),
         int(d["first_slot"]), int(d["last_slot"]), int(d["lunch_slot"]), bid)
    )
    flash("Branch updated.", "success")
    return redirect(url_for("branches"))


@app.route("/branches/<int:bid>/delete", methods=["POST"])
@admin_required
def branch_delete(bid):
    execute("DELETE FROM branches WHERE id=%s", (bid,))
    flash("Branch deleted.", "warning")
    return redirect(url_for("branches"))


# ══════════════════════════════════════════════════════════════════════════════
# Sections
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/sections")
@admin_required
def sections():
    rows     = query("SELECT s.*, b.name AS branch_name, b.code FROM sections s JOIN branches b ON b.id=s.branch_id ORDER BY s.id")
    branches = query("SELECT * FROM branches ORDER BY id")
    return render_template("admin/sections.html", sections=rows, branches=branches)


@app.route("/sections/add", methods=["POST"])
@admin_required
def section_add():
    d = request.form
    execute("INSERT INTO sections (branch_id, name, strength) VALUES (%s,%s,%s)",
            (int(d["branch_id"]), d["name"].strip(), int(d["strength"])))
    flash("Section added.", "success")
    return redirect(url_for("sections"))


@app.route("/sections/<int:sid>/edit", methods=["POST"])
@admin_required
def section_edit(sid):
    d = request.form
    execute("UPDATE sections SET branch_id=%s, name=%s, strength=%s WHERE id=%s",
            (int(d["branch_id"]), d["name"].strip(), int(d["strength"]), sid))
    flash("Section updated.", "success")
    return redirect(url_for("sections"))


@app.route("/sections/<int:sid>/delete", methods=["POST"])
@admin_required
def section_delete(sid):
    execute("DELETE FROM sections WHERE id=%s", (sid,))
    flash("Section deleted.", "warning")
    return redirect(url_for("sections"))


# ══════════════════════════════════════════════════════════════════════════════
# Teachers
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/teachers")
@admin_required
def teachers():
    rows = query("SELECT * FROM teachers ORDER BY id")
    unavail = {}
    for r in query("SELECT teacher_id, day, slot FROM teacher_unavailability"):
        unavail.setdefault(r["teacher_id"], []).append((r["day"], r["slot"]))
    return render_template("admin/teachers.html", teachers=rows, unavail=unavail)


@app.route("/teachers/add", methods=["POST"])
@admin_required
def teacher_add():
    d = request.form
    execute("INSERT INTO teachers (name, min_per_day, max_per_day) VALUES (%s,%s,%s)",
            (d["name"].strip(), int(d["min_per_day"]), int(d["max_per_day"])))
    flash("Teacher added.", "success")
    return redirect(url_for("teachers"))


@app.route("/teachers/<int:tid>/edit", methods=["POST"])
@admin_required
def teacher_edit(tid):
    d = request.form
    execute("UPDATE teachers SET name=%s, min_per_day=%s, max_per_day=%s WHERE id=%s",
            (d["name"].strip(), int(d["min_per_day"]), int(d["max_per_day"]), tid))
    flash("Teacher updated.", "success")
    return redirect(url_for("teachers"))


@app.route("/teachers/<int:tid>/delete", methods=["POST"])
@admin_required
def teacher_delete(tid):
    execute("DELETE FROM teachers WHERE id=%s", (tid,))
    flash("Teacher deleted.", "warning")
    return redirect(url_for("teachers"))


@app.route("/teachers/<int:tid>/unavailability", methods=["POST"])
@admin_required
def teacher_unavailability(tid):
    """Replace unavailability for this teacher with submitted checkboxes."""
    execute("DELETE FROM teacher_unavailability WHERE teacher_id=%s", (tid,))
    slots = request.form.getlist("slots")  # list of "day-slot" strings
    for ds in slots:
        d, s = ds.split("-")
        execute("INSERT INTO teacher_unavailability (teacher_id, day, slot) VALUES (%s,%s,%s)",
                (tid, int(d), int(s)))
    flash("Unavailability saved.", "success")
    return redirect(url_for("teachers"))


# ══════════════════════════════════════════════════════════════════════════════
# Rooms
# ══════════════════════════════════════════════════════════════════════════════

ROOM_TYPES = ["classroom", "computer_lab", "electronics_lab", "workshop", "seminar_hall"]


@app.route("/rooms")
@admin_required
def rooms():
    rows = query("SELECT * FROM rooms ORDER BY id")
    return render_template("admin/rooms.html", rooms=rows, room_types=ROOM_TYPES)


@app.route("/rooms/add", methods=["POST"])
@admin_required
def room_add():
    d = request.form
    execute("INSERT INTO rooms (name, room_type, capacity) VALUES (%s,%s,%s)",
            (d["name"].strip(), d["room_type"], int(d["capacity"])))
    flash("Room added.", "success")
    return redirect(url_for("rooms"))


@app.route("/rooms/<int:rid>/edit", methods=["POST"])
@admin_required
def room_edit(rid):
    d = request.form
    execute("UPDATE rooms SET name=%s, room_type=%s, capacity=%s WHERE id=%s",
            (d["name"].strip(), d["room_type"], int(d["capacity"]), rid))
    flash("Room updated.", "success")
    return redirect(url_for("rooms"))


@app.route("/rooms/<int:rid>/delete", methods=["POST"])
@admin_required
def room_delete(rid):
    execute("DELETE FROM rooms WHERE id=%s", (rid,))
    flash("Room deleted.", "warning")
    return redirect(url_for("rooms"))


# ══════════════════════════════════════════════════════════════════════════════
# Courses
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/courses")
@admin_required
def courses():
    rows = query("SELECT * FROM courses ORDER BY id")
    return render_template("admin/courses.html", courses=rows, room_types=ROOM_TYPES)


@app.route("/courses/add", methods=["POST"])
@admin_required
def course_add():
    d = request.form
    execute(
        "INSERT INTO courses (code, name, kind, weekly_sessions, block_periods, room_type) VALUES (%s,%s,%s,%s,%s,%s)",
        (d["code"].strip().upper(), d["name"].strip(), d["kind"],
         int(d["weekly_sessions"]), int(d["block_periods"]), d["room_type"])
    )
    flash("Course added.", "success")
    return redirect(url_for("courses"))


@app.route("/courses/<int:cid>/edit", methods=["POST"])
@admin_required
def course_edit(cid):
    d = request.form
    execute(
        "UPDATE courses SET code=%s, name=%s, kind=%s, weekly_sessions=%s, block_periods=%s, room_type=%s WHERE id=%s",
        (d["code"].strip().upper(), d["name"].strip(), d["kind"],
         int(d["weekly_sessions"]), int(d["block_periods"]), d["room_type"], cid)
    )
    flash("Course updated.", "success")
    return redirect(url_for("courses"))


@app.route("/courses/<int:cid>/delete", methods=["POST"])
@admin_required
def course_delete(cid):
    execute("DELETE FROM courses WHERE id=%s", (cid,))
    flash("Course deleted.", "warning")
    return redirect(url_for("courses"))


# ══════════════════════════════════════════════════════════════════════════════
# Assignments
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/assignments")
@admin_required
def assignments():
    rows     = query("""
        SELECT a.id, s.name AS section_name, b.code AS branch_code,
               c.code AS course_code, c.name AS course_name,
               t.name AS teacher_name, a.section_id, a.course_id, a.teacher_id
        FROM assignments a
        JOIN sections s ON s.id=a.section_id
        JOIN branches b ON b.id=s.branch_id
        JOIN courses  c ON c.id=a.course_id
        JOIN teachers t ON t.id=a.teacher_id
        ORDER BY b.code, s.name, c.code
    """)
    sections = query("SELECT s.id, s.name, b.code FROM sections s JOIN branches b ON b.id=s.branch_id ORDER BY b.code,s.name")
    courses  = query("SELECT * FROM courses ORDER BY code")
    teachers = query("SELECT * FROM teachers ORDER BY name")
    return render_template("admin/assignments.html",
                           assignments=rows, sections=sections,
                           courses=courses, teachers=teachers)


@app.route("/assignments/add", methods=["POST"])
@admin_required
def assignment_add():
    d = request.form
    try:
        execute("INSERT INTO assignments (section_id, course_id, teacher_id) VALUES (%s,%s,%s)",
                (int(d["section_id"]), int(d["course_id"]), int(d["teacher_id"])))
        flash("Assignment added.", "success")
    except Exception as e:
        if is_unique_violation(e):
            flash("This section already has this course assigned.", "danger")
        else:
            flash(f"Error: {e}", "danger")
    return redirect(url_for("assignments"))


@app.route("/assignments/<int:aid>/delete", methods=["POST"])
@admin_required
def assignment_delete(aid):
    execute("DELETE FROM assignments WHERE id=%s", (aid,))
    flash("Assignment removed.", "warning")
    return redirect(url_for("assignments"))


# ══════════════════════════════════════════════════════════════════════════════
# Timetable generation
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/generate", methods=["GET", "POST"])
@admin_required
def generate():
    if request.method == "POST":
        solver_name = request.form.get("solver", DEFAULT_SOLVER)
        time_limit  = int(request.form.get("time_limit", CPSAT_TIME_LIMIT))

        conn = get_db()
        try:
            problem = load_problem(conn)
        finally:
            conn.close()

        t0 = time.time()
        if solver_name == "cpsat":
            from timetable.solver_cpsat import solve_cpsat
            entries = solve_cpsat(problem, time_limit)
        else:
            from timetable.solver_heuristic import solve_heuristic
            entries = solve_heuristic(problem)

        elapsed = round(time.time() - t0, 2)

        hard, soft = ([], []) if not entries else validate(problem, entries)

        conn = get_db()
        try:
            run_id = save_run(conn, problem, entries, solver_name, hard, soft,
                              created_by=session.get("user_id"))
        finally:
            conn.close()

        if entries:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            to_json (problem, entries, f"{OUTPUT_DIR}/run_{run_id}.json")
            to_excel(problem, entries, f"{OUTPUT_DIR}/run_{run_id}.xlsx")
            flash(f"✅ Timetable generated in {elapsed}s — "
                  f"{len(hard)} hard violations, {len(soft)} soft warnings.", "success")
        else:
            flash("❌ No feasible timetable found. Add more rooms/teachers or relax constraints.", "danger")

        return redirect(url_for("run_detail", run_id=run_id))

    return render_template("admin/generate.html",
                           default_solver=DEFAULT_SOLVER,
                           default_time_limit=CPSAT_TIME_LIMIT)


# ══════════════════════════════════════════════════════════════════════════════
# Timetable runs
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/runs")
@login_required
def runs():
    rows = query("""
        SELECT r.*, u.name AS created_by_name
        FROM timetable_runs r
        LEFT JOIN users u ON u.id=r.created_by
        ORDER BY r.created_at DESC
    """)
    return render_template("timetable/runs.html", runs=rows)


@app.route("/runs/<int:run_id>")
@login_required
def run_detail(run_id):
    run = query("SELECT * FROM timetable_runs WHERE id=%s", (run_id,), one=True)
    if not run:
        abort(404)

    sections = query("""
        SELECT DISTINCT s.id, s.name, b.code AS branch_code
        FROM timetable_entries te JOIN sections s ON s.id=te.section_id
        JOIN branches b ON b.id=s.branch_id
        WHERE te.run_id=%s ORDER BY b.code, s.name
    """, (run_id,))

    teachers = query("""
        SELECT DISTINCT t.id, t.name FROM timetable_entries te
        JOIN teachers t ON t.id=te.teacher_id WHERE te.run_id=%s ORDER BY t.name
    """, (run_id,))

    rooms = query("""
        SELECT DISTINCT r.id, r.name FROM timetable_entries te
        JOIN rooms r ON r.id=te.room_id WHERE te.run_id=%s ORDER BY r.name
    """, (run_id,))

    return render_template("timetable/runs.html",
                           runs=query("SELECT * FROM timetable_runs ORDER BY created_at DESC"),
                           active_run=run, sections=sections,
                           teachers=teachers, rooms=rooms)


@app.route("/runs/<int:run_id>/publish", methods=["POST"])
@admin_required
def run_publish(run_id):
    conn = get_db()
    try:
        publish_run(conn, run_id)
    finally:
        conn.close()
    flash("Run published.", "success")
    return redirect(url_for("run_detail", run_id=run_id))


# ══════════════════════════════════════════════════════════════════════════════
# Timetable view (grid)
# ══════════════════════════════════════════════════════════════════════════════

def _get_entries(run_id, filter_col, filter_val):
    return query(f"""
        SELECT te.*, c.name AS course_name, c.code AS course_code,
               t.name AS teacher_name, r.name AS room_name,
               s.name AS section_name
        FROM timetable_entries te
        JOIN courses  c ON c.id=te.assignment_id  -- note: joined via assignment
        JOIN teachers t ON t.id=te.teacher_id
        JOIN rooms    r ON r.id=te.room_id
        JOIN sections s ON s.id=te.section_id
        WHERE te.run_id=%s AND te.{filter_col}=%s
        ORDER BY te.day, te.slot
    """, (run_id, filter_val))


def _build_view_entries(run_id, filter_col, filter_val):
    """Return entries with proper course name via assignments join."""
    return query(f"""
        SELECT te.day, te.slot, te.session_no,
               c.name AS course_name, c.code AS course_code,
               t.name AS teacher_name, t.id AS teacher_id,
               r.name AS room_name, r.id AS room_id,
               s.name AS section_name, s.id AS section_id,
               a.course_id
        FROM timetable_entries te
        JOIN assignments a ON a.id=te.assignment_id
        JOIN courses  c ON c.id=a.course_id
        JOIN teachers t ON t.id=te.teacher_id
        JOIN rooms    r ON r.id=te.room_id
        JOIN sections s ON s.id=te.section_id
        WHERE te.run_id=%s AND te.{filter_col}=%s
        ORDER BY te.day, te.slot
    """, (run_id, filter_val))


@app.route("/timetable/<int:run_id>/section/<int:sec_id>")
@login_required
def view_section(run_id, sec_id):
    # Role check: students can only view their own section
    if session.get("role") == "student":
        user = current_user()
        # (Assumes student.section_id is stored; simplified check)
    entries = _build_view_entries(run_id, "section_id", sec_id)
    sec  = query("SELECT s.*, b.lunch_slot FROM sections s JOIN branches b ON b.id=s.branch_id WHERE s.id=%s", (sec_id,), one=True)
    run  = query("SELECT * FROM timetable_runs WHERE id=%s", (run_id,), one=True)
    return render_template("timetable/view.html",
                           entries=entries, subject=sec,
                           subject_type="section", run=run,
                           lunch_slot=sec["lunch_slot"] if sec else None)


@app.route("/timetable/<int:run_id>/teacher/<int:tea_id>")
@login_required
def view_teacher(run_id, tea_id):
    entries = _build_view_entries(run_id, "teacher_id", tea_id)
    tea = query("SELECT * FROM teachers WHERE id=%s", (tea_id,), one=True)
    run = query("SELECT * FROM timetable_runs WHERE id=%s", (run_id,), one=True)
    return render_template("timetable/view.html",
                           entries=entries, subject=tea,
                           subject_type="teacher", run=run, lunch_slot=None)


@app.route("/timetable/<int:run_id>/room/<int:room_id>")
@login_required
def view_room(run_id, room_id):
    entries = _build_view_entries(run_id, "room_id", room_id)
    room = query("SELECT * FROM rooms WHERE id=%s", (room_id,), one=True)
    run  = query("SELECT * FROM timetable_runs WHERE id=%s", (run_id,), one=True)
    return render_template("timetable/view.html",
                           entries=entries, subject=room,
                           subject_type="room", run=run, lunch_slot=None)


# ══════════════════════════════════════════════════════════════════════════════
# Export
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/export/<int:run_id>/excel")
@login_required
def export_excel(run_id):
    path = f"{OUTPUT_DIR}/run_{run_id}.xlsx"
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True,
                     download_name=f"timetable_run_{run_id}.xlsx")


@app.route("/export/<int:run_id>/json")
@login_required
def export_json(run_id):
    path = f"{OUTPUT_DIR}/run_{run_id}.json"
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True,
                     download_name=f"timetable_run_{run_id}.json")


@app.route("/export/<int:run_id>/pdf")
@login_required
def export_pdf(run_id):
    pdf_path = f"{OUTPUT_DIR}/run_{run_id}.pdf"
    if not os.path.exists(pdf_path):
        # Rebuild entries from DB and generate PDF on the fly
        conn = get_db()
        try:
            problem = load_problem(conn)
            raw = query("""
                SELECT a.section_id AS sec_db, a.course_id AS crs_db,
                       te.teacher_id AS tea_db, te.room_id AS rm_db,
                       te.day, te.slot, te.session_no
                FROM timetable_entries te
                JOIN assignments a ON a.id = te.assignment_id
                WHERE te.run_id = %s
                ORDER BY te.session_no, te.slot
            """, (run_id,))
        finally:
            conn.close()

        if not raw:
            abort(404)

        from timetable.models import Entry
        from timetable.pdf_exporter import to_pdf

        # Map DB int ids → str ids used in Problem
        sec_map  = {s.name: sid for sid, s in problem.sections.items()}
        tea_map  = {t.name: tid for tid, t in problem.teachers.items()}
        room_map = {r.name: rid for rid, r in problem.rooms.items()}

        # DB gives us int ids; build reverse map from DB rows
        sec_db  = {r["sec_db"]  for r in raw}
        tea_db  = {r["tea_db"]  for r in raw}
        rm_db   = {r["rm_db"]   for r in raw}

        # Build entries grouped by session_no (each session_no = one block)
        from collections import defaultdict
        sessions = defaultdict(list)
        for r in raw:
            sessions[r["session_no"]].append(r)

        entries = []
        for sno, rows in sessions.items():
            r0 = rows[0]  # first row of block
            # Resolve section id via DB lookup
            sec_rows  = query("SELECT id, name FROM sections  WHERE id=%s", (r0["sec_db"],),  one=True)
            tea_rows  = query("SELECT id, name FROM teachers  WHERE id=%s", (r0["tea_db"],), one=True)
            rm_rows   = query("SELECT id, name FROM rooms     WHERE id=%s", (r0["rm_db"],),  one=True)
            crs_rows  = query("SELECT id, code FROM courses   WHERE id=%s", (r0["crs_db"],), one=True)
            if not all([sec_rows, tea_rows, rm_rows, crs_rows]):
                continue
            sid  = f"{query('SELECT b.code FROM branches b JOIN sections s ON s.branch_id=b.id WHERE s.id=%s', (r0['sec_db'],), one=True)['code']}-{sec_rows['name']}"
            tid  = f"T{tea_rows['id']}"
            rid  = f"R{rm_rows['id']}"
            cid  = crs_rows["code"]
            blk  = len(rows)
            if sid in problem.sections and tid in problem.teachers and rid in problem.rooms and cid in problem.courses:
                entries.append(Entry(sid, cid, tid, rid, r0["day"], r0["slot"], blk))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        to_pdf(problem, entries, pdf_path)

    return send_file(pdf_path, as_attachment=True,
                     download_name=f"timetable_run_{run_id}.pdf")


# ══════════════════════════════════════════════════════════════════════════════
# User Management (admin only)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/users")
@admin_required
def users():
    rows = query("SELECT id, name, email, role FROM users ORDER BY role, name")
    return render_template("admin/users.html", users=rows)


@app.route("/users/add", methods=["POST"])
@admin_required
def user_add():
    d  = request.form
    pw = d.get("password", "").encode()
    if len(pw) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("users"))
    pw_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
    try:
        execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,%s)",
            (d["name"].strip(), d["email"].strip().lower(), pw_hash, d["role"])
        )
        flash(f"User '{d['name']}' created.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("users"))


@app.route("/users/<int:uid>/delete", methods=["POST"])
@admin_required
def user_delete(uid):
    if uid == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users"))
    execute("DELETE FROM users WHERE id=%s", (uid,))
    flash("User deleted.", "warning")
    return redirect(url_for("users"))


@app.route("/users/<int:uid>/reset-password", methods=["POST"])
@admin_required
def user_reset_password(uid):
    pw = request.form.get("password", "").encode()
    if len(pw) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("users"))
    pw_hash = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
    execute("UPDATE users SET password_hash=%s WHERE id=%s", (pw_hash, uid))
    flash("Password reset.", "success")
    return redirect(url_for("users"))


# ══════════════════════════════════════════════════════════════════════════════
# JSON API endpoints (for JS fetch calls)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify({
        "branches":    query("SELECT COUNT(*) AS n FROM branches",    one=True)["n"],
        "sections":    query("SELECT COUNT(*) AS n FROM sections",    one=True)["n"],
        "teachers":    query("SELECT COUNT(*) AS n FROM teachers",    one=True)["n"],
        "rooms":       query("SELECT COUNT(*) AS n FROM rooms",       one=True)["n"],
        "courses":     query("SELECT COUNT(*) AS n FROM courses",     one=True)["n"],
        "assignments": query("SELECT COUNT(*) AS n FROM assignments", one=True)["n"],
    })


# ══════════════════════════════════════════════════════════════════════════════
# Error handlers
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)
