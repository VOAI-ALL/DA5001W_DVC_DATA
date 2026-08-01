from pathlib import Path
import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "Implementation_Plan.md"
OUTPUT = ROOT / "Implementation_Plan.pdf"


def inline_markdown(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", stripped))


def add_bullets(story, items, style):
    if not items:
        return
    story.append(
        ListFlowable(
            [ListItem(Paragraph(inline_markdown(item), style), leftIndent=12) for item in items],
            bulletType="bullet",
            start="circle",
            leftIndent=18,
            bulletFontSize=7,
        )
    )
    story.append(Spacer(1, 0.06 * inch))


def add_numbered(story, items, style):
    if not items:
        return
    story.append(
        ListFlowable(
            [ListItem(Paragraph(inline_markdown(item), style), leftIndent=12) for item in items],
            bulletType="1",
            leftIndent=18,
        )
    )
    story.append(Spacer(1, 0.06 * inch))


def add_table(story, rows, styles):
    if not rows:
        return
    data = [[Paragraph(inline_markdown(cell), styles["TableCell"]) for cell in row] for row in rows]
    available_width = A4[0] - 1.4 * inch
    col_count = max(len(row) for row in rows)
    col_widths = [available_width / col_count] * col_count
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243447")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C2CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.12 * inch))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(0.7 * inch, 0.42 * inch, "MLOps Project Implementation Plan")
    canvas.drawRightString(A4[0] - 0.7 * inch, 0.42 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf():
    markdown = INPUT.read_text(encoding="utf-8").splitlines()

    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "PlanTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            spaceAfter=16,
            textColor=colors.HexColor("#102A43"),
            alignment=TA_LEFT,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            spaceBefore=12,
            spaceAfter=7,
            textColor=colors.HexColor("#243447"),
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=5,
            textColor=colors.HexColor("#334E68"),
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            spaceAfter=5,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.4,
            leading=10.6,
        ),
    }

    story = []
    bullets = []
    numbered = []
    table_rows = []

    def flush_lists_and_tables():
        nonlocal bullets, numbered, table_rows
        add_bullets(story, bullets, styles["Body"])
        bullets = []
        add_numbered(story, numbered, styles["Body"])
        numbered = []
        add_table(story, table_rows, styles)
        table_rows = []

    first_title = True
    in_code_block = False
    code_lines = []

    for raw in markdown:
        line = raw.rstrip()

        if line.strip().startswith("```"):
            if in_code_block:
                flush_lists_and_tables()
                code_text = "<br/>".join(html.escape(code_line) for code_line in code_lines)
                story.append(Paragraph(f"<font name='Courier'>{code_text}</font>", styles["Body"]))
                story.append(Spacer(1, 0.08 * inch))
                code_lines = []
                in_code_block = False
            else:
                flush_lists_and_tables()
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_lists_and_tables()
            continue

        if line.startswith("|") and "|" in line[1:]:
            if is_table_separator(line):
                continue
            add_bullets(story, bullets, styles["Body"])
            bullets = []
            add_numbered(story, numbered, styles["Body"])
            numbered = []
            table_rows.append(split_table_row(line))
            continue

        flush_lists_and_tables()

        if line.startswith("# "):
            if not first_title:
                story.append(PageBreak())
            story.append(Paragraph(inline_markdown(line[2:].strip()), styles["Title"]))
            first_title = False
        elif line.startswith("## "):
            story.append(Paragraph(inline_markdown(line[3:].strip()), styles["H2"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_markdown(line[4:].strip()), styles["H3"]))
        elif re.match(r"^\s*-\s+", line):
            bullets.append(re.sub(r"^\s*-\s+", "", line))
        elif re.match(r"^\s*\d+\.\s+", line):
            numbered.append(re.sub(r"^\s*\d+\.\s+", "", line))
        else:
            story.append(Paragraph(inline_markdown(line), styles["Body"]))

    flush_lists_and_tables()

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="MLOps Project Implementation Plan",
        author="Codex",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
