#!/usr/bin/env python3
"""
Bước 3: Ghép nối các batch đã dịch và kết xuất file HTML Canvas A4 hoàn chỉnh.
- Đọc tất cả các file translated_batch_01.md, translated_batch_02.md,...
- Khôi phục các công thức LaTeX gốc từ token <<<MATH_TOKEN_XXXX>>>.
- Nhúng hình ảnh (hỗ trợ base64 tự chứa) và định dạng bảng biểu học thuật.
- Render vào template canvas_a4.html và lưu thành translated_paper.html.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re
import sys

# Đảm bảo UTF-8 cho Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from jinja2 import Environment, FileSystemLoader

try:
    from math_isolator import LaTeXIsolator
except ImportError:
    from scripts.math_isolator import LaTeXIsolator


def image_to_base64(img_path: Path) -> str:
    """Chuyển đổi hình ảnh sang base64 data URI để file HTML hoàn toàn độc lập."""
    suffix = img_path.suffix.lower().replace(".", "")
    if suffix == "jpg":
        suffix = "jpeg"
    with open(img_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{suffix};base64,{encoded}"


def markdown_to_html(md_text: str, output_dir: Path) -> str:
    """
    Bộ phân tích Markdown gọn nhẹ phục vụ văn bản học thuật:
    - Tiêu đề h1, h2, h3, h4.
    - Định dạng in đậm, in nghiêng, trích dẫn.
    - Danh sách có thứ tự và không thứ tự.
    - Bảng biểu chuẩn học thuật (Booktabs style).
    - Hình ảnh và caption căn giữa.
    """
    lines = md_text.splitlines()
    html_lines = []
    in_list = False
    list_type = "ul"
    in_table = False
    table_rows = []
    rendered_figure_nums = set()

    def flush_table():
        nonlocal in_table, table_rows
        if not in_table or not table_rows:
            return ""
        table_html = ['<div class="paper-table-wrapper"><table>']
        header_done = False
        for r_idx, row in enumerate(table_rows):
            # Bỏ qua dòng phân cách Markdown |---|---|
            if re.match(r"^\|?\s*[-:]+[-|\s:]*\|?$", row.strip()):
                continue
            cols = [c.strip() for c in row.strip().strip("|").split("|")]
            if not header_done:
                table_html.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr></thead><tbody>")
                header_done = True
            else:
                table_html.append("<tr>" + "".join(f"<td>{c}</td>" for c in cols) + "</tr>")
        if header_done:
            table_html.append("</tbody>")
        table_html.append("</table></div>")
        in_table = False
        table_rows = []
        return "\n".join(table_html)

    for line in lines:
        stripped = line.strip()

        # Kiểm tra bảng biểu (| ... |)
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_rows.append(stripped)
            continue
        elif in_table:
            html_lines.append(flush_table())

        if not stripped:
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
            html_lines.append("")
            continue

        # 1. Hình ảnh Markdown ![caption](path)
        img_match = re.search(r"!\[(.*?)\]\((.*?)\)", stripped)
        if img_match:
            caption = img_match.group(1).strip()
            img_rel = img_match.group(2).strip()
            img_full_path = output_dir / img_rel
            if not img_full_path.is_file():
                # Thử tìm trực tiếp trong figures/
                img_full_path = output_dir / "figures" / Path(img_rel).name

            if img_full_path.is_file():
                img_src = image_to_base64(img_full_path)
            else:
                img_src = img_rel

            # Đánh dấu số figure đã render
            fig_num_match = re.search(r"(?:figure|fig|hình)\s*_?(\d+)", img_rel, re.IGNORECASE) or re.search(r"(?:Figure|Fig\.|Hình)\s*(\d+)", caption, re.IGNORECASE)
            if fig_num_match:
                rendered_figure_nums.add(int(fig_num_match.group(1)))

            caption_html = f'<div class="figure-caption">{caption}</div>' if caption else ""
            html_lines.append(
                f'<div class="paper-figure"><img src="{img_src}" alt="{caption}"/>{caption_html}</div>'
            )
            continue

        # 2. Tự động chèn hình ảnh khi gặp Caption bài báo (Hình X. / Figure X.)
        cap_match = re.match(r"^(?:\*\*)?(?:Hình|Figure|Fig\.)\s*(\d+)[\.:]?(.*)$", stripped, re.IGNORECASE)
        if cap_match:
            fig_num = int(cap_match.group(1))
            if fig_num not in rendered_figure_nums:
                candidate_filenames = [
                    f"figure_{fig_num:02d}.png",
                    f"figure_{fig_num:02d}.jpg",
                    f"figure_{fig_num:02d}.jpeg",
                    f"figure_{fig_num}.png",
                    f"figure_{fig_num}.jpg",
                ]
                fig_found = None
                for c_name in candidate_filenames:
                    p = output_dir / "figures" / c_name
                    if p.is_file():
                        fig_found = p
                        break

                if fig_found:
                    img_src = image_to_base64(fig_found)
                    rendered_figure_nums.add(fig_num)
                    caption_html = f'<div class="figure-caption">{inline_formatting(stripped)}</div>'
                    html_lines.append(
                        f'<div class="paper-figure"><img src="{img_src}" alt="Hình {fig_num}"/>{caption_html}</div>'
                    )
                    continue

        # Tiêu đề
        if stripped.startswith("#### "):
            html_lines.append(f"<h4>{inline_formatting(stripped[5:])}</h4>")
            continue
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{inline_formatting(stripped[4:])}</h3>")
            continue
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{inline_formatting(stripped[3:])}</h2>")
            continue
        elif stripped.startswith("# "):
            html_lines.append(f"<h1>{inline_formatting(stripped[2:])}</h1>")
            continue

        # Danh sách
        ul_match = re.match(r"^[-*+]\s+(.*)$", stripped)
        if ul_match:
            if not in_list or list_type != "ul":
                if in_list:
                    html_lines.append(f"</{list_type}>")
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            html_lines.append(f"<li>{inline_formatting(ul_match.group(1))}</li>")
            continue

        ol_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ol_match:
            if not in_list or list_type != "ol":
                if in_list:
                    html_lines.append(f"</{list_type}>")
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            html_lines.append(f"<li>{inline_formatting(ol_match.group(1))}</li>")
            continue

        if in_list:
            html_lines.append(f"</{list_type}>")
            in_list = False

        # Đoạn văn thông thường
        html_lines.append(f"<p>{inline_formatting(stripped)}</p>")

    if in_table:
        html_lines.append(flush_table())
    if in_list:
        html_lines.append(f"</{list_type}>")

    return "\n".join(html_lines)


def inline_formatting(text: str) -> str:
    """Xử lý định dạng in đậm, in nghiêng, code inline."""
    # Bold **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    # Italic *text*
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    # Inline code `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def main():
    parser = argparse.ArgumentParser(description="Compile Translated Paper Batches into A4 HTML Canvas")
    parser.add_argument("--output-dir", required=True, help="Thư mục chứa metadata.json và các batch dịch")
    parser.add_argument("--title", default=None, help="Tiêu đề bài báo hiển thị (tùy chọn)")

    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    metadata_path = output_dir / "metadata.json"

    if not metadata_path.is_file():
        print(f"Lỗi: Không tìm thấy file metadata.json trong {output_dir}", file=sys.stderr)
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    title = args.title or metadata.get("title") or "Bản dịch bài báo khoa học"
    batches_meta = metadata.get("batches", [])
    math_tokens = metadata.get("math_tokens", [])
    figures = metadata.get("figures", [])

    print(f"[BƯỚC 3] Đang tiến hành ghép nối {len(batches_meta)} batch bài báo: '{title}'...")

    batches_dir = output_dir / "batches"
    combined_md_parts = []

    for b in batches_meta:
        b_idx = b["index"]
        trans_file = batches_dir / f"translated_batch_{b_idx:02d}.md"
        raw_file = batches_dir / f"batch_{b_idx:02d}.txt"

        if trans_file.is_file():
            print(f"  -> Đang nạp: {trans_file.name}")
            with open(trans_file, "r", encoding="utf-8") as f:
                combined_md_parts.append(f.read())
        elif raw_file.is_file():
            print(f"  [CẢNH BÁO] Chưa dịch batch {b_idx:02d}. Sử dụng tạm văn bản gốc {raw_file.name}...")
            with open(raw_file, "r", encoding="utf-8") as f:
                combined_md_parts.append(f.read())
        else:
            print(f"  [LỖI] Không tìm thấy file batch {b_idx:02d} trong {batches_dir}", file=sys.stderr)

    full_markdown = "\n\n".join(combined_md_parts)

    # 1. Khôi phục các công thức LaTeX gốc
    print(f"[Công thức Toán] Đang khôi phục {len(math_tokens)} công thức toán học...")
    full_markdown = LaTeXIsolator.reinject_formulas(full_markdown, math_tokens)

    # 2. Chuyển Markdown sang HTML
    print("[HTML Canvas] Đang chuyển đổi nội dung Markdown sang cấu trúc HTML học thuật...")
    content_html = markdown_to_html(full_markdown, output_dir)

    # 3. Nạp Template Jinja2
    skill_root = Path(__file__).resolve().parent.parent
    templates_dir = skill_root / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    template = env.get_template("canvas_a4.html")

    rendered_html = template.render(
        title=title,
        content_html=content_html,
        total_pages=metadata.get("total_pages", 1),
    )

    # 4. Ghi file kết quả cuối cùng
    out_html_path = output_dir / "translated_paper.html"
    with open(out_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"\n[BƯỚC 3 HOÀN TẤT] File HTML Canvas A4 đã được tạo thành công tại:")
    print(f"  -> {out_html_path}")
    print("Người dùng có thể mở tệp này trên bất kỳ trình duyệt nào và bấm 'Tải PDF (In A4)' để xuất bản!")


if __name__ == "__main__":
    main()
