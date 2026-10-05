import pytest
from app.services.parser.math_isolator import LaTeXIsolator


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_latex_isolator():
    sample_text = (
        "In this paper, we propose the attention mechanism where "
        "$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$ "
        "and display equation is:\n"
        "$$\\mathcal{L}_{total} = \\sum_{i=1}^N (y_i - \\hat{y}_i)^2$$\n"
        "This improves model convergence."
    )

    masked, tokens = LaTeXIsolator.isolate_formulas(sample_text)
    assert len(tokens) == 2
    assert "<<<MATH_TOKEN_0001>>>" in masked
    assert "<<<MATH_TOKEN_0002>>>" in masked
    assert "softmax" not in masked  # The math is hidden!

    # Test re-injection
    token_map = {t["token_placeholder"]: t["raw_latex"] for t in tokens}
    restored = LaTeXIsolator.reinject_formulas(masked, token_map)
    assert restored == sample_text
