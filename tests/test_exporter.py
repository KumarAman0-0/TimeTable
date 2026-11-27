"""Tests for timetable/exporter.py — JSON and Excel output."""
import json
import os
import tempfile
import unittest
from timetable.sample_data import build_sample
from timetable.solver_heuristic import solve_heuristic
from timetable.exporter import to_json, to_excel
from timetable.models import DAYS, SLOT_TIMES


class TestJsonExporter(unittest.TestCase):

    def setUp(self):
        self.p = build_sample()
        self.entries = solve_heuristic(self.p)
        self.assertIsNotNone(self.entries)
        self.tmp = tempfile.mkdtemp()

    def test_json_file_created(self):
        path = os.path.join(self.tmp, "out.json")
        to_json(self.p, self.entries, path)
        self.assertTrue(os.path.exists(path))

    def test_json_is_valid_list(self):
        path = os.path.join(self.tmp, "out.json")
        to_json(self.p, self.entries, path)
        with open(path) as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(self.entries))

    def test_json_entry_has_required_keys(self):
        path = os.path.join(self.tmp, "out.json")
        to_json(self.p, self.entries, path)
        with open(path) as f:
            data = json.load(f)
        required = {"section", "course", "teacher", "room", "day", "slot", "time", "block"}
        for row in data:
            self.assertTrue(required.issubset(row.keys()),
                            f"Missing keys in row: {row}")

    def test_json_days_are_valid(self):
        path = os.path.join(self.tmp, "out.json")
        to_json(self.p, self.entries, path)
        with open(path) as f:
            data = json.load(f)
        for row in data:
            self.assertIn(row["day"], DAYS)

    def test_json_time_strings_are_valid(self):
        path = os.path.join(self.tmp, "out.json")
        to_json(self.p, self.entries, path)
        with open(path) as f:
            data = json.load(f)
        for row in data:
            self.assertIn(row["time"], SLOT_TIMES)

    def test_json_sorted_by_section_day_slot(self):
        path = os.path.join(self.tmp, "out.json")
        to_json(self.p, self.entries, path)
        with open(path) as f:
            data = json.load(f)
        keys = [(r["section"], DAYS.index(r["day"]) if r["day"] in DAYS else 0, r["slot"]) for r in data]
        self.assertEqual(keys, sorted(keys))


class TestExcelExporter(unittest.TestCase):

    def setUp(self):
        self.p = build_sample()
        self.entries = solve_heuristic(self.p)
        self.assertIsNotNone(self.entries)
        self.tmp = tempfile.mkdtemp()

    def test_excel_file_created(self):
        path = os.path.join(self.tmp, "out.xlsx")
        to_excel(self.p, self.entries, path)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)

    def test_excel_has_section_sheets(self):
        from openpyxl import load_workbook
        path = os.path.join(self.tmp, "out.xlsx")
        to_excel(self.p, self.entries, path)
        wb = load_workbook(path)
        section_sheets = [s for s in wb.sheetnames if s.startswith("Sec ")]
        self.assertGreater(len(section_sheets), 0)

    def test_excel_has_teacher_sheets(self):
        from openpyxl import load_workbook
        path = os.path.join(self.tmp, "out.xlsx")
        to_excel(self.p, self.entries, path)
        wb = load_workbook(path)
        teacher_sheets = [s for s in wb.sheetnames if s.startswith("Teacher ")]
        self.assertGreater(len(teacher_sheets), 0)

    def test_excel_has_room_sheets(self):
        from openpyxl import load_workbook
        path = os.path.join(self.tmp, "out.xlsx")
        to_excel(self.p, self.entries, path)
        wb = load_workbook(path)
        room_sheets = [s for s in wb.sheetnames if s.startswith("Room ")]
        self.assertGreater(len(room_sheets), 0)

    def test_excel_header_row_has_days(self):
        from openpyxl import load_workbook
        path = os.path.join(self.tmp, "out.xlsx")
        to_excel(self.p, self.entries, path)
        wb = load_workbook(path)
        ws = wb[wb.sheetnames[0]]
        headers = [ws.cell(1, c).value for c in range(2, 8)]
        self.assertEqual(headers, DAYS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
