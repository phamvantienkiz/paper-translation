import html
from pathlib import Path

import pymupdf

from app.core.config import settings
from app.core.logging import logger
from app.models.math_token import MathTokenModel
from app.models.segment import PaperSegmentModel
from app.models.session import PaperSessionModel
from app.services.parser.math_isolator import LaTeXIsolator


def markdown_table_to_html(md_table: str) -> str:
    """Chuyển đổi bảng Markdown sang thẻ <table> HTML chuẩn hóa."""
    lines = [line.strip() for line in md_table.strip().splitlines() if line.strip()]
    if not lines or "|" not in lines[0]:
        return f"<pre>{html.escape(md_table)}</pre>"

    html_rows = []
    is_header = True
    for line in lines:
        if line.startswith("|-") or line.startswith("| -") or ":---" in line or "|---" in line:
            is_header = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        tag = "th" if is_header else "td"
        row_content = "".join([f"<{tag}>{html.escape(c)}</{tag}>" for c in cells])
        html_rows.append(f"<tr>{row_content}</tr>")
        if is_header:
            is_header = False

    return f'<table class="paper-table"><tbody>{"".join(html_rows)}</tbody></table>'


class PDFExporter:
    """Dịch vụ xuất bản dịch bài báo ra tệp PDF chuẩn báo cáo khoa học."""

    def __init__(self, export_dir: Path | None = None):
        self.export_dir = export_dir or (settings.STORAGE_DIR / "exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_document(
        self,
        session: PaperSessionModel,
        segments: list[PaperSegmentModel],
        math_tokens: list[MathTokenModel],
    ) -> str:
        """Tạo mã nguồn HTML hoàn chỉnh chứa đầy đủ tiêu đề, các đoạn dịch, bảng và công thức."""
        # 1. Tạo bản đồ token toán học để re-inject
        token_map: dict[str, str] = {t.token_placeholder: t.raw_latex for t in math_tokens}

        paper_title = html.escape(session.title or session.file_name or "Bài báo khoa học")

        body_elements = []

        for seg in segments:
            # Ưu tiên lấy bản dịch, nếu chưa dịch thì dùng bản gốc
            raw_text = seg.translated_content or seg.original_content or ""
            # Re-inject công thức toán LaTeX gốc
            restored_text = LaTeXIsolator.reinject_formulas(raw_text, token_map)

            if seg.segment_type == "TITLE":
                body_elements.append(f'<h1 class="paper-title">{html.escape(restored_text)}</h1>')
            elif seg.segment_type == "HEADING":
                body_elements.append(f'<h2 class="section-heading">{html.escape(restored_text)}</h2>')
            elif seg.segment_type == "TABLE":
                table_html = markdown_table_to_html(restored_text)
                body_elements.append(f'<div class="table-container">{table_html}</div>')
            elif seg.segment_type == "MATH_DISPLAY":
                body_elements.append(
                    f'<div class="math-display-box"><code>{html.escape(restored_text)}</code></div>'
                )
            elif seg.segment_type == "FIGURE":
                fig_html = ""
                if seg.media_path:
                    # Đường dẫn tuyệt đối local để WeasyPrint / trình duyệt nạp ảnh
                    local_img_path = seg.media_path
                    if local_img_path.startswith("/api/v1/assets/"):
                        rel_path = local_img_path.replace("/api/v1/assets/", "")
                        abs_img_file = settings.STORAGE_DIR / "assets" / rel_path
                        if abs_img_file.exists():
                            local_img_path = abs_img_file.as_uri()
                    fig_html = f'<div class="figure-container"><img src="{local_img_path}" class="figure-img" /></div>'
                caption = f'<p class="figure-caption"><em>{html.escape(restored_text)}</em></p>' if restored_text else ""
                body_elements.append(f'{fig_html}{caption}')
            else:
                # Segment PARAGRAPH thông thường: làm nổi bật các công thức $...$
                escaped_p = html.escape(restored_text)
                # Đổi dòng và giữ format
                formatted_p = escaped_p.replace("\n", "<br/>")
                body_elements.append(f'<p class="body-paragraph">{formatted_p}</p>')

        body_html = "\n".join(body_elements)

        full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>{paper_title}</title>
<style>
  @page {{
    size: A4;
    margin: 25mm 20mm 25mm 20mm;
    @top-right {{
      content: "Paper Translation — Bản dịch Tiếng Việt";
      font-size: 8pt;
      color: #64748b;
      font-style: italic;
    }}
    @bottom-center {{
      content: "Trang " counter(page) " / " counter(pages);
      font-size: 8pt;
      color: #64748b;
    }}
  }}
  body {{
    font-family: 'Times New Roman', Times, 'DejaVu Serif', serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1e293b;
    margin: 0;
    padding: 0;
  }}
  .paper-header {{
    text-align: center;
    margin-bottom: 25px;
    padding-bottom: 15px;
    border-bottom: 1px solid #cbd5e1;
  }}
  .paper-title {{
    font-size: 18pt;
    font-weight: bold;
    color: #0f172a;
    line-height: 1.3;
    margin: 0 0 10px 0;
  }}
  .paper-badge {{
    display: inline-block;
    font-family: monospace;
    font-size: 8.5pt;
    background: #e0e7ff;
    color: #3730a3;
    padding: 2px 8px;
    border-radius: 4px;
    margin-top: 5px;
  }}
  .section-heading {{
    font-size: 13pt;
    font-weight: bold;
    color: #1e3a8a;
    margin-top: 20px;
    margin-bottom: 8px;
    border-bottom: 0.5px solid #e2e8f0;
    padding-bottom: 4px;
  }}
  .body-paragraph {{
    text-align: justify;
    text-justify: inter-word;
    margin: 0 0 10px 0;
    text-indent: 1.5em;
  }}
  .math-display-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 12px 0;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 9.5pt;
  }}
  .table-container {{
    margin: 15px 0;
    overflow-x: auto;
  }}
  .paper-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
    margin: 0 auto;
  }}
  .paper-table th, .paper-table td {{
    border: 1px solid #cbd5e1;
    padding: 6px 10px;
    text-align: left;
  }}
  .paper-table th {{
    background: #f1f5f9;
    font-weight: bold;
    color: #0f172a;
  }}
  .paper-table tr:nth-child(even) {{
    background: #f8fafc;
  }}
  .figure-container {{
    text-align: center;
    margin: 15px 0 5px 0;
  }}
  .figure-img {{
    max-width: 85%;
    max-height: 300px;
    object-fit: contain;
  }}
  .figure-caption {{
    text-align: center;
    font-size: 8.5pt;
    color: #475569;
    margin-top: 4px;
  }}
</style>
</head>
<body>
  <div class="paper-header">
    <div class="paper-badge">BẢN DỊCH SONG NGỮ KHOA HỌC IT / AI</div>
  </div>
  {body_html}
</body>
</html>"""
        return full_html

    def export_pdf(
        self,
        session: PaperSessionModel,
        segments: list[PaperSegmentModel],
        math_tokens: list[MathTokenModel],
    ) -> Path:
        """Xuất tài liệu sang tệp PDF. Tự động hỗ trợ WeasyPrint kèm fallback PyMuPDF đảm bảo chạy thông suốt."""
        output_filename = f"{session.id}_translated.pdf"
        output_path = self.export_dir / output_filename

        html_content = self.generate_html_document(session, segments, math_tokens)

        # 1. Thử nghiệm sinh PDF bằng WeasyPrint
        try:
            import weasyprint
            logger.info(f"[{session.id}] Đang biên dịch PDF qua WeasyPrint...")
            weasyprint.HTML(string=html_content).write_pdf(str(output_path))
            logger.info(f"[{session.id}] Xuất PDF qua WeasyPrint thành công: {output_path}")
            return output_path
        except (ImportError, OSError, Exception) as weasy_err:
            logger.warning(
                f"[{session.id}] WeasyPrint không khả dụng ({weasy_err}). Tự động chuyển đổi sang PyMuPDF Layout Engine."
            )

        # 2. Fallback: Sinh PDF học thuật đa trang tiêu chuẩn bằng PyMuPDF
        return self._export_via_pymupdf(session, segments, math_tokens, output_path)

    def _export_via_pymupdf(
        self,
        session: PaperSessionModel,
        segments: list[PaperSegmentModel],
        math_tokens: list[MathTokenModel],
        output_path: Path,
    ) -> Path:
        """Sinh tệp PDF bằng PyMuPDF thuần túy (không phụ thuộc external C libraries)."""
        token_map = {t.token_placeholder: t.raw_latex for t in math_tokens}
        doc = pymupdf.open()

        page_width, page_height = 595.0, 842.0  # A4 standard points
        margin_x, margin_top, margin_bottom = 50.0, 60.0, 60.0
        content_width = page_width - (margin_x * 2)

        def add_new_page(doc_obj) -> pymupdf.Page:
            p = doc_obj.new_page(width=page_width, height=page_height)
            # Header
            p.insert_text(
                (margin_x, 35),
                "Paper Translation — Bản dịch Tiếng Việt",
                fontsize=8,
                color=(0.4, 0.45, 0.5),
            )
            return p

        current_page = add_new_page(doc)
        current_y = margin_top

        # Tiêu đề bài báo
        title_text = session.title or session.file_name or "Bài báo khoa học"
        rect = pymupdf.Rect(margin_x, current_y, margin_x + content_width, current_y + 60)
        current_page.insert_textbox(rect, title_text, fontsize=16, fontname="helv", color=(0.1, 0.15, 0.3))
        current_y += 65

        for seg in segments:
            raw_text = seg.translated_content or seg.original_content or ""
            text = LaTeXIsolator.reinject_formulas(raw_text, token_map).strip()
            if not text:
                continue

            fontsize = 10
            fontname = "times-roman"
            color = (0.1, 0.1, 0.1)

            if seg.segment_type in ("TITLE", "HEADING"):
                fontsize = 13
                fontname = "helv"
                color = (0.1, 0.2, 0.55)
                current_y += 10
            elif seg.segment_type == "MATH_DISPLAY":
                fontsize = 9.5
                fontname = "courier"
                color = (0.2, 0.2, 0.2)
                text = f"[Công thức]: {text}"

            # Ước lượng chiều cao cần thiết
            estimated_lines = max(1, len(text) // 80 + text.count("\n") + 1)
            estimated_height = estimated_lines * (fontsize * 1.5)

            if current_y + estimated_height > page_height - margin_bottom:
                current_page = add_new_page(doc)
                current_y = margin_top

            rect = pymupdf.Rect(margin_x, current_y, margin_x + content_width, current_y + estimated_height + 20)
            rendered_height = current_page.insert_textbox(
                rect, text, fontsize=fontsize, fontname=fontname, color=color
            )
            # Nếu rendered_height âm (vượt quá rect), cho sang trang mới
            if rendered_height < 0:
                current_page = add_new_page(doc)
                current_y = margin_top
                rect = pymupdf.Rect(margin_x, current_y, margin_x + content_width, page_height - margin_bottom)
                current_page.insert_textbox(rect, text, fontsize=fontsize, fontname=fontname, color=color)
                current_y += estimated_height + 8
            else:
                current_y += max(rendered_height, estimated_height) + 8

        # Thêm số trang footer cho tất cả các trang
        total_pages = len(doc)
        for page_idx in range(total_pages):
            p = doc[page_idx]
            footer_text = f"Trang {page_idx + 1} / {total_pages}"
            p.insert_text(
                (page_width / 2 - 25, page_height - 30),
                footer_text,
                fontsize=8,
                color=(0.4, 0.45, 0.5),
            )

        doc.save(str(output_path))
        doc.close()
        logger.info(f"[{session.id}] Xuất PDF qua PyMuPDF Engine hoàn tất: {output_path}")
        return output_path
