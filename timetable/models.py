"""Data model for the College Timetable Generator.

Time is modelled as a global wall-clock grid:  DAYS x SLOTS.
Every branch declares which slots it uses (first_slot..last_slot-1) and
which single slot is its lunch break, so different branches can have
different timings and different lunch times while shared teachers and
rooms are still clash-checked on the same clock.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from math import ceil
from typing import Dict, List, Set, Tuple, Optional

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SLOT_TIMES = [
    "09:00-09:50", "09:50-10:40", "10:40-11:30", "11:30-12:20",
    "12:20-13:10", "13:10-14:00", "14:00-14:50", "14:50-15:40",
]


@dataclass
class Branch:
    id: str
    name: str
    first_slot: int = 0
    last_slot: int = 8          # exclusive
    lunch_slot: int = 4         # no class for this branch in this slot

    def valid_slots(self) -> List[int]:
        return [s for s in range(self.first_slot, self.last_slot) if s != self.lunch_slot]


@dataclass
class Section:
    id: str
    branch_id: str
    name: str
    strength: int = 60


@dataclass
class Teacher:
    id: str
    name: str
    min_per_day: int = 0        # soft: if the teacher has classes that day, at least this many
    max_per_day: int = 5        # hard
    unavailable: Set[Tuple[int, int]] = field(default_factory=set)   # {(day, slot)}


@dataclass
class Room:
    id: str
    name: str
    tag: str = "classroom"      # 'classroom', 'computer_lab', 'electronics_lab', ...
    capacity: int = 60
    branch_id: Optional[str] = None
    department: Optional[str] = None


@dataclass
class Course:
    id: str
    name: str
    kind: str = "theory"        # 'theory' | 'lab'
    weekly: int = 3             # sessions per week
    block: int = 1              # consecutive periods per session (labs: 2)
    room_tag: str = "classroom" # which kind of room it needs


@dataclass
class Assignment:
    """One course of one section taught by one teacher."""
    section_id: str
    course_id: str
    teacher_id: str


@dataclass
class Entry:
    section_id: str
    course_id: str
    teacher_id: str
    room_id: str
    day: int
    slot: int
    block: int = 1


class Problem:
    def __init__(self, branches, sections, teachers, rooms, courses, assignments):
        self.branches: Dict[str, Branch] = {b.id: b for b in branches}
        self.sections: Dict[str, Section] = {s.id: s for s in sections}
        self.teachers: Dict[str, Teacher] = {t.id: t for t in teachers}
        self.rooms: Dict[str, Room] = {r.id: r for r in rooms}
        self.courses: Dict[str, Course] = {c.id: c for c in courses}
        self.assignments: List[Assignment] = list(assignments)

    # ---- helpers shared by both solvers -------------------------------
    def branch_of(self, section_id: str) -> Branch:
        return self.branches[self.sections[section_id].branch_id]

    def valid_starts(self, branch: Branch, block: int) -> List[int]:
        """Start slots where `block` consecutive slots are all teaching slots."""
        ok = set(branch.valid_slots())
        return [s for s in sorted(ok) if all((s + k) in ok for k in range(block))]

    def rooms_for(self, a: Assignment) -> List[Room]:
        course = self.courses[a.course_id]
        section = self.sections[a.section_id]
        strength = section.strength
        return [r for r in self.rooms.values()
                if r.tag == course.room_tag
                and r.capacity >= strength
                and (r.branch_id is None or r.branch_id == section.branch_id)]

    def teacher_free(self, teacher_id: str, day: int, slot: int, block: int) -> bool:
        t = self.teachers[teacher_id]
        return all((day, slot + k) not in t.unavailable for k in range(block))

    def day_cap(self, course: Course) -> int:
        """Max sessions of one course per day for one section."""
        return 1 if course.weekly <= len(DAYS) else ceil(course.weekly / len(DAYS))
