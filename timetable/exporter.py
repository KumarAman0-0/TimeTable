"""Export a timetable to JSON and a multi-sheet Excel workbook."""
import json
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from .models import DAYS, SLOT_TIMES, Problem


def to_json(p: Problem, entries, path):
    data = [dict(section=e.section_id, course=p.courses[e.course_id].name,
                 teacher=p.teachers[e.teacher_id].name, room=p.rooms[e.room_id].name,
                 day=DAYS[e.day], slot=e.slot, time=SLOT_TIMES[e.slot], block=e.block)
            for e in sorted(entries, key=lambda e: (e.section_id, e.day, e.slot))]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _grid(p, entries, key_fn, label_fn):
    grids = defaultdict(dict)
    for e in entries:
        for k in range(e.block):
            grids[key_fn(e)][(e.day, e.slot + k)] = label_fn(e)
    return grids


def to_excel(p: Problem, entries, path):
    wb = Workbook(); wb.remove(wb.active)
    thin = Side(style="thin", color="999999")
    head = PatternFill("solid", start_color="1F4E78")
    lunch = PatternFill("solid", start_color="FFE699")
    cell_fill = PatternFill("solid", start_color="DDEBF7")

    def sheet(title, grid, lunch_slot=None):
        ws = wb.create_sheet(title[:31])
        ws.cell(1, 1, "Time").font = Font(bold=True, color="FFFFFF"); ws.cell(1, 1).fill = head
        for d, name in enumerate(DAYS):
            c = ws.cell(1, d + 2, name); c.font = Font(bold=True, color="FFFFFF"); c.fill = head
            c.alignment = Alignment(horizontal="center")
        for s, t in enumerate(SLOT_TIMES):
            ws.cell(s + 2, 1, t).font = Font(bold=True)
            for d in range(len(DAYS)):
                c = ws.cell(s + 2, d + 2, grid.get((d, s), ""))
                c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                if grid.get((d, s)): c.fill = cell_fill
                elif lunch_slot is not None and s == lunch_slot:
                    c.value = "LUNCH"; c.fill = lunch
            ws.row_dimensions[s + 2].height = 42
        ws.column_dimensions["A"].width = 14
        for d in range(len(DAYS)): ws.column_dimensions[chr(66 + d)].width = 24

    g = _grid(p, entries, lambda e: e.section_id,
              lambda e: f"{p.courses[e.course_id].name}\n{p.teachers[e.teacher_id].name}\n{p.rooms[e.room_id].name}")
    for sid, grid in g.items():
        sheet(f"Sec {sid}", grid, p.branch_of(sid).lunch_slot)
    g = _grid(p, entries, lambda e: e.teacher_id,
              lambda e: f"{p.courses[e.course_id].name}\n{e.section_id}\n{p.rooms[e.room_id].name}")
    for tid, grid in g.items():
        sheet(f"Teacher {p.teachers[tid].name}", grid)
    g = _grid(p, entries, lambda e: e.room_id,
              lambda e: f"{p.courses[e.course_id].name}\n{e.section_id}\n{p.teachers[e.teacher_id].name}")
    for rid, grid in g.items():
        sheet(f"Room {p.rooms[rid].name}", grid)
    wb.save(path)
