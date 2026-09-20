#!/usr/bin/env python3
"""Convert research manuscript Markdown documents into professionally styled 2-column Word (.docx) files matching the official Jurnal Kejuruteraan template."""

import re
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

# Colors matching the official academic template and modern journal standards
COLOR_PRIMARY = RGBColor(0, 0, 0)       # Black standard in Jurnal Kejuruteraan
COLOR_DARK = RGBColor(0, 0, 0)          # Black text
COLOR_MID = RGBColor(110, 110, 110)
HEX_HEADER_BG = "F2F4F4"
HEX_BORDER = "000000"

# Explicit column widths for each table (to prevent overlapping text)
# In 2-column mode, column width is ~2.90 inches.
# In 1-column mode (wide table), total width is ~6.27 inches.
TABLE_WIDTHS_COL = {
    3: [Inches(0.95), Inches(1.15), Inches(0.80)],   # Table 1: Variable, Def, Sign (2.90 in)
    3: [Inches(1.05), Inches(1.10), Inches(0.75)],   # Table 2: Char, Category, n(%) (2.90 in)
    2: [Inches(1.70), Inches(1.20)],                 # Table 3: Stage, Obs (2.90 in)
    3: [Inches(1.00), Inches(0.95), Inches(0.95)],   # Table 4: Variable, Basic, MNL+ASC (2.90 in)
}

TABLE_WIDTHS_WIDE = {
    6: [Inches(1.47), Inches(0.95), Inches(0.85), Inches(0.95), Inches(0.95), Inches(1.10)],  # Table 5: Spec, LL, rho2, AIC, BIC, p (6.27 in)
}


def _set_section_layout(section, num_cols=1, col_space_dxa=708, continuous=True):
    """Configure section column layout and continuous break."""
    sectPr = section._sectPr
    for elem in sectPr.xpath('./w:type | ./w:cols'):
        sectPr.remove(elem)
    if continuous:
        sectPr.append(parse_xml(f'<w:type {nsdecls("w")} w:val="continuous"/>'))
    sectPr.append(parse_xml(f'<w:cols {nsdecls("w")} w:num="{num_cols}" w:space="{col_space_dxa}"/>'))


def _set_cell_border(cell, **kwargs):
    """Set cell borders with XML formatting (APA/IEEE 3-line standard)."""
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


def _insert_latex_math_equation(doc, formula_text):
    """Insert clean native OMML equation or styled math block into Word document."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)

    def sub(b, s):
        return (
            f'<m:sSub xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            f'<m:e><m:r><m:t>{b}</m:t></m:r></m:e>'
            f'<m:sub><m:r><m:t>{s}</m:t></m:r></m:sub>'
            f'</m:sSub>'
        )

    def txt(t):
        return f'<m:r xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:t>{t}</m:t></m:r>'

    # Equation 1: Utility specification
    if "U_{ij}" in formula_text:
        omml = (
            f'<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            f'<m:oMath>'
            f'{sub("U", "ij")} {txt("=")} '
            f'{sub("β", "time")}{sub("Time", "ij")} {txt("+")} '
            f'{sub("β", "cost")}{sub("Cost", "ij")} {txt("+")} '
            f'{sub("β", "transfer")}{sub("Transfer", "ij")} {txt("+")} '
            f'{sub("β", "access")}{sub("Access", "ij")} {txt("+")} '
            f'{sub("β", "comfort")}{sub("Comfort", "ij")} {txt("+")} '
            f'{sub("β", "reliability")}{sub("Reliability", "ij")}'
            f'</m:oMath>'
            f'</m:oMathPara>'
        )
        p._p.append(parse_xml(omml))
    # Equation 2: MNL probability
    elif "P_{ij}" in formula_text:
        num = f'{txt("exp(")}{sub("U", "ij")}{txt(")")}'
        sum_denom = (
            f'<m:nary xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            f'<m:naryPr><m:chr m:val="∑"/></m:naryPr>'
            f'<m:sub><m:r><m:t>m</m:t></m:r></m:sub>'
            f'<m:sup/>'
            f'<m:e>{txt("exp(")}{sub("U", "im")}{txt(")")}</m:e>'
            f'</m:nary>'
        )
        frac = f'<m:f xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:num>{num}</m:num><m:den>{sum_denom}</m:den></m:f>'
        omml = (
            f'<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            f'<m:oMath>'
            f'{sub("P", "ij")} {txt("=")} {frac}'
            f'</m:oMath>'
            f'</m:oMathPara>'
        )
        p._p.append(parse_xml(omml))
    else:
        # Fallback styled equation run
        run = p.add_run(formula_text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(9.5)
        run.italic = True


def _format_inline_text(paragraph, text):
    """Parse basic inline markdown bold and italic formatting."""
    tokens = re.split(r'(\*\*.*?\*\*)', text)
    for token in tokens:
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            content = token[2:-2]
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
            sub_tokens = re.split(r'(\*.*?\*)', token)
            for st in sub_tokens:
                if st.startswith('*') and st.endswith('*') and len(st) >= 2:
                    r = paragraph.add_run(st[1:-1])
                    r.italic = True
                else:
                    r = paragraph.add_run(st)
                r.font.name = "Times New Roman"


def convert_markdown_to_docx(md_path: Path, docx_path: Path) -> Path:
    """Convert manuscript Markdown into 2-column Word Document matching template layout."""
    md_path = Path(md_path)
    docx_path = Path(docx_path)
    content = md_path.read_text(encoding="utf-8")
    base_dir = md_path.parent

    doc = docx.Document()

    # Section 0: Title & Abstract (1 Column, A4, 1-inch margins)
    s0 = doc.sections[0]
    s0.page_width = Inches(8.27)
    s0.page_height = Inches(11.69)
    s0.top_margin = Inches(1.0)
    s0.bottom_margin = Inches(1.0)
    s0.left_margin = Inches(1.0)
    s0.right_margin = Inches(1.0)
    _set_section_layout(s0, num_cols=1, continuous=False)

    lines = content.splitlines()
    i = 0
    current_cols = 1

    # Header Journal metadata
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(2)
    r_meta = p_meta.add_run("Jurnal Kejuruteraan (Journal of Engineering) Online First | ISSN: 0128-0198 E-ISSN: 2289-7526")
    r_meta.font.name = "Times New Roman"
    r_meta.font.size = Pt(8.5)
    r_meta.font.color.rgb = COLOR_MID

    while i < len(lines):
        line = lines[i].rstrip()

        # Title (# Title)
        if line.startswith('# '):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(12)
            run = p.add_run(line[2:].strip())
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            i += 1
            continue

        # Abstract header (## ABSTRAK / ## ABSTRACT)
        if line == '## ABSTRAK' or line == '## ABSTRACT':
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(line[3:].strip())
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10.5)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            i += 1
            continue

        # Keywords line
        if line.startswith('**Kata kunci:**') or line.startswith('**Keywords:**'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(14)
            _format_inline_text(p, line)
            for r in p.runs:
                r.font.size = Pt(9.5)

            # Switch to 2-column layout starting from INTRODUCTION
            s_body = doc.add_section()
            _set_section_layout(s_body, num_cols=2, col_space_dxa=708, continuous=True)
            current_cols = 2

            i += 1
            continue

        # Heading 1 (## PENDAHULUAN / ## INTRODUCTION / etc.)
        if line.startswith('## '):
            h_text = line[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(h_text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(10)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            i += 1
            continue

        # Heading 2 (### Subheading)
        if line.startswith('### '):
            h_text = line[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(h_text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(9.5)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY
            i += 1
            continue

        # Blank line
        if not line:
            i += 1
            continue

        # Wide Table: if markdown table has >= 5 columns (Table 5), switch to 1-column section
        # Smaller tables (Tables 1-4) stay inside the 2-column layout with explicit cell widths
        if line.startswith('|') and line.endswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].rstrip().startswith('|') and lines[i].rstrip().endswith('|'):
                table_lines.append(lines[i].rstrip())
                i += 1

            num_cols_table = max(len([c for c in l.strip('|').split('|')]) for l in table_lines)
            is_wide_table = (num_cols_table >= 5)

            if is_wide_table and current_cols == 2:
                # Switch to 1 column for wide table
                s_wide = doc.add_section()
                _set_section_layout(s_wide, num_cols=1, continuous=True)
                current_cols = 1

            _build_docx_table(doc, table_lines, is_wide=is_wide_table)

            if is_wide_table and current_cols == 1:
                # Switch back to 2 columns after wide table
                s_back = doc.add_section()
                _set_section_layout(s_back, num_cols=2, col_space_dxa=708, continuous=True)
                current_cols = 2

            continue

        # Images: fit nicely into the current column (width=2.85 in in 2-col)
        # Figure 1, Figure 3, Figure 6 are wide complex diagrams -> switch to 1 column (width=6.0 in)
        img_match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if img_match:
            img_rel_path = img_match.group(2)
            full_img_path = (base_dir / img_rel_path).resolve()
            if full_img_path.exists():
                is_wide_fig = any(k in str(full_img_path) for k in ("figure_01", "figure_03", "figure_06"))

                if is_wide_fig and current_cols == 2:
                    s_fig = doc.add_section()
                    _set_section_layout(s_fig, num_cols=1, continuous=True)
                    current_cols = 1
                elif not is_wide_fig and current_cols == 1:
                    s_back = doc.add_section()
                    _set_section_layout(s_back, num_cols=2, col_space_dxa=708, continuous=True)
                    current_cols = 2

                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(8)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.keep_with_next = True
                run = p.add_run()

                # Width: 6.0 in for wide figures in 1-col; 2.85 in for figures inside 2-col
                target_width = Inches(6.0) if current_cols == 1 else Inches(2.85)
                run.add_picture(str(full_img_path), width=target_width)

            i += 1
            continue

        # Figure / Table Caption line
        if re.match(r'^(FIGURE|GAMBAR|TABLE|TABEL)\s+\d+\.', line):
            is_caption_for_wide_fig = any(k in line for k in ("FIGURE 1", "GAMBAR 1", "FIGURE 3", "GAMBAR 3", "FIGURE 6", "GAMBAR 6"))
            is_caption_for_wide_tbl = any(k in line for k in ("TABLE 5", "TABEL 5"))

            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.keep_with_next = True if line.startswith(('TABLE', 'TABEL')) else False
            run = p.add_run(line.strip())
            run.font.name = 'Times New Roman'
            run.font.size = Pt(9.0)
            run.bold = True
            run.font.color.rgb = COLOR_PRIMARY

            # If this was caption for wide figure, return to 2-column layout for text
            if line.startswith(('FIGURE', 'GAMBAR')) and is_caption_for_wide_fig and current_cols == 1:
                s_back = doc.add_section()
                _set_section_layout(s_back, num_cols=2, col_space_dxa=708, continuous=True)
                current_cols = 2

            i += 1
            continue

        # Display math block (LaTeX $$...$$ or \[...\])
        is_math_block = line.startswith('$$') or line.startswith(r'\[')
        if is_math_block:
            end_marker = '$$' if line.startswith('$$') else r'\]'
            math_lines = [line]
            if not (line.endswith(end_marker) and len(line) > 2):
                while i + 1 < len(lines):
                    i += 1
                    line = lines[i].rstrip()
                    math_lines.append(line)
                    if line.endswith(end_marker):
                        break
            formula_text = " ".join(math_lines).replace('$$', '').replace(r'\[', '').replace(r'\]', '').strip()
            _insert_latex_math_equation(doc, formula_text)
            i += 1
            continue

        # Notes
        if line.startswith('**Catatan:**') or line.startswith('**Note:**'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(6)
            _format_inline_text(p, line)
            for r in p.runs:
                r.font.size = Pt(8.0)
                r.font.color.rgb = COLOR_MID
            i += 1
            continue

        # Standard paragraph text
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.05
        _format_inline_text(p, line)
        for r in p.runs:
            if not r.font.size:
                r.font.size = Pt(9.5) if current_cols == 2 else Pt(10)

        i += 1

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))
    return docx_path


def _build_docx_table(doc, table_lines, is_wide=False):
    """Parse markdown table lines and generate academic 3-line table with explicit cell widths."""
    parsed_rows = []
    for l in table_lines:
        cells = [c.strip() for c in l.strip('|').split('|')]
        if all(re.match(r'^:?-+:?$', c) for c in cells if c):
            continue
        parsed_rows.append(cells)

    if not parsed_rows:
        return

    num_rows = len(parsed_rows)
    num_cols = max(len(r) for r in parsed_rows)

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Determine explicit column widths
    if is_wide and num_cols in TABLE_WIDTHS_WIDE:
        col_widths = TABLE_WIDTHS_WIDE[num_cols]
    elif not is_wide and num_cols in TABLE_WIDTHS_COL:
        col_widths = TABLE_WIDTHS_COL[num_cols]
    else:
        # Fallback distribution
        total_w = 6.0 if is_wide else 2.85
        col_widths = [Inches(total_w / num_cols)] * num_cols

    # Apply widths to columns
    for c_idx, w in enumerate(col_widths):
        if c_idx < len(table.columns):
            table.columns[c_idx].width = w

    for row_idx, row_data in enumerate(parsed_rows):
        is_header = (row_idx == 0)
        tr = table.rows[row_idx]
        tr.height = Pt(16 if is_header else 14)

        for col_idx, cell_value in enumerate(row_data):
            cell = tr.cells[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if col_idx < len(col_widths):
                cell.width = col_widths[col_idx]

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)

            val_clean = cell_value.replace('**', '').strip()
            if re.match(r'^[−\-+]?[0-9\.,]+%?$', val_clean) or val_clean in ('—', '−'):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            _format_inline_text(p, cell_value)

            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(7.8 if is_wide else 8.2)
                if is_header:
                    r.bold = True
                    r.font.color.rgb = COLOR_PRIMARY
                else:
                    r.font.color.rgb = COLOR_DARK

            # Borders: APA/IEEE 3-line table format
            if is_header:
                _set_cell_background(cell, HEX_HEADER_BG)
                _set_cell_border(cell, top="single", top_sz="12", top_color="000000",
                                 bottom="single", bottom_sz="6", bottom_color="000000")
            elif row_idx == num_rows - 1:
                _set_cell_border(cell, bottom="single", bottom_sz="12", bottom_color="000000")
            else:
                _set_cell_border(cell, bottom="single", bottom_sz="4", bottom_color="E0E0E0")

    post_p = doc.add_paragraph()
    post_p.paragraph_format.space_before = Pt(0)
    post_p.paragraph_format.space_after = Pt(4)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, type=Path)
    parser.add_argument("--docx", required=True, type=Path)
    args = parser.parse_args()
    out = convert_markdown_to_docx(args.md, args.docx)
    print(f"Generated Clean 2-Column DOCX: {out}")


if __name__ == "__main__":
    main()
