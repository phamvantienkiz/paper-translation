"""
Module cô lập và khôi phục công thức toán học LaTeX.
Bảo toàn các công thức Toán học dưới dạng mã đại diện <<<MATH_TOKEN_XXXX>>>
nhằm chống việc dịch làm sai lệch ký hiệu khoa học.
"""

from __future__ import annotations

import re
from typing import Any


class LaTeXIsolator:
    """Isolates LaTeX formulas before translation and re-injects them after translation."""

    # Environments like \begin{equation}...\end{equation}, \begin{align}...\end{align}
    ENV_PATTERN = re.compile(
        r"\\begin\{(equation|align|gather|multline|matrix|pmatrix|bmatrix|vmatrix)\*?\}.*?\\end\{\1\*?\}",
        re.DOTALL,
    )
    # Display math: $$ ... $$ or \[ ... \]
    DISPLAY_PATTERN = re.compile(r"(\$\$.*?\$\$|\\\[.*?\\\])", re.DOTALL)
    # Inline math: $ ... $ or \( ... \)
    INLINE_PATTERN = re.compile(r"(?<!\$)\$(?!\$)([^\$\n]+?)(?<!\$)\$(?!\$)|(\\\(.*?\\\))")

    @classmethod
    def isolate_formulas(
        cls, text: str, start_index: int = 1
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Quét văn bản tìm công thức LaTeX, thay thế bằng token <<<MATH_TOKEN_XXXX>>>
        và trả về văn bản đã mask kèm danh sách token tương ứng.
        """
        tokens: list[dict[str, Any]] = []
        current_idx = start_index

        def env_replacer(match: re.Match) -> str:
            nonlocal current_idx
            placeholder = f"<<<MATH_TOKEN_{current_idx:04d}>>>"
            raw_math = match.group(0)
            tokens.append({
                "token_placeholder": placeholder,
                "raw_latex": raw_math,
                "is_display_math": True,
            })
            current_idx += 1
            return placeholder

        def display_replacer(match: re.Match) -> str:
            nonlocal current_idx
            placeholder = f"<<<MATH_TOKEN_{current_idx:04d}>>>"
            raw_math = match.group(0)
            tokens.append({
                "token_placeholder": placeholder,
                "raw_latex": raw_math,
                "is_display_math": True,
            })
            current_idx += 1
            return placeholder

        def inline_replacer(match: re.Match) -> str:
            nonlocal current_idx
            placeholder = f"<<<MATH_TOKEN_{current_idx:04d}>>>"
            raw_math = match.group(0)
            tokens.append({
                "token_placeholder": placeholder,
                "raw_latex": raw_math,
                "is_display_math": False,
            })
            current_idx += 1
            return placeholder

        # 1. First replace complex environments
        masked = cls.ENV_PATTERN.sub(env_replacer, text)
        # 2. Then replace display math $$ ... $$
        masked = cls.DISPLAY_PATTERN.sub(display_replacer, masked)
        # 3. Finally replace inline math $ ... $
        masked = cls.INLINE_PATTERN.sub(inline_replacer, masked)

        return masked, tokens

    @classmethod
    def reinject_formulas(
        cls, text: str, token_map: dict[str, str] | list[dict[str, Any]]
    ) -> str:
        """
        Khôi phục lại token <<<MATH_TOKEN_XXXX>>> thành công thức LaTeX gốc.
        """
        if isinstance(token_map, list):
            mapping = {
                t["token_placeholder"]: t["raw_latex"]
                for t in token_map
                if "token_placeholder" in t and "raw_latex" in t
            }
        else:
            mapping = token_map

        # Chuẩn hóa khoảng trắng vô ý do LLM chèn vào (ví dụ <<< MATH_TOKEN_0001 >>>)
        normalized_text = re.sub(
            r"<<<\s*(MATH_TOKEN_\d+)\s*>>>",
            r"<<<\1>>>",
            text,
        )

        for placeholder, raw_latex in mapping.items():
            normalized_text = normalized_text.replace(placeholder, raw_latex)

        return normalized_text
