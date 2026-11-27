"""PDF exporter for the College Timetable Generator.

Generates one page per section with a colour-coded timetable grid.

Usage:
    from timetable.pdf_exporter import to_pdf
    to_pdf(problem, entries, "outputs/timetable.pdf")

Requires: pip install reportlab
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, PageBreak)
from reportlab.lib.enums import TA_CENTER
from collections import defaultdict
from .models import DAYS, SLOT_TIMES, Problem, Entry


# ── colour palette ───────────────────────────────────────────────────────────
COL_HEADER = colors.HexColor("#1F4E78")
COL_LUNCH  = colors.HexColor("#FFE699")
COL_CELL   = colors.HexColor("#DDEBF7")
COL_EMPTY  = colors.white
COL_WHITE  = colors.white


def _build_grid(problem: Problem, entries: list[Entry], key_fn, label_fn):
    grids = defaultdict(dict)
    for e in entries:
        for k in range(e.block):
            grids[key_fn(e)][(e.day, e.slot + k)] = label_fn(e)
    return grids


def _make_table_data(grid: dict, lunch_slot: int | None):
    """Return (data, style_commands) for a 9-row × 7-col grid."""
    header = ["Time"] + DAYS
    rows = [header]
    for s, t in enumerate(SLOT_TIMES):
        row = [t]
        for d in range(len(DAYS)):
            cell = grid.get((d, s), "")
            if not cell and lunch_slot is not None and s == lunch_slot:
                cell = "LUNCH"
            row.append(cell)
        rows.append(row)
    return rows


def _table_style(rows, lunch_slot):
    style = [
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0),  COL_HEADER),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  COL_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  9),
        ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
        # Time column
        ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 1), (0, -1),  7),
        # Body
        ("FONTSIZE",     (1, 1), (-1, -1), 7),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUND",(0, 1), (-1, -1), [COL_EMPTY, COL_EMPTY]),
    ]
    # Colour filled cells
    for r_idx, row in enumerate(rows[1:], start=1):
        for c_idx, cell in enumerate(row[1:], start=1):
            if cell and cell != "LUNCH":
                style.append(("BACKGROUND", (c_idx, r_idx), (c_idx, r_idx), COL_CELL))
            elif cell == "LUNCH":
                style.append(("BACKGROUND", (c_idx, r_idx), (c_idx, r_idx), COL_LUNCH))
    return TableStyle(style)


def to_pdf(problem: Problem, entries: list[Entry], path: str):
    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                 fontSize=14, spaceAfter=6, alignment=TA_CENTER)
    sub_style   = ParagraphStyle("sub",   parent=styles["Normal"],
                                 fontSize=9,  spaceAfter=4, alignment=TA_CENTER)

    story = []
    col_widths = [3*cm] + [3.8*cm]*6   # Time col + 6 day cols

    # ── Section timetables ───────────────────────────────────────────────────
    grids = _build_grid(
        problem, entries,
        key_fn=lambda e: e.section_id,
        label_fn=lambda e: (f"{problem.courses[e.course_id].name}\n"
                            f"{problem.teachers[e.teacher_id].name}\n"
                            f"{problem.rooms[e.room_id].name}")
    )
    for sid, grid in sorted(grids.items()):
        sec  = problem.sections[sid]
        lunch = problem.branch_of(sid).lunch_slot
        story.append(Paragraph("College Timetable Generator", title_style))
        story.append(Paragraph(f"Section: {sec.name}", sub_style))
        rows = _make_table_data(grid, lunch)
        tbl  = Table(rows, colWidths=col_widths, rowHeights=[1*cm] + [1.5*cm]*8)
        tbl.setStyle(_table_style(rows, lunch))
        story.append(tbl)
        story.append(PageBreak())

    # ── Teacher timetables ───────────────────────────────────────────────────
    grids = _build_grid(
        problem, entries,
        key_fn=lambda e: e.teacher_id,
        label_fn=lambda e: (f"{problem.courses[e.course_id].name}\n"
                            f"{problem.sections[e.section_id].name}\n"
                            f"{problem.rooms[e.room_id].name}")
    )
    for tid, grid in sorted(grids.items()):
        tea = problem.teachers[tid]
        story.append(Paragraph("College Timetable Generator", title_style))
        story.append(Paragraph(f"Teacher: {tea.name}", sub_style))
        rows = _make_table_data(grid, None)
        tbl  = Table(rows, colWidths=col_widths, rowHeights=[1*cm] + [1.5*cm]*8)
        tbl.setStyle(_table_style(rows, None))
        story.append(tbl)
        story.append(PageBreak())

    doc.build(story)
    print(f"📄 PDF saved to {path}")
