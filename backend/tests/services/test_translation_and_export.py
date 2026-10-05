import fitz
import pytest
from app.services.export.pdf_exporter import PDFExporter
from app.services.parser.math_isolator import LaTeXIsolator
from app.services.translation.translator import (
    MockTranslator,
    OpenAICompatibleTranslator,
    TranslationFactory,
)


@pytest.mark.asyncio
async def test_mock_translator_with_glossary_and_math():
    translator = MockTranslator()
    raw_text = (
        "We propose a Transformer architecture based on multi-head attention mechanism. "
        "The loss function optimizes $\\mathcal{L}(\\theta) = -\\log p(x)$ using gradient descent."
    )
    masked_text, tokens = LaTeXIsolator.isolate_formulas(raw_text)
    assert "<<<MATH_TOKEN_0001>>>" in masked_text

    translated = await translator.translate_text(masked_text)

    # 1. Bảo toàn 100% token toán học
    assert "<<<MATH_TOKEN_0001>>>" in translated

    # 2. Dịch thuật ngữ theo Glossary IT & AI
    assert "Transformer" in translated
    assert "chú ý đa đầu (multi-head attention)" in translated
    assert "hàm mất mát (loss function)" in translated
    assert "hạ độ dốc (gradient descent)" in translated

    # 3. Khôi phục nguyên trạng công thức toán
    restored = LaTeXIsolator.reinject_formulas(translated, tokens)
    assert "$\\mathcal{L}(\\theta) = -\\log p(x)$" in restored


@pytest.mark.asyncio
async def test_openai_compatible_translator_endpoint_and_fallback():
    # Kiểm tra cấu trúc endpoint chuẩn OpenAI
    translator = OpenAICompatibleTranslator(
        api_base="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key="dummy_key",
        model="gemini-3.5-flash-lite",
    )
    assert translator.endpoint == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

    # Khi dummy_key gặp lỗi kết nối hoặc HTTP error, tự động fallback sang MockTranslator an toàn
    result = await translator.translate_text("Introduction to Transformer architecture.")
    assert "Giới thiệu" in result or "Transformer" in result


def test_translation_factory():
    translator = TranslationFactory.get_translator()
    assert translator is not None


@pytest.mark.asyncio
async def test_inline_edit_segment_api(client):
    # 1. Tạo tài liệu qua upload PDF
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 72), "Deep Learning Overview", fontsize=14)
    p.insert_text((50, 110), "Convolutional neural networks are effective for image processing.", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("dl.pdf", pdf_bytes, "application/pdf")}
    res = await client.post("/api/v1/ingestion/upload", files=files)
    assert res.status_code == 200
    session_id = res.json()["data"]["session_id"]

    # 2. Lấy danh sách segments
    segs_res = await client.get(f"/api/v1/sessions/{session_id}/segments")
    segments = segs_res.json()["data"]
    assert len(segments) >= 1
    target_seg = segments[0]

    # 3. Chỉnh sửa Inline Edit qua PATCH /segments/{id}
    new_text = "Tổng quan học sâu: Mạng nơ-ron tích chập (CNN) rất hiệu quả trong xử lý thị giác máy tính."
    patch_res = await client.patch(
        f"/api/v1/segments/{target_seg['id']}",
        json={"translated_content": new_text},
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()["data"]
    assert patched_data["translated_content"] == new_text
    assert patched_data["is_user_edited"] is True


@pytest.mark.asyncio
async def test_export_pdf_api(client):
    # 1. Tạo tài liệu
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 72), "Attention Mechanisms in AI", fontsize=16)
    p.insert_text((50, 120), "We define attention score as $S(Q, K) = \\frac{QK^T}{\\sqrt{d_k}}$.", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("attention_export.pdf", pdf_bytes, "application/pdf")}
    res = await client.post("/api/v1/ingestion/upload", files=files)
    session_id = res.json()["data"]["session_id"]

    # 2. Gọi API xuất bản dịch PDF
    export_res = await client.get(f"/api/v1/sessions/{session_id}/export/pdf")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/pdf"
    assert len(export_res.content) > 500
    assert export_res.content.startswith(b"%PDF-")
