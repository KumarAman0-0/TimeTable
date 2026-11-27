# College Timetable Generator

A constraint-based college timetable generator supporting multiple branches, sections, teachers, and rooms with clash-free scheduling.

Admin adds branches, sections, teachers, rooms/labs, courses and "who teaches what";  
the engine builds a clash-free weekly timetable in seconds.

---

## Project Structure

```
timetable_project/
├── timetable/               # Core engine (Python package)
│   ├── __init__.py
│   ├── models.py            # Data classes: Branch, Section, Teacher, Room, Course, Assignment, Entry
│   ├── sample_data.py       # Demo college: 3 branches, 5 sections, 13 teachers, 9 rooms
│   ├── solver_heuristic.py  # Randomised greedy solver (pure Python, no extra libs)
│   ├── solver_cpsat.py      # Google OR-Tools CP-SAT solver (optimal)
│   ├── validator.py         # Hard/soft constraint checker
│   └── exporter.py          # JSON + Excel export
├── db/
│   └── schema.sql           # PostgreSQL schema (clashes blocked by UNIQUE keys)
├── tests/
│   ├── __init__.py
│   └── test_solver.py       # 8 unit tests
├── docs/
│   ├── diagrams/            # ER, UseCase, Architecture, Algorithm flowchart PNGs
│   └── report/              # Mini Project Report (.docx)
├── outputs/                 # Generated timetable files (JSON, Excel)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with heuristic solver (pure Python, no extra libraries needed)
python -m timetable.main --solver heuristic --out outputs

# Run with CP-SAT solver (requires ortools, gives optimal result)
python -m timetable.main --solver cpsat --time-limit 60 --out outputs

# Run all tests
python -m unittest tests.test_solver -v
```

Outputs are saved to `outputs/timetable.json` and `outputs/timetable.xlsx`  
(one sheet per section, per teacher, and per room).

---

## Solvers

| Solver | Library | Speed | Quality |
|--------|---------|-------|---------|
| `heuristic` | None (pure Python) | Fast | Good (randomised greedy) |
| `cpsat` | `ortools` | Slower | Optimal / near-optimal |

---

## Time Model

- **Days:** Mon–Sat (6 days)  
- **Slots:** 8 global wall-clock slots (09:00–15:40, 50 min each)  
- Each branch declares its own `first_slot`, `last_slot`, and `lunch_slot`, so branches can have different timings while shared teachers/rooms are still clash-checked.

---

## Hard Constraints

- Every assignment gets exactly `weekly` sessions
- A section / teacher / room is used at most once per (day, slot)
- Sessions never cross lunch or the branch's closing time
- Room type and capacity must fit
- Teacher unavailability is respected
- Teacher daily load ≤ `max_per_day`

## Soft Constraints (minimised)

- Shortfall of teacher's minimum daily load
- Number of separate class "runs" per section/day (fewer gaps preferred)
- Late slots (early scheduling preferred)

---

## Plug In Your Own Data

Replace `build_sample()` in `timetable/sample_data.py` with a function that reads  
your database rows and returns:

```python
Problem(branches, sections, teachers, rooms, courses, assignments)
```

---

## Database

See `db/schema.sql` for the PostgreSQL schema.  
Clash-prevention is enforced at DB level via `UNIQUE (run_id, section_id, day, slot)` constraints.
