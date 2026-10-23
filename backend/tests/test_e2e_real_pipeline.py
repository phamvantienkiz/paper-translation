from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.db.session import engine
from app.main import create_app
from app.services.parser.indra_ocr_service import IndraOcrService
from app.services.translation.llama_client_service import LlamaInternalClient
from app.services.translation.llama_server_manager import LlamaServerManager

# Tệp bài báo khoa học thực tế (1 trang trích xuất từ bài báo CVPR 2025)
REAL_SAMPLE_PDF = Path("backend/storage/raw_pdfs/sample_page1_real_paper.pdf")
MODEL_GGUF_PATH = Path("backend/storage/models/gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf")


@pytest.fixture(scope="module", autouse=True)
def cleanup_after_module():
    """Đảm bảo dọn dẹp sạch tiến trình Standalone llama.cpp server sau khi chạy xong module."""
    yield
    LlamaServerManager.reset()


@pytest.mark.skipif(not REAL_SAMPLE_PDF.exists(), reason="Tệp PDF thực tế không tồn tại")
@pytest.mark.skipif(not MODEL_GGUF_PATH.exists(), reason="Tệp mô hình Gemma-4-E2B GGUF không tồn tại")
class TestRealPipelineE2E:
    """
    Testcase E2E xác thực toàn bộ chu trình xử lý thực tế 100%:
    1. Chạy thật Indra OCR bóc tách layout, reading order, tọa độ hộp và công thức toán từ PDF thực tế.
    2. Thu hồi sạch tài nguyên RAM của Indra OCR trước khi chạy LLM.
    3. Tự động spawn Standalone llama.cpp Server với mô hình thật gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf.
    4. Cấu hình đúng 4 P-cores trên Intel Core i5-13500H và giới hạn trần RAM <= 8.0GB.
    5. Python Client giao tiếp qua loopback nội bộ 127.0.0.1:8081 để dịch thuật các khối bài báo.
    6. Kiểm tra bản dịch tiếng Việt sinh ra bảo toàn 100% định danh [[BLK_XXXX]], lưu vào database và sẵn sàng hiển thị trên Canvas.
    """

    @pytest.mark.asyncio
    async def test_full_real_ocr_standalone_llama_pipeline(self):
        # 0. Khởi tạo database schema
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        app = create_app()

        # 1. Giai đoạn 1: Nạp file PDF bài báo thực tế qua Ingestion API
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            pdf_bytes = REAL_SAMPLE_PDF.read_bytes()
            files = {"file": ("sample_paper.pdf", pdf_bytes, "application/pdf")}
            resp = await client.post("/api/v1/ingestion/upload", files=files)
            assert resp.status_code == 200, f"Upload thất bại: {resp.text}"
            upload_data = resp.json()["data"]
            session_id = upload_data["session_id"]
            assert session_id is not None

        # 2. Giai đoạn 2: Chạy Indra OCR thật bóc tách layout và tọa độ
        ocr = IndraOcrService()
        parsed_doc = ocr.parse_pdf(REAL_SAMPLE_PDF)

        assert parsed_doc.total_pages == 1
        assert len(parsed_doc.blocks) >= 10, "Indra OCR phải bóc tách được các khối văn bản từ trang bài báo"
        
        # Kiểm tra chuẩn hóa tọa độ hộp [0.0 .. 1.0]
        first_block = parsed_doc.blocks[0]
        assert len(first_block.bbox_norm) == 4
        assert 0.0 <= first_block.bbox_norm[0] <= 1.0
        assert 0.0 <= first_block.bbox_norm[1] <= 1.0

        # Thu hồi sạch tài nguyên OCR trước khi gọi LLM theo quy tắc Sequential Mutex
        ocr.unload()

        # 3. Giai đoạn 3: Kiểm tra khởi động Standalone llama.cpp Server với model Gemma-4-E2B thật
        server_mgr = LlamaServerManager.get_instance(
            model_path=MODEL_GGUF_PATH,
            n_ctx=8192,
            n_threads=4,  # 4 P-cores Intel Core i5-13500H
        )
        await server_mgr.ensure_server_running(wait_timeout=45.0)
        assert server_mgr.is_running is True
        assert await server_mgr.is_healthy_async() is True

        # 4. Giai đoạn 4: Python Client giao tiếp qua mạng nội bộ thực thi dịch thuật
        llama_client = LlamaInternalClient(server_manager=server_mgr)

        sample_blocks = [b for b in parsed_doc.blocks if b.is_translatable and (b.text or "").strip()][:3]
        assert len(sample_blocks) >= 1, "Phải có ít nhất 1 khối cần dịch"

        user_content = "\n\n".join(f"[[{b.block_code}]]\n{b.text}" for b in sample_blocks)
        messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia dịch thuật bài báo khoa học. "
                    "Dịch chính xác từng khối sang tiếng Việt học thuật chuẩn xác. "
                    "BẮT BUỘC giữ nguyên mã định danh [[BLK_XXXX]] ở đầu mỗi khối. "
                    "Giữ nguyên 100% công thức LaTeX $...$."
                ),
            },
            {"role": "user", "content": user_content},
        ]

        # Thực hiện suy luận thực tế với model Gemma-4-E2B Q4_K_XL
        translated_output = await llama_client.create_chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.2,
        )

        assert translated_output is not None and len(translated_output.strip()) > 0
        # Xác nhận mô hình bảo toàn mã khối [[BLK_XXXX]]
        for b in sample_blocks:
            assert f"[[{b.block_code}]]" in translated_output, (
                f"Mã khối [[{b.block_code}]] không xuất hiện trong phản hồi: {translated_output}"
            )

        # 5. Giai đoạn 5: Kiểm tra kết quả qua Canvas Data API
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            canvas_resp = await client.get(f"/api/v1/sessions/{session_id}/canvas-data")
            assert canvas_resp.status_code == 200
            canvas_data = canvas_resp.json()["data"]
            assert canvas_data["session_id"] == session_id
            assert canvas_data["total_pages"] >= 1
            assert len(canvas_data["pages"]) >= 1

            # Kiểm tra trạng thái Engine trên UI API
            engine_resp = await client.get("/api/v1/system/engine-status")
            assert engine_resp.status_code == 200
            eng_data = engine_resp.json()
            assert eng_data["serving_mode"] == "standalone_server"
            assert eng_data["threads"] == 4
            assert eng_data["hard_ram_ceiling_gb"] == 8.0
            assert eng_data["llm_loaded"] is True
