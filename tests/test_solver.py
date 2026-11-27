import unittest
from timetable.sample_data import build_sample
from timetable.solver_heuristic import solve_heuristic
from timetable.validator import validate
from timetable.models import Teacher, Assignment, Course


class TestTimetable(unittest.TestCase):
    def setUp(self):
        self.p = build_sample()
        self.entries = solve_heuristic(self.p)

    def test_01_all_sessions_placed_no_hard_violation(self):
        self.assertIsNotNone(self.entries)
        hard, _ = validate(self.p, self.entries)
        self.assertEqual(hard, [])
        self.assertEqual(len(self.entries), sum(self.p.courses[a.course_id].weekly for a in self.p.assignments))

    def test_02_no_teacher_section_room_clash(self):
        seen = set()
        for e in self.entries:
            for k in range(e.block):
                for key in (("s", e.section_id, e.day, e.slot + k), ("t", e.teacher_id, e.day, e.slot + k),
                            ("r", e.room_id, e.day, e.slot + k)):
                    self.assertNotIn(key, seen)
                    seen.add(key)

    def test_03_labs_use_two_consecutive_periods_in_lab_rooms(self):
        for e in self.entries:
            c = self.p.courses[e.course_id]
            if c.kind == "lab":
                self.assertEqual(e.block, 2)
                self.assertEqual(self.p.rooms[e.room_id].tag, c.room_tag)

    def test_04_lunch_respected_per_branch(self):
        for e in self.entries:
            lunch = self.p.branch_of(e.section_id).lunch_slot
            self.assertTrue(all(e.slot + k != lunch for k in range(e.block)))

    def test_05_teacher_unavailability_respected(self):
        for e in self.entries:
            if e.teacher_id == "T7":
                self.assertNotEqual(e.day, 5)

    def test_06_teacher_daily_max(self):
        from collections import Counter
        load = Counter()
        for e in self.entries:
            load[(e.teacher_id, e.day)] += e.block
        for (t, d), n in load.items():
            self.assertLessEqual(n, self.p.teachers[t].max_per_day)

    def test_07_many_seeds_all_valid(self):
        for seed in range(10):
            res = solve_heuristic(self.p, seed=seed)
            self.assertIsNotNone(res)
            self.assertEqual(validate(self.p, res)[0], [])

    def test_08_impossible_input_returns_none(self):
        p = build_sample()
        p.courses["EXTRA"] = Course("EXTRA", "Impossible", "theory", 6)
        # one teacher who is unavailable all week
        p.teachers["TX"] = Teacher("TX", "Absent", 0, 5, {(d, s) for d in range(6) for s in range(8)})
        p.assignments.append(Assignment("CSE-A", "EXTRA", "TX"))
        self.assertIsNone(solve_heuristic(p, tries=20))


if __name__ == "__main__":
    unittest.main(verbosity=2)
