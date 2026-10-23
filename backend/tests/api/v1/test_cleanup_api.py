import uuid

import pytest

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.session_repository import SessionRepository


@pytest.mark.asyncio
async def test_delete_session_and_cleanup_files(client):
    session_id = f"test-cleanup-{uuid.uuid4()}"

    # Tạo file mẫu trong backend/storage/pages và backend/storage/raw_pdfs
    page_folder = settings.pages_dir / session_id
    page_folder.mkdir(parents=True, exist_ok=True)
    sample_page_img = page_folder / "page_1.png"
    sample_page_img.write_bytes(b"dummy image bytes")

    pdf_file = settings.raw_pdfs_dir / f"{session_id}.pdf"
    pdf_file.write_bytes(b"dummy pdf bytes")

    assert sample_page_img.exists()
    assert pdf_file.exists()

    async with AsyncSessionLocal() as db:
        session_repo = SessionRepository(db)
        await session_repo.create({
            "id": session_id,
            "source_type": "PDF",
            "file_name": "cleanup_test.pdf",
            "file_size_bytes": 1024,
            "file_path": str(pdf_file),
            "pdf_path": str(pdf_file),
            "status": "COMPLETED",
        })

    # Gọi DELETE /api/v1/sessions/{session_id}
    res = await client.delete(f"/api/v1/sessions/{session_id}")
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["success"] is True

    # Xác nhận các file vật lý đã bị xóa hoàn toàn khỏi backend/storage/
    assert not sample_page_img.exists()
    assert not page_folder.exists()
    assert not pdf_file.exists()

    # Kiểm tra không còn session trong DB
    check_res = await client.get(f"/api/v1/sessions/{session_id}")
    assert check_res.status_code == 404


@pytest.mark.asyncio
async def test_cleanup_temp_files_endpoint(client):
    # Tạo một file rác trong backend/storage/temp/
    dummy_temp_file = settings.temp_dir / f"test_temp_{uuid.uuid4()}.tmp"
    dummy_temp_file.write_text("temporary data")
    assert dummy_temp_file.exists()

    res = await client.post("/api/v1/sessions/cleanup-temp")
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["success"] is True
    assert res_json["data"]["deleted_count"] >= 1
    assert not dummy_temp_file.exists()
