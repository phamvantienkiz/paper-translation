from app.services.parser.math_isolator import LaTeXIsolator


def test_isolate_inline_math():
    text = "The loss function is defined as $L(\\theta) = -\\log p(x)$ for all parameters."
    masked_text, tokens = LaTeXIsolator.isolate_formulas(text)

    assert "<<<MATH_TOKEN_0001>>>" in masked_text
    assert len(tokens) == 1
    assert tokens[0]["raw_latex"] == "$L(\\theta) = -\\log p(x)$"
    assert not tokens[0]["is_display_math"]

    restored = LaTeXIsolator.reinject_formulas(masked_text, tokens)
    assert restored == text


def test_isolate_display_math():
    text = (
        "Equation of attention:\n"
        "$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$\n"
        "where Q, K, V are matrices."
    )
    masked_text, tokens = LaTeXIsolator.isolate_formulas(text)

    assert "<<<MATH_TOKEN_0001>>>" in masked_text
    assert len(tokens) == 1
    assert tokens[0]["is_display_math"]
    assert "\\text{Attention}" in tokens[0]["raw_latex"]

    restored = LaTeXIsolator.reinject_formulas(masked_text, tokens)
    assert restored == text


def test_isolate_equation_environment():
    text = (
        "Consider the formulation:\n"
        "\\begin{equation}\n"
        "f(x) = \\sigma(W x + b)\n"
        "\\end{equation}\n"
        "which provides the activation."
    )
    masked_text, tokens = LaTeXIsolator.isolate_formulas(text)

    assert "<<<MATH_TOKEN_0001>>>" in masked_text
    assert len(tokens) == 1
    assert tokens[0]["is_display_math"]
    assert "\\begin{equation}" in tokens[0]["raw_latex"]

    restored = LaTeXIsolator.reinject_formulas(masked_text, tokens)
    assert restored == text


def test_isolate_multiple_mixed_tokens():
    text = (
        "Given input $x \\in \\mathbb{R}^d$ and target $y \\in \\{0, 1\\}$, "
        "we compute:\n"
        "$$\\hat{y} = \\sigma(w^T x)$$\n"
        "with loss $J(w)$."
    )
    masked_text, tokens = LaTeXIsolator.isolate_formulas(text)

    assert len(tokens) == 4
    assert "<<<MATH_TOKEN_0001>>>" in masked_text
    assert "<<<MATH_TOKEN_0002>>>" in masked_text
    assert "<<<MATH_TOKEN_0003>>>" in masked_text
    assert "<<<MATH_TOKEN_0004>>>" in masked_text

    restored = LaTeXIsolator.reinject_formulas(masked_text, tokens)
    assert restored == text
