import uuid

import fitz
import pytest

from app.db.session import AsyncSessionLocal
from app.repositories.ocr_block_repository import OcrBlockRepository
from app.repositories.page_repository import PageRepository
from app.repositories.session_repository import SessionRepository


@pytest.mark.asyncio
async def test_canvas_data_api(client):
    session_id = f"test-canvas-{uuid.uuid4()}"
    async with AsyncSessionLocal() as db:
        session_repo = SessionRepository(db)
        page_repo = PageRepository(db)
        block_repo = OcrBlockRepository(db)

        session = await session_repo.create({
            "id": session_id,
            "source_type": "PDF",
            "file_name": "sample_paper.pdf",
            "file_size_bytes": 1024,
            "file_path": f"storage/raw/{session_id}/original.pdf",
            "pdf_path": f"storage/raw_pdfs/{session_id}.pdf",
            "title": "Attention Is All You Need",
            "total_pages": 1,
            "status": "COMPLETED",
            "progress_percent": 100,
        })

        page = await page_repo.create({
            "id": str(uuid.uuid4()),
            "session_id": session.id,
            "page_number": 1,
            "width_pt": 595.27,
            "height_pt": 841.89,
            "ocr_rotation": 0,
            "ocr_skew": 0.0,
            "page_image_path": f"storage/pages/{session_id}/page_1.png",
        })

        _block = await block_repo.create({
            "id": str(uuid.uuid4()),
            "session_id": session.id,
            "page_id": page.id,
            "page_number": 1,
            "block_code": "BLK_0001",
            "reading_order": 0,
            "label": "title",
            "bbox_x0": 0.084,
            "bbox_y0": 0.085,
            "bbox_x1": 0.915,
            "bbox_y1": 0.130,
            "is_translatable": True,
            "original_text": "Attention Is All You Need",
            "translated_text": "Cơ Chế Chú Ý Là Tất Cả Những Gì Bạn Cần",
            "is_user_edited": False,
        })

    # 2. Gọi GET /api/v1/sessions/{session_id}/canvas-data
    response = await client.get(f"/api/v1/sessions/{session.id}/canvas-data")
    assert response.status_code == 200
    res_body = response.json()
    assert res_body["success"] is True

    canvas_data = res_body["data"]
    assert canvas_data["session_id"] == session.id
    assert canvas_data["title"] == "Attention Is All You Need"
    assert canvas_data["total_pages"] == 1
    assert len(canvas_data["pages"]) == 1

    page_data = canvas_data["pages"][0]
    assert page_data["page_number"] == 1
    assert page_data["width_pt"] == 595.27
    assert "/api/v1/assets/pages/" in page_data["page_image_url"]
    assert len(page_data["blocks"]) == 1

    blk_data = page_data["blocks"][0]
    assert blk_data["block_code"] == "BLK_0001"
    assert blk_data["bbox_norm"] == [0.084, 0.085, 0.915, 0.13]
    assert blk_data["translated_text"] == "Cơ Chế Chú Ý Là Tất Cả Những Gì Bạn Cần"
    assert blk_data["is_translatable"] is True

    # 3. Kiểm tra endpoint phục vụ ảnh nền trang: GET /api/v1/assets/pages/{session_id}/page_1.png
    from app.core.config import settings
    page_img_file = settings.pages_dir / session.id / "page_1.png"
    page_img_file.parent.mkdir(parents=True, exist_ok=True)
    page_img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    img_res = await client.get(f"/api/v1/assets/pages/{session.id}/page_1.png")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_patch_block_translation(client):
    session_id = f"test-patch-{uuid.uuid4()}"
    async with AsyncSessionLocal() as db:
        session_repo = SessionRepository(db)
        page_repo = PageRepository(db)
        block_repo = OcrBlockRepository(db)

        session = await session_repo.create({
            "id": session_id,
            "source_type": "PDF",
            "file_name": "patch_paper.pdf",
            "file_size_bytes": 1024,
            "file_path": f"storage/raw/{session_id}/original.pdf",
            "status": "COMPLETED",
        })

        page = await page_repo.create({
            "id": str(uuid.uuid4()),
            "session_id": session.id,
            "page_number": 1,
            "width_pt": 595.27,
            "height_pt": 841.89,
            "page_image_path": f"storage/pages/{session_id}/page_1.png",
        })

        block = await block_repo.create({
            "id": str(uuid.uuid4()),
            "session_id": session.id,
            "page_id": page.id,
            "page_number": 1,
            "block_code": "BLK_0001",
            "reading_order": 0,
            "label": "text",
            "bbox_x0": 0.1,
            "bbox_y0": 0.1,
            "bbox_x1": 0.5,
            "bbox_y1": 0.2,
            "is_translatable": True,
            "original_text": "Original text before edit.",
            "translated_text": "Bản dịch cũ.",
            "is_user_edited": False,
        })

    # Gọi PATCH /api/v1/blocks/{block_id}
    new_text = "Bản dịch tiếng Việt đã được người dùng chỉnh sửa hoàn thiện."
    patch_res = await client.patch(
        f"/api/v1/blocks/{block.id}",
        json={"translated_text": new_text},
    )
    assert patch_res.status_code == 200
    res_body = patch_res.json()
    assert res_body["success"] is True
    assert res_body["data"]["translated_text"] == new_text
    assert res_body["data"]["is_user_edited"] is True


@pytest.mark.asyncio
async def test_export_pdf_direct_endpoint(client):
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 72), "Layout Test Paper", fontsize=14)
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("direct_export.pdf", pdf_bytes, "application/pdf")}
    res = await client.post("/api/v1/ingestion/upload", files=files)
    assert res.status_code == 200
    session_id = res.json()["data"]["session_id"]

    # Gọi GET /api/v1/export/{session_id}/pdf
    export_res = await client.get(f"/api/v1/export/{session_id}/pdf")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/pdf"
    assert len(export_res.content) > 100
