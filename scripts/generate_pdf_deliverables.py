#!/usr/bin/env python3
"""Generate the two assignment PDF deliverables directly from source docs."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Iterable, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
LIVRABLES = ROOT / "livrables"
RAPPORT_SRC = ROOT / "livrables" / "RAPPORT_TECHNIQUE.md"
GUIDE_SRC = ROOT / "docs" / "GUIDE_UTILISATION.md"

REPORT_PDF = ROOT / "livrables" / "Rapport_DataLake_Finance_Artemiy_Smogunov_Nathan_Smadja-Tubiana_Patrice_Ignongui.pdf"
TECH_PDF = ROOT / "livrables" / "Documentation_Technique_DataLake_Finance_Artemiy_Smogunov_Nathan_Smadja-Tubiana_Patrice_Ignongui.pdf"

GROUP_NAMES = ["Artemiy Smogunov", "Nathan Smadja-Tubiana", "Patrice Ignongui"]
TITLE = "Projet EFREI 2025-2026"


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_inline(text: str) -> str:
    text = escape_html(text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
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


def add_paragraphs(text: str, source_dir: Path, st: dict[str, ParagraphStyle], story: list) -> None:
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
                wrapped = []
                for code_line in code_lines:
                    wrapped.extend(textwrap.wrap(code_line, width=88, replace_whitespace=False) or [""])
                story.append(Preformatted("\n".join(wrapped), st["code"]))
                story.append(Spacer(1, 4))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(stripped)
            continue

        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped.strip())
        if image_match:
            image_path = (source_dir / image_match.group(2)).resolve()
            if not image_path.exists():
                raise FileNotFoundError(f"Capture introuvable : {image_path}")
            width, height = ImageReader(str(image_path)).getSize()
            max_width = A4[0] - 4.4 * cm
            max_height = 17 * cm
            scale = min(max_width / width, max_height / height, 1)
            image_block: list = [Image(str(image_path), width=width * scale, height=height * scale)]
            if image_match.group(1):
                image_block.append(Paragraph(escape_html(image_match.group(1)), st["subtitle"]))
            image_block.append(Spacer(1, 8))
            story.append(KeepTogether(image_block))
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



def title_page(st: dict[str, ParagraphStyle], story: list, kind: str) -> None:
    story.extend([
        Spacer(1, 2 * cm),
        Paragraph(kind, st["title"]),
        Paragraph("Data Lake financier", st["subtitle"]),
        Spacer(1, 1.2 * cm),
        Paragraph(f"Groupe : {', '.join(GROUP_NAMES)}", st["body"]),
        Spacer(1, 1.2 * cm),
        Paragraph(TITLE, st["subtitle"]),
        PageBreak(),
    ])


def generate_pdf(output: Path, sources: Iterable[Path], section_title: str) -> None:
    st = styles()
    story: list = []
    title_page(st, story, section_title)

    for idx, path in enumerate(sources):
        if idx:
            story.append(PageBreak())
        content = path.read_text(encoding="utf-8")
        add_paragraphs(content, path.parent, st, story)

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
    generate_pdf(TECH_PDF, [GUIDE_SRC], "Documentation technique")


if __name__ == "__main__":
    main()
