"""Pure-Python randomised greedy solver (no external libraries).

Idea
----
1. Break every (section, course) into weekly sessions.
2. Place the hardest sessions first: labs (multi-period blocks), then
   sessions of the busiest teachers.
3. For each session look at every feasible (day, start slot, room) and
   pick the cheapest one according to a soft-cost function (spread subjects
   over the week, avoid gaps, fill teachers' minimum daily load, use early
   slots, use the smallest suitable room).
4. If a session cannot be placed, throw the attempt away and retry with a
   different random order.  Keep the best complete timetable found.
"""
import random
from collections import defaultdict
from .models import DAYS, Entry, Problem
from .validator import validate


def _attempt(p: Problem, rng: random.Random):
    teacher_total = defaultdict(int)
    for a in p.assignments:
        c = p.courses[a.course_id]
        teacher_total[a.teacher_id] += c.weekly * c.block

    sessions = []
    for a in p.assignments:
        c = p.courses[a.course_id]
        for _ in range(c.weekly):
            key = (-c.block, -teacher_total[a.teacher_id] + rng.random() * 6, rng.random())
            sessions.append((key, a))
    sessions.sort(key=lambda x: x[0])

    sec_busy, tea_busy, room_busy = set(), set(), set()
    t_load = defaultdict(int)
    sec_day = defaultdict(int)
    sec_course_day = defaultdict(int)
    entries = []

    for _, a in sessions:
        course = p.courses[a.course_id]
        sec = p.sections[a.section_id]
        branch = p.branch_of(a.section_id)
        teacher = p.teachers[a.teacher_id]
        valid = branch.valid_slots()
        rooms = sorted(p.rooms_for(a), key=lambda r: r.capacity)
        cap = p.day_cap(course)
        best, best_cost = None, None

        for d in range(len(DAYS)):
            if sec_course_day[(sec.id, course.id, d)] >= cap:
                continue
            if t_load[(teacher.id, d)] + course.block > teacher.max_per_day:
                continue
            for s in p.valid_starts(branch, course.block):
                span = range(s, s + course.block)
                if any((sec.id, d, x) in sec_busy or (teacher.id, d, x) in tea_busy for x in span):
                    continue
                if not p.teacher_free(teacher.id, d, s, course.block):
                    continue
                room = next((r for r in rooms
                             if all((r.id, d, x) not in room_busy for x in span)), None)
                if room is None:
                    continue

                cost = rng.random() * 2
                cost += 3 * sec_day[(sec.id, d)]                      # spread over the week
                load = t_load[(teacher.id, d)]
                if 0 < load < teacher.min_per_day:
                    cost -= 5                                         # help reach minimum load
                elif load == 0:
                    cost += 2
                if sec_day[(sec.id, d)]:                              # avoid gaps
                    i, j = valid.index(s), valid.index(s + course.block - 1)
                    near = [valid[i - 1]] if i > 0 else []
                    near += [valid[j + 1]] if j + 1 < len(valid) else []
                    cost += -3 if any((sec.id, d, x) in sec_busy for x in near) else 3
                cost += 0.4 * (s - branch.first_slot)                 # prefer early slots
                cost += (room.capacity - sec.strength) / 100          # smallest suitable room
                if best_cost is None or cost < best_cost:
                    best_cost, best = cost, (d, s, room)

        if best is None:
            return None
        d, s, room = best
        for x in range(s, s + course.block):
            sec_busy.add((sec.id, d, x)); tea_busy.add((teacher.id, d, x))
            room_busy.add((room.id, d, x))
        t_load[(teacher.id, d)] += course.block
        sec_day[(sec.id, d)] += course.block
        sec_course_day[(sec.id, course.id, d)] += 1
        entries.append(Entry(sec.id, course.id, teacher.id, room.id, d, s, course.block))
    return entries


def solve_heuristic(p: Problem, tries: int = 400, seed: int = 0, keep_good: int = 30):
    rng = random.Random(seed)
    best, best_pen, found = None, None, 0
    for _ in range(tries):
        res = _attempt(p, rng)
        if res is None:
            continue
        found += 1
        hard, soft = validate(p, res)
        if hard:                       # should never happen, safety net
            continue
        if best is None or len(soft) < best_pen:
            best, best_pen = res, len(soft)
        if best_pen == 0 or found >= keep_good:
            break
    return best
