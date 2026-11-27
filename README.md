# 🎓 College Timetable Generator

An automated, constraint-based College Timetable Generator web application and solver engine. Built with **Python, Flask, Google OR-Tools (CP-SAT), and SQLite/PostgreSQL**, it schedules multiple branches, sections, faculty, and classrooms/labs into clash-free weekly timetables in seconds.

---

## 🌟 Key Features

### ⚡ 1. Dual Constraint Solver Engine
* **🔀 Heuristic Solver**: Pure Python randomized greedy algorithm — finishes in under **0.2 seconds** with zero external solver dependencies.
* **🧮 CP-SAT Solver (Optimal)**: Uses **Google OR-Tools** constraint programming to find globally optimal schedules respecting hard limits and minimizing teacher idle gaps.

### 🏢 2. Target Scope Selection (Branch & Department Filtering)
* **🌐 All Branches (Entire College)**: Generates a unified master schedule across all branches and sections.
* **🏢 Specific Branch(es)**: Filter and generate timetables strictly for selected departments (e.g., CSE only, ECE only) with clash protection for shared faculty.

### ⏱️ 3. Live Stopwatch & Countdown Timer
* Real-time elapsed stopwatch (`00:00`, `00:01`...).
* Dynamic countdown timer synchronized with user's CP-SAT time limit.
* Live animated progress bar (`0%` to `100%`) powered by modern asynchronous Fetch API.

### 👩‍🏫 4. Faculty Specialization & Branch Constraints (with Dynamic "Other" Input)
* **Affiliation & Constraints**: Assign faculty to specific departments, branches, or subjects.
* **Dynamic "Other" Input**: Select `➕ Other (Type Manually...)` in dropdowns to dynamically reveal custom text fields for typing new departments, branches, or subjects.
* **Smart Assignment Validation**: Prevents invalid cross-branch or cross-subject assignments right at creation time.
* **Flexible Faculty**: Teachers left without constraints automatically serve as flexible multi-disciplinary faculty.

### 🔐 5. Authentication & Access Control
* Role-based permissions (**Admin**, **Teacher**, **Student**).
* **👁️ Password Visibility Toggle**: One-click show/hide eye toggle on all password inputs.
* **⚡ 1-Click Demo Fill**: Instantly populates credentials on login and registration pages for quick evaluation.

### 📊 6. Multi-Format Exporters
* **Excel (.xlsx)**: Formatted workbook with dedicated sheets for each Section, Teacher, and Room.
* **PDF Export**: Print-ready weekly timetable grid with color-coded slots.
* **JSON Export**: Structured timetable data ready for API consumption.

### 🧪 7. 100% Automated Test Coverage
* **51 Automated Unit Tests** covering solvers, validators, database loaders, exporters, and web routes.

---

## 🏗️ Project Architecture

```
timetable_project/
├── timetable/               # Core Solver & Timetable Engine (Python package)
│   ├── models.py            # Data classes: Branch, Section, Teacher, Room, Course, Assignment, Entry
│   ├── solver_heuristic.py  # Fast randomised greedy algorithm (pure Python)
│   ├── solver_cpsat.py      # Google OR-Tools CP-SAT solver (optimal)
│   ├── validator.py         # Hard constraint and soft warning checker
│   ├── db_loader.py         # Database problem loader with selective branch filtering
│   ├── db_saver.py          # Saves solved entries & scope tags to database
│   ├── exporter.py          # Excel (.xlsx) and JSON exporters
│   ├── pdf_exporter.py      # PDF schedule generator using ReportLab
│   └── sample_data.py       # Standard demo college problem builder
├── db/
│   ├── schema.sql           # PostgreSQL production schema
│   └── init_db.py           # Database initialisation utility
├── templates/               # Jinja2 HTML Templates
│   ├── admin/               # Management pages (Branches, Sections, Teachers, Rooms, Courses, Assignments, Generate)
│   ├── auth/                # Authentication (Login, Register with eye toggle & demo buttons)
│   ├── timetable/           # Timetable views & run history
│   └── errors/              # 403 & 404 error handlers
├── static/
│   ├── css/style.css        # Clean responsive CSS with modern UI cards & badges
│   └── js/timetable.js      # Interactive timetable UI scripts
├── tests/                   # 51 Comprehensive Unit Tests
│   ├── test_solver.py       # Solver logic & constraint validation tests
│   ├── test_validator.py    # Clash detection tests
│   ├── test_exporter.py     # Excel & JSON export tests
│   ├── test_db_loader.py    # DB loader & query tests
│   └── test_api.py          # Flask HTTP routes, auth, & API tests
├── docs/                    # Diagrams & Project Documentation
│   ├── diagrams/            # Architecture, ER, Flowchart, and Use-Case diagrams
│   └── report/              # Complete Project Report (.docx)
├── scripts/                 # Convenience Shell Scripts
│   ├── run.sh               # 1-Click web server launcher
│   ├── test.sh              # 1-Click test runner
│   └── init_db.sh           # Database seed verification
├── outputs/                 # Generated output schedules (JSON, XLSX, PDF)
├── app.py                   # Main Flask Application
├── database.py              # Dual SQLite & PostgreSQL abstraction layer
├── config.py                # Configuration & environment settings
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

### 📐 Diagrams
The project includes complete software engineering diagrams in [`docs/diagrams/`](docs/diagrams/):
* **Architecture Diagram**: Multi-tier architecture (Web UI, Flask Controllers, Constraint Engine, Database).
* **Entity-Relationship (ER) Diagram**: Normalized database schema with foreign keys and unique constraints.
* **Algorithm Flowchart**: Step-by-step solver execution flow.
* **Use-Case Diagram**: Actor interactions for Administrators, Teachers, and Students.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* Python 3.9+ (Python 3.10, 3.11, 3.12, 3.13, 3.14 supported)
* `pip` package manager

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/KumarAman0-0/TimeTable.git
cd TimeTable/timetable_project

# Create and activate a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Web Application
```bash
# Using the convenience script:
./scripts/run.sh

# Or directly:
python3 app.py
```
Open **`http://localhost:5000`** in your browser.

### 4. Default Login Credentials
* **Administrator**: `admin@college.edu` / `admin123`
*(Or simply click **"⚡ Demo: Fill Credentials"** on the login page!)*

---

## 🧪 Running the Tests

To run the complete automated test suite of **51 unit tests**:

```bash
# Using convenience script:
./scripts/test.sh

# Or using Python unittest runner:
python3 -m unittest discover -s tests -v
```

All 51 tests verify:
* Hard constraint violations (no teacher, room, or section clashes).
* Minimum and maximum daily load compliance.
* Consecutive 2-period lab blocks in designated lab rooms.
* Lunch break isolation per branch.
* Password hashing, session authentication, and route authorization.
* Excel, PDF, and JSON formatting integrity.

---

## 📄 License
This project is licensed under the MIT License.
