import re
from typing import Dict, List, Tuple, Union


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
    ) -> Tuple[str, List[Dict[str, any]]]:
        """
        Scans text for LaTeX formulas, replaces each with a placeholder token,
        and returns the masked text along with the list of extracted tokens.
        """
        tokens: List[Dict[str, any]] = []
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
    def reinject_formulas(cls, text: str, token_map: Union[Dict[str, str], List[Dict[str, any]]]) -> str:
        """
        Replaces placeholders back with their original LaTeX formulas.
        token_map can be:
        - {placeholder: raw_latex}
        - or list of token dicts [{"token_placeholder": ..., "raw_latex": ...}, ...]
        """
        if not text or not token_map:
            return text

        result = text
        if isinstance(token_map, list):
            for tok in token_map:
                ph = tok.get("token_placeholder")
                raw = tok.get("raw_latex", "")
                if ph:
                    result = result.replace(ph, raw)
        elif isinstance(token_map, dict):
            for placeholder, raw_latex in token_map.items():
                result = result.replace(placeholder, raw_latex)
        return result
