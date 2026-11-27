"""Database abstraction layer supporting both SQLite (built-in, zero setup)
and PostgreSQL (production).

If PostgreSQL is not running or DATABASE_URL starts with sqlite,
it automatically uses SQLite and creates/seeds tables on first access.
"""
import os
import sqlite3
import bcrypt
from config import DATABASE_URL

# Check if psycopg2 is available
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.errors
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False

DB_FILE = os.path.join(os.path.dirname(__file__), "timetable.db")


# ── SQLite Wrappers ──────────────────────────────────────────────────────────

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=()):
        if "%s" in sql:
            sql = sql.replace("%s", "?")
        return self.cursor.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        if "%s" in sql:
            sql = sql.replace("%s", "?")
        return self.cursor.executemany(sql, seq_of_params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        return self.cursor.lastrowid


class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


# ── Connection Provider ──────────────────────────────────────────────────────

_initialized = False


def _get_raw_connection():
    """Attempt to connect to PostgreSQL if configured, otherwise use SQLite."""
    use_postgres = (
        DATABASE_URL.startswith("postgresql://")
        or DATABASE_URL.startswith("postgres://")
    )

    if use_postgres and HAS_PSYCOPG2:
        try:
            return psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=3
            )
        except Exception:
            # PostgreSQL connection failed, fall back to SQLite
            pass

    # SQLite connection
    if DATABASE_URL.startswith("sqlite:///"):
        path = DATABASE_URL.replace("sqlite:///", "")
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), path)
    else:
        path = DB_FILE

    raw = sqlite3.connect(path)
    return SQLiteConnectionWrapper(raw)


def get_db():
    global _initialized
    conn = _get_raw_connection()
    if not _initialized:
        _auto_init(conn)
        _initialized = True
    return conn


def is_unique_violation(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return "UNIQUE" in str(exc).upper()
    if HAS_PSYCOPG2 and isinstance(exc, psycopg2.errors.UniqueViolation):
        return True
    return "unique" in str(exc).lower()


# ── Query & Execute Helpers ──────────────────────────────────────────────────

def query(sql, params=(), one=False):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            try:
                res = cur.fetchone()
            except Exception:
                res = None
        conn.commit()
        return res
    finally:
        conn.close()


# ── Schema & Seed Data ───────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin','teacher','student'))
);

CREATE TABLE IF NOT EXISTS branches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    first_slot  INTEGER NOT NULL DEFAULT 0,
    last_slot   INTEGER NOT NULL DEFAULT 8,
    lunch_slot  INTEGER NOT NULL DEFAULT 4,
    CHECK (first_slot <= lunch_slot AND lunch_slot < last_slot)
);

CREATE TABLE IF NOT EXISTS sections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id   INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    strength    INTEGER NOT NULL CHECK (strength > 0),
    UNIQUE (branch_id, name)
);

CREATE TABLE IF NOT EXISTS teachers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    name          TEXT NOT NULL,
    min_per_day   INTEGER NOT NULL DEFAULT 0,
    max_per_day   INTEGER NOT NULL DEFAULT 5,
    department    TEXT DEFAULT NULL,
    branch_id     INTEGER REFERENCES branches(id) ON DELETE SET NULL,
    specialization TEXT DEFAULT NULL,
    CHECK (min_per_day <= max_per_day)
);

CREATE TABLE IF NOT EXISTS teacher_unavailability (
    teacher_id  INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    day         INTEGER NOT NULL CHECK (day BETWEEN 0 AND 5),
    slot        INTEGER NOT NULL CHECK (slot BETWEEN 0 AND 7),
    PRIMARY KEY (teacher_id, day, slot)
);

CREATE TABLE IF NOT EXISTS rooms (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT UNIQUE NOT NULL,
    room_type TEXT NOT NULL DEFAULT 'classroom',
    capacity  INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE IF NOT EXISTS courses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('theory','lab')),
    weekly_sessions INTEGER NOT NULL CHECK (weekly_sessions > 0),
    block_periods   INTEGER NOT NULL DEFAULT 1 CHECK (block_periods BETWEEN 1 AND 4),
    room_type       TEXT NOT NULL DEFAULT 'classroom'
);

CREATE TABLE IF NOT EXISTS assignments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id  INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    course_id   INTEGER NOT NULL REFERENCES courses(id)  ON DELETE CASCADE,
    teacher_id  INTEGER NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT,
    UNIQUE (section_id, course_id)
);

CREATE TABLE IF NOT EXISTS timetable_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by       INTEGER REFERENCES users(id),
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    solver           TEXT NOT NULL,
    status           TEXT NOT NULL,
    hard_violations  INTEGER NOT NULL DEFAULT 0,
    soft_warnings    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS timetable_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL REFERENCES timetable_runs(id) ON DELETE CASCADE,
    session_no    INTEGER NOT NULL,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id),
    section_id    INTEGER NOT NULL REFERENCES sections(id),
    teacher_id    INTEGER NOT NULL REFERENCES teachers(id),
    room_id       INTEGER NOT NULL REFERENCES rooms(id),
    day           INTEGER NOT NULL CHECK (day BETWEEN 0 AND 5),
    slot          INTEGER NOT NULL CHECK (slot BETWEEN 0 AND 7),
    UNIQUE (run_id, section_id, day, slot),
    UNIQUE (run_id, teacher_id, day, slot),
    UNIQUE (run_id, room_id,    day, slot)
);

CREATE INDEX IF NOT EXISTS idx_entries_run     ON timetable_entries(run_id);
CREATE INDEX IF NOT EXISTS idx_entries_teacher ON timetable_entries(run_id, teacher_id);
"""


def _auto_init(conn):
    """Run schema creation, seed admin user and default demo college data if table is empty."""
    with conn.cursor() as cur:
        # Check if users table exists
        if isinstance(conn, SQLiteConnectionWrapper):
            for statement in SCHEMA_SQL.split(";"):
                stmt = statement.strip()
                if stmt:
                    cur.execute(stmt)
        else:
            # PostgreSQL schema
            schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
            if os.path.exists(schema_path):
                with open(schema_path) as f:
                    cur.execute(f.read())

        # Ensure migration columns exist in teachers table
        for col, col_type in [("department", "TEXT"), ("branch_id", "INTEGER"), ("specialization", "TEXT")]:
            try:
                cur.execute(f"SELECT {col} FROM teachers LIMIT 1")
            except Exception:
                try:
                    cur.execute(f"ALTER TABLE teachers ADD COLUMN {col} {col_type} DEFAULT NULL")
                except Exception:
                    pass

        # Seed admin user
        cur.execute("SELECT id FROM users WHERE email=%s", ("admin@college.edu",))
        if not cur.fetchone():
            pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,%s)",
                ("Administrator", "admin@college.edu", pw_hash, "admin")
            )

        # Seed demo data if branches is empty
        cur.execute("SELECT COUNT(*) FROM branches")
        row = cur.fetchone()
        count = row[0] if row else 0
        if count == 0:
            _seed_demo_data(cur)

    conn.commit()


def _seed_demo_data(cur):
    """Seed the standard college demo data into the database."""
    from timetable.sample_data import build_sample
    problem = build_sample()

    for b in problem.branches.values():
        cur.execute(
            "INSERT INTO branches (code, name, first_slot, last_slot, lunch_slot) VALUES (%s,%s,%s,%s,%s)",
            (b.id, b.name, b.first_slot, b.last_slot, b.lunch_slot)
        )

    for s in problem.sections.values():
        cur.execute("SELECT id FROM branches WHERE code=%s", (s.branch_id,))
        bid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO sections (branch_id, name, strength) VALUES (%s,%s,%s)",
            (bid, s.name, s.strength)
        )

    tea_id_map = {}
    for t in problem.teachers.values():
        cur.execute(
            "INSERT INTO teachers (name, min_per_day, max_per_day) VALUES (%s,%s,%s) RETURNING id",
            (t.name, t.min_per_day, t.max_per_day)
        )
        tid = cur.fetchone()[0]
        tea_id_map[t.id] = tid
        for d, slot in t.unavailable:
            cur.execute(
                "INSERT INTO teacher_unavailability (teacher_id, day, slot) VALUES (%s,%s,%s)",
                (tid, d, slot)
            )

    for r in problem.rooms.values():
        cur.execute(
            "INSERT INTO rooms (name, room_type, capacity) VALUES (%s,%s,%s)",
            (r.name, r.tag, r.capacity)
        )

    for c in problem.courses.values():
        cur.execute(
            "INSERT INTO courses (code, name, kind, weekly_sessions, block_periods, room_type) VALUES (%s,%s,%s,%s,%s,%s)",
            (c.id, c.name, c.kind, c.weekly, c.block, c.room_tag)
        )

    for a in problem.assignments:
        sec_name = problem.sections[a.section_id].name
        cur.execute("SELECT s.id FROM sections s WHERE s.name=%s", (sec_name,))
        sid = cur.fetchone()[0]
        cur.execute("SELECT id FROM courses WHERE code=%s", (a.course_id,))
        cid = cur.fetchone()[0]
        tid = tea_id_map[a.teacher_id]
        cur.execute(
            "INSERT INTO assignments (section_id, course_id, teacher_id) VALUES (%s,%s,%s)",
            (sid, cid, tid)
        )
