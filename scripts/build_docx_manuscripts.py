#!/usr/bin/env python3
"""Convert research manuscript Markdown documents into professionally styled Word (.docx) files."""

import re
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

COLOR_PRIMARY = RGBColor(26, 82, 118)   # #1A5276 Dark Blue
COLOR_DARK = RGBColor(44, 62, 80)       # #2C3E50 Body Text
COLOR_MID = RGBColor(127, 140, 141)     # #7F8C8D Gray
MID_GRAY = COLOR_MID
HEX_HEADER_BG = "F2F4F4"                # Light gray-blue table header
HEX_BORDER = "BDC3C7"


def _set_cell_border(cell, **kwargs):
    """Set cell borders with XML formatting."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'<w:top w:val="{kwargs.get("top", "none")}" w:sz="{kwargs.get("top_sz", "4")}" w:space="0" w:color="{kwargs.get("top_color", HEX_BORDER)}"/>\n'
        f'<w:left w:val="{kwargs.get("left", "none")}" w:sz="{kwargs.get("left_sz", "4")}" w:space="0" w:color="{kwargs.get("left_color", HEX_BORDER)}"/>\n'
        f'<w:bottom w:val="{kwargs.get("bottom", "none")}" w:sz="{kwargs.get("bottom_sz", "4")}" w:space="0" w:color="{kwargs.get("bottom_color", HEX_BORDER)}"/>\n'
        f'<w:right w:val="{kwargs.get("right", "none")}" w:sz="{kwargs.get("right_sz", "4")}" w:space="0" w:color="{kwargs.get("right_color", HEX_BORDER)}"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)


def _set_cell_background(cell, hex_color):
    """Set cell background shading."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def _add_styled_heading(doc, text, level):
    """Add styled headings with clean typography."""
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.bold = True

    if level == 1:
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(12)
        run.font.color.rgb = COLOR_PRIMARY
    elif level == 2:
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run.font.size = Pt(11)
        run.font.color.rgb = COLOR_PRIMARY
    else:
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run.font.size = Pt(10)
        run.font.color.rgb = COLOR_DARK
    return p


def _format_inline_text(paragraph, text):
    """Parse basic inline markdown bold, italic, math-like symbols."""
    # Split by bold first (**...**)
    tokens = re.split(r'(\*\*.*?\*\*)', text)
    for token in tokens:
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            content = token[2:-2]
            # check italic inside bold
            sub_tokens = re.split(r'(\*.*?\*)', content)
            for st in sub_tokens:
                if st.startswith('*') and st.endswith('*') and len(st) >= 2:
                    r = paragraph.add_run(st[1:-1])
                    r.bold = True
                    r.italic = True
                else:
                    r = paragraph.add_run(st)
                    r.bold = True
                r.font.name = "Times New Roman"
        else:
            # check italic (*...*)
            sub_tokens = re.split(r'(\*.*?\*)', token)
            for st in sub_tokens:
                if st.startswith('*') and st.endswith('*') and len(st) >= 2:
                    r = paragraph.add_run(st[1:-1])
                    r.italic = True
                else:
                    r = paragraph.add_run(st)
                r.font.name = "Times New Roman"


def convert_markdown_to_docx(md_path: Path, docx_path: Path) -> Path:
    """Convert a manuscript markdown file into a styled docx file."""
    md_path = Path(md_path)
    docx_path = Path(docx_path)
    content = md_path.read_text(encoding="utf-8")
    base_dir = md_path.parent

    doc = docx.Document()

    # Page setup: A4, 1 inch margins
    sections = doc.sections
    for s in sections:
        s.page_width = Inches(8.27)   # A4
        s.page_height = Inches(11.69)
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # Set base Normal style
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(10)
    style_normal.font.color.rgb = COLOR_DARK

    lines = content.splitlines()
    i = 0
    in_table = False
    table_lines = []

    while i < len(lines):
        line = lines[i].rstrip()

        # Check for Markdown Table block
        if line.startswith('|') and line.endswith('|'):
            table_lines.append(line)
            in_table = True
            i += 1
            continue
        elif in_table:
            # End of table block: process table
            _build_docx_table(doc, table_lines)
            in_table = False
            table_lines = []
            # do not increment i, let current line be processed below

        # Title (# Title)
        if line.startswith('# '):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(14)
            run = p.add_run(line[2:].strip())
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            i += 1
            continue

        # Heading 1 (## Heading)
        if line.startswith('## '):
            _add_styled_heading(doc, line[3:].strip(), level=1)
            i += 1
            continue

        # Heading 2 (### Heading)
        if line.startswith('### '):
            _add_styled_heading(doc, line[4:].strip(), level=2)
            i += 1
            continue

        # Blank line
        if not line:
            i += 1
            continue

        # Image tag: ![caption](relative_path)
        img_match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if img_match:
            img_rel_path = img_match.group(2)
            full_img_path = (base_dir / img_rel_path).resolve()
            if full_img_path.exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.keep_with_next = True
                run = p.add_run()
                # Insert image scaled to 6.2 inches (standard margin width on A4)
                run.add_picture(str(full_img_path), width=Inches(6.2))
            i += 1
            continue

        # Caption text (FIGURE X or GAMBAR X or TABEL X or TABLE X)
        if re.match(r'^(FIGURE|GAMBAR|TABLE|TABEL)\s+\d+\.', line):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(10)
            p.paragraph_format.keep_with_next = True if line.startswith(('TABLE', 'TABEL')) else False
            run = p.add_run(line.strip())
            run.font.name = 'Times New Roman'
            run.font.size = Pt(9.5)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            i += 1
            continue

        # Math formula display block (\[ ... \])
        if line.startswith(r'\['):
            math_lines = [line]
            while not line.endswith(r'\]') and i + 1 < len(lines):
                i += 1
                line = lines[i].rstrip()
                math_lines.append(line)
            formula_text = " ".join(math_lines).replace(r'\[', '').replace(r'\]', '').strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(formula_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10)
            run.italic = True
            i += 1
            continue

        # Note / Footnote paragraph
        if line.startswith('**Catatan:**') or line.startswith('**Note:**'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(8)
            _format_inline_text(p, line)
            for r in p.runs:
                r.font.size = Pt(8.5)
                r.font.color.rgb = MID_GRAY
            i += 1
            continue

        # Keywords line
        if line.startswith('**Kata kunci:**') or line.startswith('**Keywords:**'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(12)
            _format_inline_text(p, line)
            for r in p.runs:
                r.font.size = Pt(9.5)
            i += 1
            continue

        # Standard paragraph text
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        _format_inline_text(p, line)
        i += 1

    # If document ended inside a table
    if in_table and table_lines:
        _build_docx_table(doc, table_lines)

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))
    return docx_path


def _build_docx_table(doc, table_lines):
    """Parse markdown table lines and generate a styled Word table."""
    # Filter out divider lines (e.g. |---|---|)
    parsed_rows = []
    for l in table_lines:
        cells = [c.strip() for c in l.strip('|').split('|')]
        # check if it's separator row
        if all(re.match(r'^:?-+:?$', c) for c in cells if c):
            continue
        parsed_rows.append(cells)

    if not parsed_rows:
        return

    num_rows = len(parsed_rows)
    num_cols = max(len(r) for r in parsed_rows)

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for row_idx, row_data in enumerate(parsed_rows):
        is_header = (row_idx == 0)
        tr = table.rows[row_idx]
        tr.height = Pt(18 if is_header else 15)

        for col_idx, cell_value in enumerate(row_data):
            cell = tr.cells[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)

            # Alignment heuristics: numbers right-aligned, text left-aligned
            val_clean = cell_value.replace('**', '').strip()
            if re.match(r'^[−\-+]?[0-9\.,]+%?$', val_clean) or val_clean in ('—', '−'):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            _format_inline_text(p, cell_value)

            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(8.5 if not is_header else 9.0)
                if is_header:
                    r.bold = True
                    r.font.color.rgb = COLOR_PRIMARY
                else:
                    r.font.color.rgb = COLOR_DARK

            # Borders & Shading: Academic standard (APA/IEEE 3-line style)
            if is_header:
                _set_cell_background(cell, HEX_HEADER_BG)
                _set_cell_border(cell, top="single", top_sz="12", top_color="1A5276",
                                 bottom="single", bottom_sz="6", bottom_color="1A5276")
            elif row_idx == num_rows - 1:
                # Bottom border for final row
                _set_cell_border(cell, bottom="single", bottom_sz="12", bottom_color="1A5276")
            else:
                _set_cell_border(cell, bottom="single", bottom_sz="4", bottom_color=HEX_BORDER)

    # Add space after table
    post_p = doc.add_paragraph()
    post_p.paragraph_format.space_before = Pt(0)
    post_p.paragraph_format.space_after = Pt(6)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, type=Path)
    parser.add_argument("--docx", required=True, type=Path)
    args = parser.parse_args()
    out = convert_markdown_to_docx(args.md, args.docx)
    print(f"Generated DOCX: {out}")


if __name__ == "__main__":
    main()
