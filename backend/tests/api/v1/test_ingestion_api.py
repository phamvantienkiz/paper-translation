import io
import fitz
import pytest
from docx import Document


@pytest.mark.asyncio
async def test_upload_pdf_api(client):
    # 1. Create a dummy scientific PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Attention Is All You Need", fontsize=18)
    page.insert_text(
        (50, 120),
        "We propose the Transformer model with attention $A = \\text{softmax}(QK^T / \\sqrt{d_k})V$.",
        fontsize=12,
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    # 2. Upload via API
    files = {"file": ("attention.pdf", pdf_bytes, "application/pdf")}
    response = await client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 200
    res_body = response.json()
    assert res_body["success"] is True
    data = res_body["data"]
    assert data["source_type"] == "PDF"
    assert "session_id" in data
    session_id = data["session_id"]

    # 3. Retrieve session details
    session_res = await client.get(f"/api/v1/sessions/{session_id}")
    assert session_res.status_code == 200
    session_data = session_res.json()["data"]
    assert session_data["file_name"] == "attention.pdf"

    # 4. Retrieve segments
    segments_res = await client.get(f"/api/v1/sessions/{session_id}/segments")
    assert segments_res.status_code == 200
    segments = segments_res.json()["data"]
    assert len(segments) >= 1

    # 5. Retrieve math tokens
    tokens_res = await client.get(f"/api/v1/sessions/{session_id}/tokens")
    assert tokens_res.status_code == 200
    tokens = tokens_res.json()["data"]
    assert len(tokens) >= 1
    assert any("<<<MATH_TOKEN_" in t["token_placeholder"] for t in tokens)


@pytest.mark.asyncio
async def test_upload_docx_api(client):
    # 1. Create a dummy scientific DOCX
    doc = Document()
    doc.add_heading("Deep Residual Learning", level=1)
    doc.add_paragraph("Residual networks ease the training of networks that are substantially deeper.")
    doc.add_paragraph("We define the residual block as $y = F(x, {W_i}) + x$.")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Architecture"
    table.cell(0, 1).text = "Top-1 Error"
    table.cell(1, 0).text = "ResNet-152"
    table.cell(1, 1).text = "4.49%"

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    # 2. Upload via API
    files = {
        "file": (
            "resnet.docx",
            docx_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = await client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 200
    res_body = response.json()
    assert res_body["success"] is True
    data = res_body["data"]
    assert data["source_type"] == "DOCX"
    session_id = data["session_id"]

    # 3. Retrieve segments
    segments_res = await client.get(f"/api/v1/sessions/{session_id}/segments")
    assert segments_res.status_code == 200
    segments = segments_res.json()["data"]
    assert len(segments) >= 2


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client):
    files = {"file": ("malicious.exe", b"MZ\x90\x00", "application/octet-stream")}
    response = await client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 400
    assert "Định dạng tệp không được hỗ trợ" in response.json()["detail"]
