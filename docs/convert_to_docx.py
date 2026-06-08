"""Convert defense_qa_comprehensive.md to a well-formatted Word document."""
import re
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

MD_PATH = "/Users/lanyuanzhe/Documents/GitHub/algaeimage/docs/defense_qa_comprehensive.md"
DOCX_PATH = "/Users/lanyuanzhe/Documents/GitHub/algaeimage/docs/defense_qa_comprehensive.docx"


def set_cell_shading(cell, color_hex):
    """Set cell background color."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def add_code_block(doc, code_text):
    """Add a code block paragraph with monospace font and gray background."""
    for line in code_text.strip().split("\n"):
        p = doc.add_paragraph()
        p.style = doc.styles["Code"]
        run = p.add_run(line)
        # style already applied via paragraph style
    # Remove trailing empty paragraph if code block ended with newline
    if code_text.endswith("\n"):
        # The last paragraph we added is for a trailing empty line — remove it
        pass  # we handle this by stripping code_text before split


def convert_md_to_docx(md_path, docx_path):
    doc = Document()

    # ── Page setup ──
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    # ── Style definitions ──
    style = doc.styles["Normal"]
    style.font.name = "微软雅黑"
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.35
    # Set East Asian font
    rPr = style.element.get_or_add_rPr()
    rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="微软雅黑"/>')
    rPr.append(rFonts)

    # Heading styles
    for level, (size, color_hex, bold) in enumerate(
        [(24, "1a5276", True), (16, "2471a3", True), (13, "2e86c1", True)], start=1
    ):
        h_style = doc.styles[f"Heading {level}"]
        h_style.font.name = "微软雅黑"
        h_style.font.size = Pt(size)
        h_style.font.bold = bold
        h_style.font.color.rgb = RGBColor.from_string(color_hex)
        h_style.paragraph_format.space_before = Pt(18 if level == 1 else 14)
        h_style.paragraph_format.space_after = Pt(8)
        h_rPr = h_style.element.get_or_add_rPr()
        h_rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="微软雅黑"/>')
        h_rPr.append(h_rFonts)

    # Code style
    code_style = doc.styles.add_style("Code", WD_STYLE_TYPE.PARAGRAPH)
    code_style.font.name = "Consolas"
    code_style.font.size = Pt(8.5)
    code_style.paragraph_format.space_before = Pt(2)
    code_style.paragraph_format.space_after = Pt(2)
    code_style.paragraph_format.line_spacing = 1.15
    code_style.paragraph_format.left_indent = Cm(0.5)

    # ── Parse Markdown ──
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # ── Blank line ──
        if not line:
            i += 1
            continue

        # ── Horizontal rule ──
        if line.strip() == "---":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            pPr = p._p.get_or_add_pPr()
            pBdr = parse_xml(
                f'<w:pBdr {nsdecls("w")}>'
                f'<w:bottom w:val="single" w:sz="6" w:space="1" w:color="bdc3c7"/>'
                f"</w:pBdr>"
            )
            pPr.append(pBdr)
            i += 1
            continue

        # ── Blockquote ──
        if line.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            quote_text = " ".join(quote_lines)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1.0)
            run = p.add_run(quote_text)
            run.italic = True
            run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            run.font.size = Pt(10)
            continue

        # ── Code block ──
        if line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].rstrip().startswith("```"):
                code_lines.append(lines[i].rstrip())
                i += 1
            i += 1  # skip closing ```
            code_text = "\n".join(code_lines)
            for cl in code_lines:
                p = doc.add_paragraph()
                p.style = doc.styles["Code"]
                run = p.add_run(cl if cl else " ")
            continue

        # ── Table ──
        if line.startswith("|") and line.strip().endswith("|"):
            # Collect all table lines
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].rstrip())
                i += 1

            # Remove separator line (e.g. |:---|:---|)
            body_lines = []
            for tl in table_lines:
                stripped = tl.strip()
                # Check if this is a separator line (only contains |, :, -, spaces)
                if re.match(r"^\|[\s\-:|]+\|$", stripped):
                    continue
                body_lines.append(stripped)

            if not body_lines:
                continue

            # Parse cells
            rows = []
            for bl in body_lines:
                cells = [c.strip() for c in bl.split("|")[1:-1]]
                rows.append(cells)

            num_cols = max(len(r) for r in rows)
            num_rows = len(rows)

            table = doc.add_table(rows=num_rows, cols=num_cols)
            table.style = "Light Grid Accent 1"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True

            for ri, row_cells in enumerate(rows):
                for ci, cell_text in enumerate(row_cells):
                    if ci < num_cols:
                        cell = table.rows[ri].cells[ci]
                        cell.text = ""
                        p = cell.paragraphs[0]
                        run = p.add_run(cell_text)
                        run.font.size = Pt(9)
                        run.font.name = "微软雅黑"
                        if ri == 0:
                            run.bold = True
                            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                            set_cell_shading(cell, "2471a3")
            doc.add_paragraph()  # spacing after table
            continue

        # ── Heading 1 (# ) ──
        if line.startswith("# ") and not line.startswith("## "):
            doc.add_heading(line[2:].strip(), level=1)
            i += 1
            continue

        # ── Heading 2 (## ) ──
        if line.startswith("## ") and not line.startswith("### "):
            doc.add_heading(line[3:].strip(), level=2)
            i += 1
            continue

        # ── Heading 3 (### ) ──
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
            i += 1
            continue

        # ── Unordered list (- or *) ──
        if re.match(r"^[\-\*] ", line):
            p = doc.add_paragraph(style="List Bullet")
            _add_markdown_inline(p, line[2:])
            i += 1
            continue

        # ── Ordered list (1. ) ──
        list_match = re.match(r"^\d+\.\s+(.+)", line)
        if list_match:
            p = doc.add_paragraph(style="List Number")
            _add_markdown_inline(p, list_match.group(1))
            i += 1
            continue

        # ── Regular paragraph ──
        # Check for inline bold/code within paragraph
        p = doc.add_paragraph()
        _add_markdown_inline(p, line)
        i += 1

    doc.save(docx_path)
    print(f"Saved: {docx_path}")


def _add_markdown_inline(paragraph, text):
    """Parse inline markdown: **bold**, *italic*, `code`, [link](url)."""
    # Pattern for inline elements
    pattern = re.compile(
        r"(\*\*(.+?)\*\*|"  # **bold**
        r"\_\_(.+?)\_\_|"  # __bold__
        r"\[([^\]]+)\]\(([^)]+)\)|"  # [text](url)
        r"`([^`]+)`|"  # `code`
        r"\*(.+?)\*)"  # *italic*
    )

    last_end = 0
    for m in pattern.finditer(text):
        # Add plain text before this match
        if m.start() > last_end:
            run = paragraph.add_run(text[last_end : m.start()])

        if m.group(2):  # **bold**
            run = paragraph.add_run(m.group(2))
            run.bold = True
        elif m.group(3):  # __bold__
            run = paragraph.add_run(m.group(3))
            run.bold = True
        elif m.group(4):  # [text](url)
            run = paragraph.add_run(m.group(4))
            run.underline = True
            run.font.color.rgb = RGBColor(0x24, 0x71, 0xA3)
        elif m.group(6):  # `code`
            run = paragraph.add_run(m.group(6))
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif m.group(7):  # *italic*
            run = paragraph.add_run(m.group(7))
            run.italic = True

        last_end = m.end()

    # Add remaining text
    if last_end < len(text):
        paragraph.add_run(text[last_end:])


if __name__ == "__main__":
    convert_md_to_docx(MD_PATH, DOCX_PATH)
