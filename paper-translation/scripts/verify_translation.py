#!/usr/bin/env python3
"""
verify_translation.py
---------------------
Công cụ xác minh và kiểm tra chéo tính toàn vẹn của bản dịch bài báo khoa học.
Hỗ trợ kiểm tra:
1. Tính nhất quán của Tiêu đề bài báo & Tác giả trong metadata.json.
2. Kiểm tra tính toàn vẹn của tất cả công thức toán học LaTeX (so khớp token <<<MATH_TOKEN_XXXX>>>).
3. Kiểm tra tính hợp lệ và cấu trúc của bảng biểu Markdown (phát hiện lệch cột do OCR bỏ sót dấu '-', ô trống).
4. Phát hiện rác OCR phổ biến (nhãn text từ sơ đồ khối, số phương trình trôi dạt vào văn bản).
5. Kiểm tra danh mục hình ảnh Figures và Tài liệu tham khảo (References).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

# Đảm bảo UTF-8 cho Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def check_metadata(metadata: dict[str, Any]) -> list[str]:
    """Kiểm tra metadata.json về tiêu đề và cấu trúc."""
    warnings = []
    title = metadata.get("title", "").strip()
    if not title:
        warnings.append("[Tiêu đề] Thiếu tiêu đề trong metadata.json.")
    elif re.search(r"\b\d+†\b", title) or "," in title and len(title.split(",")) > 2:
        warnings.append(
            f"[Tiêu đề] Cảnh báo: Tiêu đề hiện tại ('{title[:50]}...') có dấu hiệu là danh sách tác giả do OCR trích xuất nhầm. Cần kiểm tra lại PDF gốc!"
        )

    tokens = metadata.get("math_tokens", [])
    if not tokens:
        warnings.append("[Toán học] Không tìm thấy danh sách 'math_tokens' trong metadata.json.")

    figures = metadata.get("figures", [])
    if not figures:
        warnings.append("[Hình ảnh] Không tìm thấy hình ảnh 'figures' nào trong metadata.json.")

    return warnings


def check_math_tokens(
    metadata: dict[str, Any], translated_text: str
) -> tuple[list[str], list[str]]:
    """Kiểm tra các token toán học giữa metadata.json và văn bản dịch."""
    errors = []
    warnings = []
    tokens = metadata.get("math_tokens", [])
    token_map = {t["token_placeholder"]: t.get("raw_latex", "") for t in tokens}

    # Tìm tất cả token có trong văn bản dịch
    found_tokens = set(re.findall(r"<<<MATH_TOKEN_\d{4}>>>", translated_text))
    expected_tokens = set(token_map.keys())

    missing_in_text = expected_tokens - found_tokens
    extra_in_text = found_tokens - expected_tokens

    if missing_in_text:
        # Một số token có thể là số bảng biểu bị thay thế bằng số thực trong markdown đã verify
        warnings.append(
            f"[Toán học] Có {len(missing_in_text)} token trong metadata không xuất hiện trong bản dịch (Có thể đã được thay bằng số thực hoặc công thức trực tiếp)."
        )
    if extra_in_text:
        errors.append(
            f"[Toán học] Có {len(extra_in_text)} token lạ xuất hiện trong bản dịch nhưng không có trong metadata.json: {list(extra_in_text)[:5]}"
        )

    # Kiểm tra cú pháp LaTeX cơ bản trong metadata
    for tok, raw in token_map.items():
        # Kiểm tra đóng mở ngoặc nhọn
        open_curly = raw.count("{")
        close_curly = raw.count("}")
        if open_curly != close_curly:
            warnings.append(
                f"[Toán học] Cú pháp lệch ngoặc nhọn {{ }} tại {tok}: '{raw[:40]}...'"
            )

    return errors, warnings


def check_markdown_tables(md_text: str) -> list[str]:
    """Kiểm tra số cột trong từng hàng của các bảng biểu Markdown."""
    warnings = []
    lines = md_text.splitlines()
    in_table = False
    table_num = 0
    col_count = 0
    header_line = ""

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cols = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                in_table = True
                table_num += 1
                col_count = len(cols)
                header_line = stripped
            else:
                # Bỏ qua dòng phân cách |---|---|
                if re.match(r"^\|?\s*[-:]+[-|\s:]*\|?$", stripped):
                    continue
                if len(cols) != col_count:
                    warnings.append(
                        f"[Bảng {table_num} - Dòng {line_idx}] Lệch số cột! Header có {col_count} cột nhưng dòng này chỉ có {len(cols)} cột: '{stripped[:50]}...'. Thường do OCR bỏ sót dấu '-' hoặc ô trống!"
                    )
        else:
            in_table = False
            col_count = 0

    return warnings


def check_ocr_artifacts(text: str) -> list[str]:
    """Phát hiện các đoạn rác OCR điển hình từ sơ đồ hoặc số phương trình trôi dạt."""
    warnings = []
    # Rác từ sơ đồ khối
    diagram_box_junk = [
        "LOL Stage",
        "Deblur Stage",
        "Upsampling",
        "LNorm",
        "ModulePhase",
        "P-Shu",
        "ffl",
        "Chen's Oid",
    ]
    for junk in diagram_box_junk:
        if junk.lower() in text.lower():
            warnings.append(
                f"[Rác OCR] Phát hiện chuỗi nhãn sơ đồ rác '{junk}' trong văn bản dịch. Hãy loại bỏ khỏi nội dung đoạn văn."
            )

    # Số phương trình trôi dạt (ví dụ dòng bắt đầu bằng (4) hoặc (5) đứng riêng lẻ hoặc trước văn bản khác)
    drifted_eq = re.findall(r"^\((\d+)\)\s+[A-Za-zÀ-ỹ]", text, re.MULTILINE)
    if drifted_eq:
        warnings.append(
            f"[Số phương trình] Phát hiện số phương trình có dấu hiệu trôi dạt vào văn bản: {drifted_eq}. Hãy kiểm tra xem đây có phải số thứ tự công thức (4), (5) bị đặt nhầm chỗ không."
        )

    return warnings


def check_references(text: str) -> list[str]:
    """Kiểm tra sự hiện diện của phần Tài liệu tham khảo."""
    warnings = []
    has_ref_heading = bool(re.search(r"(?:Tài liệu tham khảo|References)", text, re.IGNORECASE))
    has_citations = bool(re.search(r"\[\d+\].*?(?:19\d{2}|20\d{2})", text))

    if not has_ref_heading and not has_citations:
        warnings.append(
            "[Tài liệu tham khảo] Chưa phát hiện danh mục Tài liệu tham khảo (References). Hãy bổ sung các trích dẫn [1]... từ bản PDF gốc."
        )
    return warnings


def verify_translation(output_dir: Path) -> dict[str, Any]:
    """Chạy toàn bộ quy trình kiểm tra trên thư mục output."""
    output_dir = Path(output_dir).resolve()
    if not output_dir.is_dir():
        print(f"Lỗi: Không tìm thấy thư mục {output_dir}", file=sys.stderr)
        sys.exit(1)

    metadata_path = output_dir / "metadata.json"
    batches_dir = output_dir / "batches"

    if not metadata_path.is_file():
        print(f"Lỗi: Không tìm thấy {metadata_path}", file=sys.stderr)
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Đọc tất cả các file translated_batch_*.md
    translated_batches = sorted(batches_dir.glob("translated_batch_*.md"))
    if not translated_batches:
        print(f"Lỗi: Không tìm thấy file translated_batch_*.md nào trong {batches_dir}", file=sys.stderr)
        sys.exit(1)

    combined_text = ""
    for b_path in translated_batches:
        with open(b_path, "r", encoding="utf-8") as f:
            combined_text += f"\n\n{f.read()}"

    all_errors = []
    all_warnings = []

    # 1. Metadata check
    all_warnings.extend(check_metadata(metadata))

    # 2. Math tokens check
    t_errs, t_warns = check_math_tokens(metadata, combined_text)
    all_errors.extend(t_errs)
    all_warnings.extend(t_warns)

    # 3. Tables check
    all_warnings.extend(check_markdown_tables(combined_text))

    # 4. OCR artifacts check
    all_warnings.extend(check_ocr_artifacts(combined_text))

    # 5. References check
    all_warnings.extend(check_references(combined_text))

    return {
        "output_dir": str(output_dir),
        "total_batches": len(translated_batches),
        "total_words": len(combined_text.split()),
        "errors": all_errors,
        "warnings": all_warnings,
        "is_clean": len(all_errors) == 0 and len(all_warnings) == 0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verify and validate academic paper translation results."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Đường dẫn tới thư mục kết quả bài báo (ví dụ output/<tên-paper>)",
    )
    args = parser.parse_args()

    results = verify_translation(Path(args.output_dir))

    print("=" * 70)
    print(" BÁO CÁO KIỂM TRA CHÉO TÍNH TOÀN VẸN BẢN DỊCH (TRANSLATION VERIFICATION)")
    print("=" * 70)
    print(f"Thư mục kiểm tra : {results['output_dir']}")
    print(f"Số batch đã dịch : {results['total_batches']}")
    print(f"Tổng số từ dịch  : {results['total_words']:,} từ")
    print("-" * 70)

    if results["errors"]:
        print(f"[!] PHÁT HIỆN {len(results['errors'])} LỖI NGHIÊM TRỌNG:")
        for e in results["errors"]:
            print(f"  - {e}")
    else:
        print("[✓] Không có lỗi nghiêm trọng.")

    if results["warnings"]:
        print(f"\n[!] CÓ {len(results['warnings'])} ĐIỂM CẦN LƯU Ý / HIỆU CHỈNH:")
        for w in results["warnings"]:
            print(f"  - {w}")
    else:
        print("[✓] Bản dịch hoàn toàn sạch rác OCR và đạt chuẩn toàn vẹn.")

    print("=" * 70)
    if results["is_clean"]:
        print("Trạng thái: ĐẠT CHUẨN (Sẵn sàng biên dịch HTML Canvas A4)")
        sys.exit(0)
    else:
        print("Trạng thái: CẦN RÀ SOÁT LẠI trước khi kết xuất cuối cùng.")
        sys.exit(1 if results["errors"] else 0)


if __name__ == "__main__":
    main()
