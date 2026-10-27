#!/usr/bin/env python3
"""
Bước 1: OCR và phân lô văn bản bài báo (Adaptive Batching).
- Phân tích bố cục tài liệu PDF bằng Indra OCR (mô hình cục bộ trong ../models).
- Trích xuất và lưu hình ảnh vào output/figures/.
- Cách ly các công thức LaTeX thành mã đại diện <<<MATH_TOKEN_XXXX>>>.
- Gom cụm văn bản thành các batch độc lập không vượt quá 2000 - 2500 từ tiếng Anh.
- Ghi các file batch_01.txt, batch_02.txt,... và metadata.json.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
from pathlib import Path
import re
import sys

# Đảm bảo UTF-8 cho Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz
from PIL import Image

# Import LaTeXIsolator cục bộ
try:
    from math_isolator import LaTeXIsolator
except ImportError:
    from scripts.math_isolator import LaTeXIsolator


JUNK_WATERMARK_REGEX = re.compile(
    r"(?i)(?:^arxiv:\d{4}\.\d+.*"
    r"|.*ieee\s+transactions.*"
    r"|.*cvpr.*"
    r"|.*iccv.*"
    r"|.*neurips.*"
    r"|.*icml.*"
    r"|.*conference\s+on\s+computer\s+vision.*"
    r"|.*authorized\s+licensed\s+use\s+limited\s+to:.*"
    r"|.*downloaded\s+on\s+.*utc\s+from\s+ieee.*"
    r"|.*copyright\s+©.*"
    r"|.*all\s+rights\s+reserved.*"
    r"|^\d+\s*$)",
    re.DOTALL,
)


def count_words(text: str) -> int:
    """Đếm số từ tiếng Anh trong đoạn văn."""
    if not text:
        return 0
    return len(text.split())


def extract_academic_figures(
    doc_fitz: fitz.Document,
    output_figures_dir: Path,
) -> tuple[dict[int, dict], list[dict]]:
    """
    Trích xuất hình ảnh, sơ đồ khoa học (Academic Figures) chất lượng cao từ trang PDF.
    - Định vị các caption Figure X / Fig X.
    - Xác định vùng bounding box an toàn bao hàm toàn bộ sơ đồ/hình ảnh từ mốc trước đến sát trên caption.
    - Render ở độ phân giải cao (200 DPI) và autocrop loại bỏ lề trắng thừa, bảo toàn 100% chi tiết hình vẽ.
    """
    from PIL import ImageChops
    output_figures_dir.mkdir(parents=True, exist_ok=True)
    all_figures = []
    fig_map = {}

    fig_list = []
    for p_idx, page in enumerate(doc_fitz):
        blocks = page.get_text("blocks")
        for b in blocks:
            text = b[4].strip()
            m = re.match(r"^(Figure\s+(\d+)[\.:].*?)$", text, re.DOTALL | re.IGNORECASE)
            if m:
                fig_list.append({
                    "num": int(m.group(2)),
                    "page": p_idx,
                    "rect": fitz.Rect(b[:4]),
                    "caption": text,
                })

    fig_list.sort(key=lambda x: (x["page"], x["rect"].y0))

    for f in fig_list:
        p_idx = f["page"]
        page = doc_fitz[p_idx]
        cap = f["rect"]
        num = f["num"]

        is_full = (cap.x0 < 160 and cap.x1 > 400) or cap.width > 300
        if is_full:
            x_min, x_max = 40.0, page.rect.width - 40.0
        elif cap.x0 < page.rect.width * 0.45:
            x_min, x_max = 40.0, page.rect.width * 0.50
        else:
            x_min, x_max = page.rect.width * 0.50, page.rect.width - 40.0

        y_min = 45.0
        for other in fig_list:
            if other["page"] == p_idx and other["rect"].y1 < cap.y0:
                if other["rect"].y1 > y_min:
                    y_min = other["rect"].y1 + 4.0

        crop_rect = fitz.Rect(x_min, y_min, x_max, cap.y0 - 2.0)
        pix = page.get_pixmap(clip=crop_rect, dpi=200)
        im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        bg = Image.new(im.mode, im.size, (255, 255, 255))
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
        if bbox:
            w, h = im.size
            m = 10
            box = (max(0, bbox[0] - m), max(0, bbox[1] - m), min(w, bbox[2] + m), min(h, bbox[3] + m))
            cropped = im.crop(box)
        else:
            cropped = im

        fig_filename = f"figure_{num:02d}.png"
        fig_path = output_figures_dir / fig_filename
        cropped.save(str(fig_path))

        fig_data = {
            "num": num,
            "page": p_idx + 1,
            "filename": fig_filename,
            "rel_path": f"figures/{fig_filename}",
            "width": cropped.width,
            "height": cropped.height,
            "caption": f["caption"],
        }
        fig_map[num] = fig_data
        all_figures.append(fig_data)

    return fig_map, all_figures


def extract_figures_from_page(
    doc_fitz: fitz.Document,
    page_num: int,
    output_figures_dir: Path,
) -> list[dict[str, str]]:
    """Trích xuất ảnh nhúng bổ sung từ trang PDF."""
    extracted = []
    if page_num > len(doc_fitz):
        return extracted

    page = doc_fitz[page_num - 1]
    image_list = page.get_images(full=True)

    for img_idx, img_info in enumerate(image_list, start=1):
        xref = img_info[0]
        base_image = doc_fitz.extract_image(xref)
        image_bytes = base_image.get("image")
        image_ext = base_image.get("ext", "png")
        width = base_image.get("width", 0)
        height = base_image.get("height", 0)

        # Chỉ lưu các ảnh nhúng lớn có ý nghĩa
        if width < 150 or height < 150:
            continue

        fig_filename = f"image_p{page_num:02d}_{img_idx:02d}.{image_ext}"
        fig_path = output_figures_dir / fig_filename
        if not fig_path.exists():
            with open(fig_path, "wb") as f:
                f.write(image_bytes)

        rel_path = f"figures/{fig_filename}"
        extracted.append({
            "page": page_num,
            "filename": fig_filename,
            "rel_path": rel_path,
            "width": width,
            "height": height,
        })

    return extracted


def run_ocr(pdf_path: Path, models_dir: Path) -> tuple[str, list[dict[str, any]]]:
    """
    Thực thi Indra OCR để nhận diện chữ và công thức.
    Nếu Indra OCR không khả dụng, tự động fallback sang PyMuPDF layout extraction.
    """
    blocks = []
    paper_title = pdf_path.stem

    try:
        import indra_ocr

        print(f"[OCR] Nạp Indra OCR từ thư mục: {models_dir}...")
        model_arg = str(models_dir) if (models_dir / "det.onnx").exists() else None
        try:
            converter = indra_ocr.load(path=model_arg, threads=4, math=True, mode="auto")
            print("[OCR] Kích hoạt thành công Indra OCR chế độ Math LaTeX.")
        except Exception as e_math:
            print(f"[OCR] Cảnh báo math module ({e_math}), chuyển sang Indra OCR standard mode.")
            converter = indra_ocr.load(path=model_arg, threads=4, math=False, mode="auto")

        doc_fitz = fitz.open(str(pdf_path))
        for item in converter.convert(str(pdf_path)):
            if isinstance(item, tuple) and len(item) == 2:
                page_idx, indra_page = item
            else:
                indra_page = item
                page_idx = getattr(indra_page, "page_idx", 0)

            page_num = page_idx + 1
            raw_blocks = getattr(indra_page, "blocks", [])
            if not raw_blocks and hasattr(indra_page, "lines"):
                raw_blocks = [
                    {"label": "Text", "bbox": ln.box, "text": ln.text}
                    for ln in indra_page.lines
                    if ln.text.strip()
                ]

            for b in raw_blocks:
                text = (b.get("text") or "").strip()
                label = (b.get("label") or "Text").lower()

                if not text or JUNK_WATERMARK_REGEX.match(text):
                    continue

                if "header" in label or "footer" in label:
                    continue

                if not paper_title or paper_title == pdf_path.stem:
                    if "title" in label or (page_num == 1 and len(text) > 10 and "\n" not in text):
                        paper_title = text

                blocks.append({
                    "page": page_num,
                    "label": label,
                    "text": text,
                })
        doc_fitz.close()

    except Exception as e:
        print(f"[OCR] Không thể chạy Indra OCR ({e}). Kích hoạt fallback PyMuPDF layout.")
        doc = fitz.open(str(pdf_path))
        for page_num in range(1, len(doc) + 1):
            page = doc[page_num - 1]
            page_blocks = page.get_text("blocks")
            for b in page_blocks:
                text = b[4].strip()
                if not text or JUNK_WATERMARK_REGEX.match(text):
                    continue
                blocks.append({
                    "page": page_num,
                    "label": "text",
                    "text": text,
                })
        doc.close()

    return paper_title, blocks


def split_into_batches(
    blocks: list[dict[str, any]],
    max_words_per_batch: int = 2200,
) -> list[str]:
    """
    Gom nhóm các khối văn bản thành các batch với trần cứng không quá max_words_per_batch từ.
    """
    batches = []
    current_batch_blocks = []
    current_word_count = 0

    for b in blocks:
        text = b["text"]
        w_count = count_words(text)

        # Nếu một khối quá dài (> max_words_per_batch), ngắt thành các đoạn nhỏ
        if w_count > max_words_per_batch:
            paragraphs = text.split("\n\n")
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                pw = count_words(p)
                if current_word_count + pw > max_words_per_batch and current_batch_blocks:
                    batches.append("\n\n".join(current_batch_blocks))
                    current_batch_blocks = []
                    current_word_count = 0
                current_batch_blocks.append(p)
                current_word_count += pw
            continue

        if current_word_count + w_count > max_words_per_batch and current_batch_blocks:
            batches.append("\n\n".join(current_batch_blocks))
            current_batch_blocks = []
            current_word_count = 0

        current_batch_blocks.append(text)
        current_word_count += w_count

    if current_batch_blocks:
        batches.append("\n\n".join(current_batch_blocks))

    return batches


def main():
    parser = argparse.ArgumentParser(description="Indra OCR & Batching Pipeline for Paper Translation")
    parser.add_argument("--pdf", required=True, help="Đường dẫn tới tệp PDF bài báo")
    parser.add_argument("--output-dir", default=None, help="Thư mục xuất kết quả (mặc định output/<pdf-name>)")
    parser.add_argument("--max-words", type=int, default=2200, help="Số từ tối đa trong mỗi batch (mặc định 2200)")

    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        print(f"Lỗi: Không tìm thấy tệp PDF tại {pdf_path}", file=sys.stderr)
        sys.exit(1)

    skill_root = Path(__file__).resolve().parent.parent
    models_dir = skill_root / "models"

    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = pdf_path.parent / "output" / pdf_path.stem

    figures_dir = output_dir / "figures"
    batches_dir = output_dir / "batches"
    figures_dir.mkdir(parents=True, exist_ok=True)
    batches_dir.mkdir(parents=True, exist_ok=True)

    print(f"[BƯỚC 1] Bắt đầu OCR & Phân tích bài báo: {pdf_path.name}")
    print(f"[BƯỚC 1] Thư mục xuất dữ liệu: {output_dir}")

    # 1. Trích xuất hình ảnh sơ đồ khoa học (Academic Figures)
    print("[Hình ảnh] Đang trích xuất sơ đồ khoa học và hình ảnh từ các trang PDF...")
    doc_fitz = fitz.open(str(pdf_path))
    total_pages = len(doc_fitz)
    fig_map, all_figures = extract_academic_figures(doc_fitz, figures_dir)
    print(f"[Hình ảnh] Đã trích xuất thành công {len(all_figures)} sơ đồ khoa học chuẩn A4 vào {figures_dir.name}/")

    # Trích xuất thêm ảnh nhúng bổ sung nếu có
    extra_imgs = []
    for p in range(1, total_pages + 1):
        figs = extract_figures_from_page(doc_fitz, p, figures_dir)
        extra_imgs.extend(figs)
    all_figures.extend(extra_imgs)
    doc_fitz.close()

    # 2. Chạy OCR
    paper_title, blocks = run_ocr(pdf_path, models_dir)
    print(f"[OCR] Đã trích xuất {len(blocks)} khối nội dung. Tiêu đề nhận diện: '{paper_title}'")

    # Gắn thẻ hình ảnh Markdown vào các khối caption
    for b in blocks:
        t = b.get("text", "")
        m = re.search(r"\b(Figure|Fig\.)\s*(\d+)[\.:]", t, re.IGNORECASE)
        if m:
            f_num = int(m.group(2))
            if f_num in fig_map:
                f_info = fig_map[f_num]
                img_md = f"![{f_info['caption']}](figures/{f_info['filename']})\n\n"
                if img_md not in t and f_info['filename'] not in t:
                    b["text"] = f"{img_md}{t}"

    # 3. Phân lô Adaptive Batching
    raw_batches = split_into_batches(blocks, max_words_per_batch=args.max_words)
    print(f"[Batching] Phân chia thành công {len(raw_batches)} batch (ngưỡng tối đa {args.max_words} từ/batch).")

    # 4. Cách ly công thức LaTeX trên từng batch
    all_math_tokens = []
    batch_metadata = []
    current_token_idx = 1

    for idx, batch_text in enumerate(raw_batches, start=1):
        masked_text, tokens = LaTeXIsolator.isolate_formulas(batch_text, start_index=current_token_idx)
        current_token_idx += len(tokens)
        all_math_tokens.extend(tokens)

        batch_filename = f"batch_{idx:02d}.txt"
        batch_file_path = batches_dir / batch_filename

        with open(batch_file_path, "w", encoding="utf-8") as f:
            f.write(masked_text)

        w_count = count_words(masked_text)
        batch_metadata.append({
            "index": idx,
            "filename": batch_filename,
            "words": w_count,
            "tokens_count": len(tokens),
        })
        print(f"  -> Đã tạo {batch_filename} ({w_count} từ, {len(tokens)} công thức toán)")

    # 5. Lưu metadata.json
    metadata = {
        "pdf_filename": pdf_path.name,
        "title": paper_title,
        "total_pages": total_pages,
        "total_batches": len(raw_batches),
        "figures": all_figures,
        "batches": batch_metadata,
        "math_tokens": all_math_tokens,
    }
    with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"[BƯỚC 1 HOÀN TẤT] Dữ liệu đã sẵn sàng trong: {output_dir}")
    print("Agent hãy tiến hành đọc từng file trong thư mục batches/ và dịch tuần tự sang tiếng Việt!")


if __name__ == "__main__":
    main()
