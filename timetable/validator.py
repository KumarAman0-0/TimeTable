"""Independent checker: verifies a finished timetable against every rule."""
from collections import defaultdict
from .models import DAYS, Problem, Entry


def validate(problem: Problem, entries: list[Entry]):
    hard, soft = [], []
    sec_busy, tea_busy, room_busy = {}, {}, {}
    per_assign = defaultdict(int)
    sec_course_day = defaultdict(int)
    teacher_day_load = defaultdict(int)

    for e in entries:
        course = problem.courses[e.course_id]
        branch = problem.branch_of(e.section_id)
        room = problem.rooms[e.room_id]
        sec = problem.sections[e.section_id]
        per_assign[(e.section_id, e.course_id, e.teacher_id)] += 1
        sec_course_day[(e.section_id, e.course_id, e.day)] += 1

        if e.block != course.block:
            hard.append(f"block length wrong for {course.name}")
        if room.tag != course.room_tag:
            hard.append(f"{course.name} placed in wrong room type {room.name}")
        if room.capacity < sec.strength:
            hard.append(f"{room.name} too small for {sec.name}")
        for k in range(e.block):
            s = e.slot + k
            if s not in branch.valid_slots():
                hard.append(f"{sec.id} {course.name} outside branch timing/lunch (slot {s})")
            if not problem.teacher_free(e.teacher_id, e.day, s, 1):
                hard.append(f"teacher {e.teacher_id} unavailable day {e.day} slot {s}")
            for table, key, who in (
                (sec_busy, (e.section_id, e.day, s), f"section {e.section_id}"),
                (tea_busy, (e.teacher_id, e.day, s), f"teacher {e.teacher_id}"),
                (room_busy, (e.room_id, e.day, s), f"room {e.room_id}"),
            ):
                if key in table:
                    hard.append(f"CLASH: {who} double-booked on {DAYS[e.day]} slot {s}")
                table[key] = True
            teacher_day_load[(e.teacher_id, e.day)] += 1

    for a in problem.assignments:
        got = per_assign[(a.section_id, a.course_id, a.teacher_id)]
        need = problem.courses[a.course_id].weekly
        if got != need:
            hard.append(f"{a.section_id}/{a.course_id}: scheduled {got} of {need} sessions")
    for (sec, cid, d), n in sec_course_day.items():
        if n > problem.day_cap(problem.courses[cid]):
            hard.append(f"{sec}/{cid} repeated {n}x on {DAYS[d]}")
    for (t, d), load in teacher_day_load.items():
        T = problem.teachers[t]
        if load > T.max_per_day:
            hard.append(f"teacher {T.name} has {load} > max {T.max_per_day} on {DAYS[d]}")
        if 0 < load < T.min_per_day:
            soft.append(f"teacher {T.name} has only {load} (< min {T.min_per_day}) on {DAYS[d]}")
    return hard, soft
