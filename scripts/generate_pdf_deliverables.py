#!/usr/bin/env python3
"""Generate the two assignment PDF deliverables directly from source docs."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
LIVRABLES = ROOT / "livrables"
RAPPORT_SRC = ROOT / "livrables" / "RAPPORT_TECHNIQUE.md"
README_SRC = ROOT / "README.md"
CONFORMITE_SRC = ROOT / "docs" / "CONFORMITE_DEVOIR.md"

REPORT_PDF = ROOT / "livrables" / "Rapport_DataLake_Finance_Artemiy_Smogunov_Nathan_Smadja-Tubiana_Patrice_Ignongui.pdf"
TECH_PDF = ROOT / "livrables" / "Documentation_Technique_DataLake_Finance_Artemiy_Smogunov_Nathan_Smadja-Tubiana_Patrice_Ignongui.pdf"

GROUP_NAMES = ["Artemiy Smogunov", "Nathan Smadja-Tubiana", "Patrice Ignongui"]
TITLE = "Data Lake financier – Démo technique"


def current_branch() -> str:
    try:
        return subprocess.check_output([
            "git",
            "-C",
            str(ROOT),
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ], text=True).strip()
    except Exception:
        return "unknown"


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_inline(text: str) -> str:
    text = escape_html(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], alignment=TA_CENTER, leading=24, spaceAfter=14),
        "subtitle": ParagraphStyle("Sub", parent=base["BodyText"], alignment=TA_CENTER, fontSize=10, leading=14, textColor=colors.gray),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], alignment=TA_LEFT, fontSize=17, leading=22, spaceBefore=8, spaceAfter=6),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], alignment=TA_LEFT, fontSize=14, leading=18, spaceBefore=6, spaceAfter=5),
        "h3": ParagraphStyle("H3", parent=base["Heading3"], alignment=TA_LEFT, fontSize=12, leading=15, spaceBefore=6, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=6),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName="Courier", fontSize=8.5, leading=11, spaceBefore=2, spaceAfter=6),
    }


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(A4[0] - 1.2 * cm, 0.8 * cm, f"Page {doc.page}")
    canvas.restoreState()


def add_paragraphs(text: str, st: dict[str, ParagraphStyle], story: list) -> None:
    lines = text.splitlines()
    in_code = False
    code_lines: List[str] = []

    def emit(line: str, style: str = "body", allow_markup: bool = True):
        if allow_markup:
            line = md_inline(line)
        elif not line:
            story.append(Spacer(1, 3))
            return
        story.append(Paragraph(line, st[style]))

    for line in lines:
        stripped = line.rstrip("\n")

        if stripped.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), st["code"]))
                story.append(Spacer(1, 4))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(stripped)
            continue

        if stripped.startswith("# "):
            emit(stripped[2:].strip(), "h1", allow_markup=False)
        elif stripped.startswith("## "):
            emit(stripped[3:].strip(), "h2", allow_markup=False)
        elif stripped.startswith("### "):
            emit(stripped[4:].strip(), "h3", allow_markup=False)
        elif re.match(r"^\s*[-*] ", stripped):
            bullet = stripped.lstrip()[2:].strip()
            emit(f"• {bullet}", "body")
        else:
            emit(md_inline(stripped), "body", allow_markup=False)



def title_page(st: dict[str, ParagraphStyle], story: list, kind: str, branch: str) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.extend([
        Spacer(1, 2 * cm),
        Paragraph(kind, st["title"]),
        Paragraph("Data Lake financier", st["subtitle"]),
        Spacer(1, 1.2 * cm),
        Paragraph(f"Groupe : {', '.join(GROUP_NAMES)}", st["body"]),
        Paragraph(f"Branche : {branch}", st["body"]),
        Spacer(1, 0.6 * cm),
        Paragraph(f"Généré le : {generated_at}", st["body"]),
        Spacer(1, 1.2 * cm),
        Paragraph(TITLE, st["subtitle"]),
        PageBreak(),
    ])


def generate_pdf(output: Path, sources: Iterable[Path], section_title: str) -> None:
    st = styles()
    story: list = []
    title_page(st, story, section_title, current_branch())

    for idx, path in enumerate(sources):
        if idx:
            story.append(PageBreak())
        content = path.read_text(encoding="utf-8")
        add_paragraphs(f"# Source: {path.as_posix()}\n\n{content}", st, story)

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)


def main() -> None:
    generate_pdf(REPORT_PDF, [RAPPORT_SRC], "Rapport technique")
    generate_pdf(TECH_PDF, [README_SRC, CONFORMITE_SRC], "Documentation technique")


if __name__ == "__main__":
    main()
