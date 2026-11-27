-- College Timetable Generator : PostgreSQL schema
-- Time model: day 0..5 = Mon..Sat, slot 0..7 = fixed wall-clock periods.

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(10)  NOT NULL CHECK (role IN ('admin','teacher','student'))
);

CREATE TABLE branches (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) UNIQUE NOT NULL,          -- CSE, ECE, ME
    name        VARCHAR(100) NOT NULL,
    first_slot  SMALLINT NOT NULL DEFAULT 0,
    last_slot   SMALLINT NOT NULL DEFAULT 8,          -- exclusive
    lunch_slot  SMALLINT NOT NULL DEFAULT 4,
    CHECK (first_slot <= lunch_slot AND lunch_slot < last_slot)
);

CREATE TABLE sections (
    id          SERIAL PRIMARY KEY,
    branch_id   INT NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    name        VARCHAR(30) NOT NULL,                 -- "3rd Yr - A"
    strength    INT NOT NULL CHECK (strength > 0),
    UNIQUE (branch_id, name)
);

CREATE TABLE teachers (
    id            SERIAL PRIMARY KEY,
    user_id       INT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    name          VARCHAR(100) NOT NULL,
    min_per_day   SMALLINT NOT NULL DEFAULT 0,
    max_per_day   SMALLINT NOT NULL DEFAULT 5,
    department    VARCHAR(100) DEFAULT NULL,
    branch_id     INT REFERENCES branches(id) ON DELETE SET NULL,
    specialization VARCHAR(100) DEFAULT NULL,
    CHECK (min_per_day <= max_per_day)
);

CREATE TABLE teacher_unavailability (
    teacher_id  INT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    day         SMALLINT NOT NULL CHECK (day BETWEEN 0 AND 5),
    slot        SMALLINT NOT NULL CHECK (slot BETWEEN 0 AND 7),
    PRIMARY KEY (teacher_id, day, slot)
);

CREATE TABLE rooms (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(50) UNIQUE NOT NULL,
    room_type VARCHAR(30) NOT NULL DEFAULT 'classroom',  -- classroom, computer_lab, ...
    capacity  INT NOT NULL CHECK (capacity > 0)
);

CREATE TABLE courses (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    kind            VARCHAR(10) NOT NULL CHECK (kind IN ('theory','lab')),
    weekly_sessions SMALLINT NOT NULL CHECK (weekly_sessions > 0),
    block_periods   SMALLINT NOT NULL DEFAULT 1 CHECK (block_periods BETWEEN 1 AND 4),
    room_type       VARCHAR(30) NOT NULL DEFAULT 'classroom'
);

-- "Which teacher teaches which course to which section"
CREATE TABLE assignments (
    id          SERIAL PRIMARY KEY,
    section_id  INT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    course_id   INT NOT NULL REFERENCES courses(id)  ON DELETE CASCADE,
    teacher_id  INT NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT,
    UNIQUE (section_id, course_id)
);

CREATE TABLE timetable_runs (
    id               SERIAL PRIMARY KEY,
    created_by       INT REFERENCES users(id),
    created_at       TIMESTAMP NOT NULL DEFAULT now(),
    solver           VARCHAR(20) NOT NULL,              -- heuristic | cpsat
    status           VARCHAR(20) NOT NULL,              -- draft | published | failed
    hard_violations  INT NOT NULL DEFAULT 0,
    soft_warnings    INT NOT NULL DEFAULT 0,
    scope            VARCHAR(50) NOT NULL DEFAULT 'All Branches'
);

-- One row per OCCUPIED period (a 2-period lab = 2 rows with the same session_no).
-- The UNIQUE constraints make clashes impossible at database level.
CREATE TABLE timetable_entries (
    id            SERIAL PRIMARY KEY,
    run_id        INT NOT NULL REFERENCES timetable_runs(id) ON DELETE CASCADE,
    session_no    INT NOT NULL,
    assignment_id INT NOT NULL REFERENCES assignments(id),
    section_id    INT NOT NULL REFERENCES sections(id),
    teacher_id    INT NOT NULL REFERENCES teachers(id),
    room_id       INT NOT NULL REFERENCES rooms(id),
    day           SMALLINT NOT NULL CHECK (day BETWEEN 0 AND 5),
    slot          SMALLINT NOT NULL CHECK (slot BETWEEN 0 AND 7),
    UNIQUE (run_id, section_id, day, slot),
    UNIQUE (run_id, teacher_id, day, slot),
    UNIQUE (run_id, room_id,    day, slot)
);

CREATE INDEX idx_entries_run     ON timetable_entries(run_id);
CREATE INDEX idx_entries_teacher ON timetable_entries(run_id, teacher_id);
