#!/usr/bin/env python3
"""
inspect_tokens.py
-----------------
Công cụ kiểm tra nhanh danh sách công thức toán học và token LaTeX trong metadata.json.
Giúp Agent và người dùng kiểm tra:
- Số lượng token toán học đã cô lập.
- Nội dung raw_latex của từng token.
- Phân loại công thức dạng khối (display math $$...$$) và nội dòng (inline math $...$).
- Tìm kiếm token theo từ khóa hoặc mã token.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Đảm bảo UTF-8 cho Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect LaTeX math tokens in metadata.json."
    )
    parser.add_argument(
        "--metadata",
        required=True,
        help="Đường dẫn tới tệp metadata.json hoặc thư mục output",
    )
    parser.add_argument(
        "--query",
        default="",
        help="Từ khóa lọc nội dung công thức (ví dụ 'gamma', 'nabla', 'L_pixel')",
    )
    parser.add_argument(
        "--token",
        default="",
        help="Mã token cụ thể cần tra cứu (ví dụ 'MATH_TOKEN_0002')",
    )

    args = parser.parse_args()

    meta_path = Path(args.metadata).resolve()
    if meta_path.is_dir():
        meta_path = meta_path / "metadata.json"

    if not meta_path.is_file():
        print(f"Lỗi: Không tìm thấy tệp {meta_path}", file=sys.stderr)
        sys.exit(1)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    tokens = meta.get("math_tokens", [])
    print(f"Tiêu đề bài báo : {meta.get('title', 'N/A')}")
    print(f"Tổng số token   : {len(tokens)}")
    print("-" * 70)

    matched = 0
    for idx, t in enumerate(tokens, start=1):
        placeholder = t.get("token_placeholder", "")
        raw_latex = t.get("raw_latex", "")
        is_display = t.get("is_display_math", False)

        if args.token and args.token.lower() not in placeholder.lower():
            continue
        if args.query and args.query.lower() not in raw_latex.lower():
            continue

        matched += 1
        kind = "Khối (Display)" if is_display else "Nội dòng (Inline)"
        print(f"[{idx:03d}] {placeholder:<25} | {kind:<16} | {raw_latex}")

    print("-" * 70)
    print(f"Đã hiển thị {matched}/{len(tokens)} token phù hợp.")


if __name__ == "__main__":
    main()
