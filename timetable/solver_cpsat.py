"""Optimal solver using Google OR-Tools CP-SAT.   pip install ortools

Decision variable
-----------------
x[a, d, s, r] = 1  if assignment `a` (section+course+teacher) has a session
                   starting on day d, slot s, in room r.
A lab session with block=2 occupies slots s and s+1.

Hard constraints
----------------
* every assignment gets exactly `weekly` sessions
* a section / teacher / room is used at most once per (day, slot)
* a session only starts where all its slots are teaching slots of that branch
  (so it never crosses lunch or the branch's closing time)
* room type and capacity must fit; teacher unavailability is respected
* a course appears at most `day_cap` times a day for a section
* teacher's daily load <= max_per_day

Soft constraints (minimised in the objective)
----------------------------------------------
* shortfall of a teacher's minimum daily load      (weight 10)
* number of separate class "runs" per section/day  (weight 3)  -> fewer gaps
* late slots                                        (weight 1)
"""
from collections import defaultdict
from .models import DAYS, Entry, Problem


def solve_cpsat(p: Problem, time_limit: int = 60, workers: int = 8):
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    x = {}                                   # (ai, d, s, rid) -> BoolVar
    per_assign = defaultdict(list)
    per_assign_day = defaultdict(list)
    occ_sec, occ_tea, occ_room = defaultdict(list), defaultdict(list), defaultdict(list)
    tea_load = defaultdict(list)             # (teacher, day) -> [(coef, var)]
    cost_terms = []

    for ai, a in enumerate(p.assignments):
        course = p.courses[a.course_id]
        branch = p.branch_of(a.section_id)
        rooms = p.rooms_for(a)
        for d in range(len(DAYS)):
            for s in p.valid_starts(branch, course.block):
                if not p.teacher_free(a.teacher_id, d, s, course.block):
                    continue
                for r in rooms:
                    v = m.NewBoolVar(f"x_{ai}_{d}_{s}_{r.id}")
                    x[(ai, d, s, r.id)] = v
                    per_assign[ai].append(v)
                    per_assign_day[(ai, d)].append(v)
                    tea_load[(a.teacher_id, d)].append((course.block, v))
                    cost_terms.append((s - branch.first_slot) * v)       # prefer early slots
                    for k in range(course.block):
                        occ_sec[(a.section_id, d, s + k)].append(v)
                        occ_tea[(a.teacher_id, d, s + k)].append(v)
                        occ_room[(r.id, d, s + k)].append(v)

    for ai, a in enumerate(p.assignments):
        course = p.courses[a.course_id]
        m.Add(sum(per_assign[ai]) == course.weekly)
        for d in range(len(DAYS)):
            if per_assign_day[(ai, d)]:
                m.Add(sum(per_assign_day[(ai, d)]) <= p.day_cap(course))

    for table in (occ_sec, occ_tea, occ_room):
        for lits in table.values():
            if len(lits) > 1:
                m.AddAtMostOne(lits)

    # teacher daily load (hard max, soft min)
    for (tid, d), terms in tea_load.items():
        T = p.teachers[tid]
        load = sum(c * v for c, v in terms)
        has = m.NewBoolVar(f"has_{tid}_{d}")
        m.Add(load <= T.max_per_day * has)
        if T.min_per_day > 0:
            short = m.NewIntVar(0, T.min_per_day, f"short_{tid}_{d}")
            m.Add(load + short >= T.min_per_day * has)
            cost_terms.append(10 * short)

    # fewer gaps: count the number of separate runs of classes per section/day
    for sid, sec in p.sections.items():
        valid = p.branch_of(sid).valid_slots()
        for d in range(len(DAYS)):
            for i, s in enumerate(valid):
                busy = sum(occ_sec.get((sid, d, s), []))
                prev = sum(occ_sec.get((sid, d, valid[i - 1]), [])) if i > 0 else 0
                run = m.NewBoolVar(f"run_{sid}_{d}_{s}")
                m.Add(run >= busy - prev)
                cost_terms.append(3 * run)

    m.Minimize(sum(cost_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    entries = []
    for (ai, d, s, rid), v in x.items():
        if solver.Value(v):
            a = p.assignments[ai]
            entries.append(Entry(a.section_id, a.course_id, a.teacher_id, rid, d, s,
                                 p.courses[a.course_id].block))
    return entries
