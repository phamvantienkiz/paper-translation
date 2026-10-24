import html
import io
from pathlib import Path
import re

from PIL import Image
import pymupdf

from app.core.config import settings
from app.core.logging import logger
from app.models.math_token import MathTokenModel
from app.models.segment import PaperSegmentModel
from app.models.session import PaperSessionModel
from app.schemas.canvas import CanvasDataResponse
from app.services.parser.math_isolator import LaTeXIsolator

TABLE_CAPTION_REGEX = re.compile(r"^(?:table\s+\d+|bảng\s+\d+)", re.IGNORECASE)
FIGURE_CAPTION_REGEX = re.compile(r"^(?:figure\s+\d+|fig\.\s*\d+|hình\s+\d+)", re.IGNORECASE)
JUNK_WATERMARK_REGEX = re.compile(
    r"(?:accepted\s+to\s+cvpr|cvpr\s+\d{4}\s+paper|this\s+cvpr\s+paper\s+is\s+the\s+open\s+access\s+version|except\s+for\s+this\s+watermark|the\s+final\s+published\s+version)",
    re.IGNORECASE,
)

MATH_REPLACEMENTS = [
    (r"\\mathbf\s*\{\s*([a-zA-Z0-9]+)\s*\}", r"<b>\1</b>"),
    (r"\\textbf\s*\{\s*([^}]+)\s*\}", r"<b>\1</b>"),
    (r"\\mathrm\s*\{\s*([^}]+)\s*\}", r"\1"),
    (r"\\operatorname\s*\{\s*([^}]+)\s*\}", r"\1"),
    (r"\\mathcal\s*\{\s*([a-zA-Z])\s*\}", r"<i>\1</i>"),
    (r"\\hat\s*\{\s*([a-zA-Z])\s*\}", r"\1&#770;"),
    (r"\\otimes", "&#8855;"),
    (r"\\cdot", "&#8901;"),
    (r"\\nabla", "&#8711;"),
    (r"\\gamma", "&#947;"),
    (r"\\lambda", "&#955;"),
    (r"\\uparrow", "&#8593;"),
    (r"\\downarrow", "&#8595;"),
    (r"\\rightarrow", "&#8594;"),
    (r"\\qquad|\\quad|\\;", " &nbsp; "),
    (r"\\left\(", "("),
    (r"\\right\)", ")"),
    (r"\\left\[", "["),
    (r"\\right\]", "]"),
    (r"\\\|", "||"),
    (r"_\s*\{\s*([^}]+)\s*\}", r"<sub>\1</sub>"),
    (r"\^\s*\{\s*([^}]+)\s*\}", r"<sup>\1</sup>"),
    (r"_\s*([a-zA-Z0-9])", r"<sub>\1</sub>"),
    (r"\^\s*([a-zA-Z0-9])", r"<sup>\1</sup>"),
]


def format_latex_to_html(text: str) -> str:
    """Chuyển đổi công thức LaTeX ($...$) sang định dạng HTML học thuật rõ ràng (serif, bold, math symbols)."""
    parts = re.split(r"(\$[^\$]+\$)", text)
    result = []
    for part in parts:
        if part.startswith("$") and part.endswith("$") and len(part) >= 2:
            inner = part[1:-1]
            for pat, sub in MATH_REPLACEMENTS:
                inner = re.sub(pat, sub, inner)
            inner = re.sub(r"\\([a-zA-Z]+)", r"\1", inner)
            result.append(f'<span class="math-formula"><i>{inner.strip()}</i></span>')
        else:
            result.append(html.escape(part).replace("\n", "<br/>"))
    return "".join(result)


def clean_figure_caption_text(caption: str) -> str:
    """Loại bỏ nhãn rác OCR dính phía trước chú thích hình/bảng (ví dụ: 'Input RetinexFormer [3] Figure 6...')."""
    cleaned = re.sub(r"^(?:[^\n]*\n)*?(?=(?:figure|fig\.|hình)\s*\d+)", "", caption, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:[^\n]*\n)*?(?=(?:table|bảng)\s*\d+)", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() if cleaned.strip() else caption.strip()


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

    def generate_canvas_html(
        self,
        session: PaperSessionModel,
        canvas_data: CanvasDataResponse,
        archive: pymupdf.Archive,
    ) -> str:
        """
        Biên dịch bố cục Canvas (3-Layer Canvas Flow) thành mã HTML học thuật hoàn chỉnh:
        - Tái hiện chính xác luồng đọc 1 cột (Tiêu đề -> Tác giả -> Cột trái -> Cột phải).
        - Trích xuất và nhúng ảnh hình vẽ (Figure) và bảng biểu (Table) từ các trang gốc.
        - Khôi phục công thức toán LaTeX và các chỉnh sửa của người dùng (is_user_edited).
        - Lọc bỏ watermark rác và header/footer trùng lặp.
        """
        pages_dir = settings.pages_dir / session.id
        body_elements: list[str] = []
        img_counter = 0

        for page_idx, page in enumerate(canvas_data.pages):
            page_img_path = pages_dir / f"page_{page.page_number}.png"
            pil_page_img = None
            if page_img_path.is_file():
                try:
                    pil_page_img = Image.open(page_img_path)
                except Exception as img_err:
                    logger.warning(f"Không thể mở ảnh trang {page.page_number}: {img_err}")

            raw_blocks = page.blocks or []
            consumed_ids: set[str] = set()

            # 1. Bỏ qua header/footer, watermark rác và số phương trình rời rạc
            for b in raw_blocks:
                label = (b.label or "").lower()
                orig = (b.original_text or "").strip()
                if label in ("page header", "page footer"):
                    consumed_ids.add(b.id)
                    continue
                if len(orig) < 250 and JUNK_WATERMARK_REGEX.search(orig):
                    consumed_ids.add(b.id)
                    continue
                if re.match(r"^\(\d+\)$", orig):
                    consumed_ids.add(b.id)
                    continue

            # 2. Nhóm bảng biểu (Table)
            table_groups: dict[str, dict] = {}
            for i, b in enumerate(raw_blocks):
                if b.id in consumed_ids:
                    continue
                orig = (b.original_text or "").strip()
                trans = (b.translated_text or "").strip()
                if TABLE_CAPTION_REGEX.search(orig) or TABLE_CAPTION_REGEX.search(trans):
                    cap_blocks = [b]
                    consumed_ids.add(b.id)
                    found_tbl = None
                    extra_hdr = None

                    b_center_x = (b.bbox_norm[0] + b.bbox_norm[2]) / 2
                    b_width = b.bbox_norm[2] - b.bbox_norm[0]

                    for j in range(i + 1, min(len(raw_blocks), i + 6)):
                        cand = raw_blocks[j]
                        if cand.id in consumed_ids:
                            continue
                        c_label = (cand.label or "").lower()
                        c_orig = (cand.original_text or "").strip()
                        c_trans = (cand.translated_text or "").strip()
                        if (
                            TABLE_CAPTION_REGEX.search(c_orig)
                            or TABLE_CAPTION_REGEX.search(c_trans)
                            or FIGURE_CAPTION_REGEX.search(c_orig)
                            or FIGURE_CAPTION_REGEX.search(c_trans)
                            or c_label == "section header"
                        ):
                            break
                        c_center_x = (cand.bbox_norm[0] + cand.bbox_norm[2]) / 2
                        same_col = b_width > 0.5 or (b_center_x < 0.5 and c_center_x < 0.5) or (b_center_x >= 0.5 and c_center_x >= 0.5)
                        if not same_col:
                            continue
                        if c_label == "table":
                            found_tbl = cand
                            consumed_ids.add(cand.id)
                            break
                        if c_label == "caption" and re.search(r"(?:params|macs|psnr|ssim|lpips)", c_orig, re.I):
                            extra_hdr = cand
                            consumed_ids.add(cand.id)
                            continue
                        prev_cap = cap_blocks[-1]
                        if c_label == "caption" and (cand.bbox_norm[1] - prev_cap.bbox_norm[3] < 0.035):
                            cap_blocks.append(cand)
                            consumed_ids.add(cand.id)
                        else:
                            break

                    if found_tbl:
                        tx0 = max(0.07, min(found_tbl.bbox_norm[0], extra_hdr.bbox_norm[0] if extra_hdr else 1.0) - 0.012)
                        ty0 = max(0.05, min(found_tbl.bbox_norm[1], extra_hdr.bbox_norm[1] if extra_hdr else 1.0) - 0.008)
                        tx1 = min(0.93, max(found_tbl.bbox_norm[2], extra_hdr.bbox_norm[2] if extra_hdr else 0.0) + 0.012)
                        ty1 = min(0.95, found_tbl.bbox_norm[3] + 0.008)
                        tbl_width = tx1 - tx0
                        tbl_center_x = (tx0 + tx1) / 2
                        col_grp = "full" if tbl_width > 0.55 else ("left" if tbl_center_x < 0.5 else "right")
                        table_groups[b.id] = {
                            "caption_blocks": cap_blocks,
                            "table_block": found_tbl,
                            "crop_bbox": (tx0, ty0, tx1, ty1),
                            "anchor_y": b.bbox_norm[1],
                            "col_grp": col_grp,
                        }
                    else:
                        for cb in cap_blocks:
                            consumed_ids.discard(cb.id)

            real_table_ids: set[str] = set()
            for grp in table_groups.values():
                for cb in grp["caption_blocks"]:
                    real_table_ids.add(cb.id)
                real_table_ids.add(grp["table_block"].id)

            # 3. Nhóm hình vẽ (Figure)
            figure_groups: dict[str, dict] = {}
            fig_cap_blocks = [
                b for b in raw_blocks
                if b.id not in consumed_ids
                and (FIGURE_CAPTION_REGEX.search(b.original_text or "") or FIGURE_CAPTION_REGEX.search(b.translated_text or ""))
            ]
            fig_cap_blocks.sort(key=lambda x: x.bbox_norm[1])

            for cap_b in fig_cap_blocks:
                orig = (cap_b.original_text or "").strip()
                has_merged_prefix = not re.match(r"^\s*(?:figure|fig\.|hình)\s*\d+", orig, re.I) and bool(FIGURE_CAPTION_REGEX.search(orig))
                y_bottom = min(cap_b.bbox_norm[3], cap_b.bbox_norm[1] + 0.012) if has_merged_prefix else max(0.08, cap_b.bbox_norm[1] - 0.004)

                y_top = 0.082
                for other in raw_blocks:
                    if other.id == cap_b.id:
                        continue
                    o_label = (other.label or "").lower()
                    if o_label in ("page header", "page footer"):
                        continue
                    o_y1 = other.bbox_norm[3]
                    if o_y1 > cap_b.bbox_norm[1] - 0.015:
                        continue
                    o_orig = (other.original_text or "").strip()
                    is_prev_fig = bool(FIGURE_CAPTION_REGEX.search(o_orig))
                    is_tbl_part = other.id in real_table_ids
                    is_hdr = o_label in ("title", "section header") or (page.page_number == 1 and other.bbox_norm[1] < 0.26)
                    is_prose = o_label == "text" and len(o_orig) > 140 and not is_prev_fig
                    if is_prev_fig or is_tbl_part or is_hdr or is_prose:
                        if o_y1 + 0.008 > y_top:
                            y_top = o_y1 + 0.008

                if y_bottom - y_top >= 0.06:
                    cap_w = cap_b.bbox_norm[2] - cap_b.bbox_norm[0]
                    cap_cx = (cap_b.bbox_norm[0] + cap_b.bbox_norm[2]) / 2
                    col_grp = "full" if cap_w > 0.45 else ("left" if cap_cx < 0.5 else "right")
                    figure_groups[cap_b.id] = {
                        "caption_block": cap_b,
                        "crop_bbox": (0.085, y_top, 0.915, y_bottom),
                        "anchor_y": y_top,
                        "col_grp": col_grp,
                    }
                    consumed_ids.add(cap_b.id)
                    for inner in raw_blocks:
                        if inner.id in consumed_ids or inner.id in real_table_ids:
                            continue
                        mid_y = (inner.bbox_norm[1] + inner.bbox_norm[3]) / 2
                        if y_top - 0.01 <= mid_y <= y_bottom + 0.015:
                            consumed_ids.add(inner.id)

            # 4. Gom tất cả các khối và sắp xếp theo luồng đọc học thuật
            entries: list[dict] = []

            for fg in figure_groups.values():
                cap_b = fg["caption_block"]
                raw_cap = (cap_b.translated_text or "").strip() or (cap_b.original_text or "").strip()
                cleaned_cap = clean_figure_caption_text(raw_cap)
                col_grp = fg["col_grp"]
                if col_grp == "full":
                    col_grp = "full_top" if fg["anchor_y"] < 0.65 else "full_bottom"
                entries.append({
                    "col_grp": col_grp,
                    "sort_y": fg["anchor_y"],
                    "type": "figure",
                    "data": {
                        "caption": cleaned_cap,
                        "crop_bbox": fg["crop_bbox"],
                    },
                })

            for tg in table_groups.values():
                caps = " ".join([
                    clean_figure_caption_text((cb.translated_text or "").strip() or (cb.original_text or "").strip())
                    for cb in tg["caption_blocks"]
                    if ((cb.translated_text or "").strip() or (cb.original_text or "").strip())
                ])
                col_grp = tg["col_grp"]
                if col_grp == "full":
                    col_grp = "full_top" if tg["anchor_y"] < 0.65 else "full_bottom"
                entries.append({
                    "col_grp": col_grp,
                    "sort_y": tg["anchor_y"],
                    "type": "table",
                    "data": {
                        "caption": caps,
                        "crop_bbox": tg["crop_bbox"],
                    },
                })

            for b in raw_blocks:
                if b.id in consumed_ids:
                    continue
                label = (b.label or "").lower()
                if label in ("figure", "figure_text"):
                    continue
                orig = (b.original_text or "").strip()
                trans = (b.translated_text or "").strip()
                display_text = trans or orig
                if not display_text:
                    continue

                x0, y0, x1, y1 = b.bbox_norm
                width = x1 - x0
                cx = (x0 + x1) / 2

                is_title = label == "title" or (page.page_number == 1 and b.block_code == "BLK_0002")
                is_author = page.page_number == 1 and not is_title and y0 < 0.265
                is_sec_hdr = not is_title and not is_author and (label in ("section header", "heading"))

                variant = "body"
                if is_title:
                    variant = "title"
                elif is_author:
                    variant = "author"
                elif is_sec_hdr:
                    variant = "section_header"

                if is_title or is_author or (width > 0.55 and y0 < 0.65):
                    col_grp = "full_top"
                elif width > 0.55:
                    col_grp = "full_bottom"
                elif cx < 0.5:
                    col_grp = "left"
                else:
                    col_grp = "right"

                entries.append({
                    "col_grp": col_grp,
                    "sort_y": y0,
                    "type": "prose",
                    "data": {
                        "text": display_text,
                        "variant": variant,
                    },
                })

            priority = {"full_top": 1, "left": 2, "right": 3, "full_bottom": 4}
            entries.sort(key=lambda e: (priority.get(e["col_grp"], 2), e["sort_y"]))

            # 5. Sinh HTML cho từng phần tử của trang và để luồng văn bản tự chảy liên tục (continuous academic flow)
            for item in entries:
                itype = item["type"]
                idata = item["data"]

                if itype == "figure":
                    img_tag = ""
                    if pil_page_img:
                        fx0, fy0, fx1, fy1 = idata["crop_bbox"]
                        left = int(fx0 * pil_page_img.width)
                        top = int(fy0 * pil_page_img.height)
                        right = int(fx1 * pil_page_img.width)
                        bottom = int(fy1 * pil_page_img.height)
                        if (right - left > 20) and (bottom - top > 20):
                            img_counter += 1
                            img_name = f"fig_{img_counter}.png"
                            cropped = pil_page_img.crop((left, top, right, bottom))
                            buf = io.BytesIO()
                            cropped.save(buf, format="PNG")
                            archive.add(buf.getvalue(), img_name)
                            img_tag = f'<div class="figure-box"><img src="{img_name}" class="figure-img" /></div>'
                    cap_html = f'<p class="figure-caption"><em>{format_latex_to_html(idata["caption"])}</em></p>' if idata["caption"] else ""
                    body_elements.append(f'<div class="figure-card">{img_tag}{cap_html}</div>')

                elif itype == "table":
                    img_tag = ""
                    if pil_page_img:
                        tx0, ty0, tx1, ty1 = idata["crop_bbox"]
                        left = int(tx0 * pil_page_img.width)
                        top = int(ty0 * pil_page_img.height)
                        right = int(tx1 * pil_page_img.width)
                        bottom = int(ty1 * pil_page_img.height)
                        if (right - left > 20) and (bottom - top > 20):
                            img_counter += 1
                            img_name = f"tbl_{img_counter}.png"
                            cropped = pil_page_img.crop((left, top, right, bottom))
                            buf = io.BytesIO()
                            cropped.save(buf, format="PNG")
                            archive.add(buf.getvalue(), img_name)
                            img_tag = f'<div class="table-box"><img src="{img_name}" class="table-img" /></div>'
                    cap_html = f'<p class="table-caption"><strong>{format_latex_to_html(idata["caption"])}</strong></p>' if idata["caption"] else ""
                    body_elements.append(f'<div class="table-card">{cap_html}{img_tag}</div>')

                elif itype == "prose":
                    text = idata["text"]
                    var = idata["variant"]
                    formatted = format_latex_to_html(text)
                    if var == "title":
                        body_elements.append(f'<h1 class="paper-title">{formatted}</h1>')
                    elif var == "author":
                        body_elements.append(f'<p class="author-meta">{formatted}</p>')
                    elif var == "section_header":
                        body_elements.append(f'<h2 class="section-heading">{formatted}</h2>')
                    else:
                        body_elements.append(f'<p class="body-paragraph">{formatted}</p>')

        css = """
        body {
            font-family: sans-serif;
            font-size: 10pt;
            line-height: 1.55;
            color: #1e293b;
            margin: 0;
            padding: 0;
        }
        .paper-title {
            font-size: 16pt;
            font-weight: bold;
            color: #0f172a;
            text-align: center;
            margin: 0 0 10px 0;
            line-height: 1.3;
        }
        .author-meta {
            text-align: center;
            font-size: 9pt;
            color: #475569;
            margin-bottom: 14px;
            line-height: 1.4;
        }
        .section-heading {
            font-size: 12pt;
            font-weight: bold;
            color: #1e3a8a;
            margin-top: 14px;
            margin-bottom: 6px;
            border-bottom: 0.5px solid #cbd5e1;
            padding-bottom: 2px;
        }
        .body-paragraph {
            text-align: justify;
            margin: 0 0 8px 0;
            text-indent: 1.2em;
        }
        .figure-card, .table-card {
            break-inside: avoid;
            page-break-inside: avoid;
            margin: 14px 0;
            text-align: center;
        }
        .figure-box, .table-box {
            text-align: center;
            margin: 0 0 4px 0;
        }
        .figure-img, .table-img {
            max-width: 100%;
            height: auto;
        }
        .figure-caption, .table-caption {
            text-align: center;
            font-size: 8.5pt;
            color: #475569;
            margin: 4px 0 0 0;
            line-height: 1.4;
        }
        .math-formula {
            font-family: "Times New Roman", Times, serif;
            font-size: 10.5pt;
        }
        """

        full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
  {"".join(body_elements)}
</body>
</html>"""
        return full_html

    def generate_html_document(
        self,
        session: PaperSessionModel,
        segments: list[PaperSegmentModel],
        math_tokens: list[MathTokenModel],
    ) -> str:
        """Tạo mã nguồn HTML hoàn chỉnh chứa đầy đủ tiêu đề, các đoạn dịch, bảng và công thức."""
        token_map: dict[str, str] = {t.token_placeholder: t.raw_latex for t in math_tokens}
        paper_title = html.escape(session.title or session.file_name or "Bài báo khoa học")

        body_elements = []

        for seg in segments:
            raw_text = seg.translated_content or seg.original_content or ""
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
                    local_img_path = seg.media_path
                    if local_img_path.startswith("/api/v1/assets/"):
                        rel_path = local_img_path.replace("/api/v1/assets/", "")
                        abs_img_file = settings.STORAGE_DIR / "assets" / rel_path
                        if abs_img_file.exists():
                            local_img_path = abs_img_file.as_uri()
                    fig_html = f'<div class="figure-container"><img src="{local_img_path}" class="figure-img" /></div>'
                caption = f'<p class="figure-caption"><em>{html.escape(restored_text)}</em></p>' if restored_text else ""
                body_elements.append(f"{fig_html}{caption}")
            else:
                escaped_p = html.escape(restored_text)
                formatted_p = escaped_p.replace("\n", "<br/>")
                body_elements.append(f'<p class="body-paragraph">{formatted_p}</p>')

        body_html = "\n".join(body_elements)

        full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>{paper_title}</title>
<style>
  body {{
    font-family: sans-serif;
    font-size: 10pt;
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
    font-size: 17pt;
    font-weight: bold;
    color: #0f172a;
    line-height: 1.3;
    margin: 0 0 10px 0;
  }}
  .section-heading {{
    font-size: 12.5pt;
    font-weight: bold;
    color: #1e3a8a;
    margin-top: 20px;
    margin-bottom: 8px;
    border-bottom: 0.5px solid #e2e8f0;
    padding-bottom: 4px;
  }}
  .body-paragraph {{
    text-align: justify;
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
    font-family: monospace;
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
  {body_html}
</body>
</html>"""
        return full_html
        return full_html

    def _export_via_story(
        self,
        html_content: str,
        output_path: Path,
        archive: pymupdf.Archive | None = None,
    ) -> Path:
        """Biên dịch tài liệu HTML chuẩn xác sang PDF đa trang qua PyMuPDF Story Engine."""
        import gc

        temp_path = output_path.with_suffix(".story_raw.pdf")
        story = pymupdf.Story(html=html_content, archive=archive)
        writer = pymupdf.DocumentWriter(str(temp_path))

        page_w, page_h = 595.0, 842.0  # A4 standard points
        margin_x, margin_y = 42.0, 48.0
        rect = pymupdf.Rect(margin_x, margin_y, page_w - margin_x, page_h - margin_y)
        mediabox = pymupdf.Rect(0, 0, page_w, page_h)

        more = 1
        while more:
            dev = writer.begin_page(mediabox)
            more, filled = story.place(rect)
            story.draw(dev)
            writer.end_page()
        writer.close()
        del writer
        gc.collect()

        # Thêm số trang chân trang chuẩn học thuật
        doc = pymupdf.open(str(temp_path))
        total_pages = len(doc)
        helv_font = pymupdf.Font("helv")
        for page_idx in range(total_pages):
            p = doc[page_idx]
            footer_text = f"Trang {page_idx + 1} / {total_pages}"
            text_width = helv_font.text_length(footer_text, fontsize=8)
            centered_x = (page_w - text_width) / 2
            p.insert_text(
                (centered_x, page_h - 25),
                footer_text,
                fontsize=8,
                color=(0.45, 0.5, 0.55),
                fontname="helv",
            )
        pdf_bytes = doc.tobytes()
        doc.close()
        del doc
        gc.collect()

        temp_path.unlink(missing_ok=True)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def export_pdf(
        self,
        session: PaperSessionModel,
        canvas_data: CanvasDataResponse | list[PaperSegmentModel] | None = None,
        segments: list[PaperSegmentModel] | list[MathTokenModel] | None = None,
        math_tokens: list[MathTokenModel] | None = None,
    ) -> Path:
        """
        Xuất tài liệu sang tệp PDF.
        Ưu tiên hàng đầu: Bố cục Canvas Layout (Flowing Single-Column) với đầy đủ hình ảnh, bảng biểu và bản dịch tiếng Việt.
        Fallback tương thích: Segments truyền thống cho tài liệu DOCX hoặc kiểm thử cũ.
        """
        # Hỗ trợ tương thích ngược khi gọi positional: export_pdf(session, segments, math_tokens)
        if isinstance(canvas_data, list):
            math_tokens = segments if isinstance(segments, list) else []
            segments = canvas_data
            canvas_data = None

        output_filename = f"{session.id}_translated.pdf"
        output_path = self.export_dir / output_filename
        archive = pymupdf.Archive()

        # 1. Trường hợp có dữ liệu Canvas (PDF tài liệu bài báo đã bóc tách OCR)
        if isinstance(canvas_data, CanvasDataResponse) and canvas_data.pages:
            logger.info(f"[{session.id}] Đang xuất PDF chất lượng cao từ bố cục Canvas ({len(canvas_data.pages)} trang)...")
            html_content = self.generate_canvas_html(session, canvas_data, archive)
            try:
                self._export_via_story(html_content, output_path, archive=archive)
                logger.info(f"[{session.id}] Xuất PDF Canvas qua PyMuPDF Story Engine thành công: {output_path}")
                return output_path
            except Exception as story_err:
                logger.warning(f"[{session.id}] Lỗi PyMuPDF Story Engine ({story_err}), thử nghiệm qua WeasyPrint/PyMuPDF fallback.")

        # 2. Trường hợp fallback qua segments (DOCX hoặc legacy segments)
        seg_list = segments if isinstance(segments, list) else []
        tok_list = math_tokens if isinstance(math_tokens, list) else []
        html_content = self.generate_html_document(session, seg_list, tok_list)

        try:
            self._export_via_story(html_content, output_path)
            logger.info(f"[{session.id}] Xuất PDF Segments qua PyMuPDF Story Engine thành công: {output_path}")
            return output_path
        except Exception as story_err:
            logger.warning(f"[{session.id}] Story Engine gặp lỗi ({story_err}). Thử fallback WeasyPrint...")

        # 3. Thử nghiệm WeasyPrint
        try:
            import weasyprint
            weasyprint.HTML(string=html_content).write_pdf(str(output_path))
            logger.info(f"[{session.id}] Xuất PDF qua WeasyPrint thành công: {output_path}")
            return output_path
        except (ImportError, OSError, Exception) as weasy_err:
            logger.warning(f"[{session.id}] WeasyPrint không khả dụng ({weasy_err}). Chuyển sang fallback cơ bản.")

        return self._export_via_pymupdf(session, seg_list, tok_list, output_path)

    def _export_via_pymupdf(
        self,
        session: PaperSessionModel,
        segments: list[PaperSegmentModel],
        math_tokens: list[MathTokenModel],
        output_path: Path,
    ) -> Path:
        """Sinh tệp PDF cơ bản nếu các engine hiện đại đều không khả dụng."""
        token_map = {t.token_placeholder: t.raw_latex for t in math_tokens}
        doc = pymupdf.open()

        page_width, page_height = 595.0, 842.0
        margin_x, margin_top, margin_bottom = 50.0, 60.0, 60.0
        content_width = page_width - (margin_x * 2)

        def add_new_page(doc_obj) -> pymupdf.Page:
            p = doc_obj.new_page(width=page_width, height=page_height)
            p.insert_text(
                (margin_x, 35),
                "Paper Translation — Bản dịch Tiếng Việt",
                fontsize=8,
                color=(0.4, 0.45, 0.5),
            )
            return p

        current_page = add_new_page(doc)
        current_y = margin_top

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
            fontname = "helv"
            color = (0.1, 0.1, 0.1)

            if seg.segment_type in ("TITLE", "HEADING"):
                fontsize = 13
                color = (0.1, 0.2, 0.55)
                current_y += 10
            elif seg.segment_type == "MATH_DISPLAY":
                fontsize = 9.5
                color = (0.2, 0.2, 0.2)
                text = f"[Công thức]: {text}"

            estimated_lines = max(1, len(text) // 80 + text.count("\n") + 1)
            estimated_height = estimated_lines * (fontsize * 1.5)

            if current_y + estimated_height > page_height - margin_bottom:
                current_page = add_new_page(doc)
                current_y = margin_top

            rect = pymupdf.Rect(margin_x, current_y, margin_x + content_width, current_y + estimated_height + 20)
            rendered_height = current_page.insert_textbox(
                rect, text, fontsize=fontsize, fontname=fontname, color=color
            )
            if rendered_height < 0:
                current_page = add_new_page(doc)
                current_y = margin_top
                rect = pymupdf.Rect(margin_x, current_y, margin_x + content_width, page_height - margin_bottom)
                current_page.insert_textbox(rect, text, fontsize=fontsize, fontname=fontname, color=color)
                current_y += estimated_height + 8
            else:
                current_y += max(rendered_height, estimated_height) + 8

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
