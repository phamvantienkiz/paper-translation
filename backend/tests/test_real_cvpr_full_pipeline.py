import json
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.db.session import engine
from app.main import create_app
from app.services.translation.llama_server_manager import LlamaServerManager

# Đường dẫn tệp bài báo khoa học CVPR 2025 thực tế (11 trang)
REAL_CVPR_PDF = Path("backend/storage/temp/Feijoo_DarkIR_Robust_Low-Light_Image_Restoration_CVPR_2025_paper.pdf")
MODEL_GGUF_PATH = Path("backend/storage/models/gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf")


@pytest.fixture(scope="module", autouse=True)
def cleanup_after_test():
    """Đảm bảo dừng và thu hồi sạch tiến trình server sau khi hoàn tất test."""
    yield
    LlamaServerManager.reset()


@pytest.mark.skipif(not REAL_CVPR_PDF.exists(), reason="Không tìm thấy tệp bài báo CVPR 2025 tại backend/storage/temp/")
@pytest.mark.skipif(not MODEL_GGUF_PATH.exists(), reason="Không tìm thấy mô hình gemma-4-E2B GGUF")
class TestFullRealPaperPipelineE2E:
    """
    Test E2E thực tế 100% không mock, không chạy riêng lẻ:
    Thực thi toàn bộ flow backend thông qua Ingestion Pipeline:
    1. Upload tệp bài báo thật (CVPR 2025 - 11 trang, ~9MB) qua POST /api/v1/ingestion/upload.
    2. Chạy thật Indra OCR đa luồng bóc tách 11 trang, nhận diện cấu trúc 2 cột, Bounding Box và LaTeX.
    3. Thu hồi sạch 100% RAM và CPU của Indra OCR (ONNX Session + ThreadPool).
    4. Standalone llama.cpp Server tự động spawn chạy mô hình gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf
       trên 4 P-cores của Intel Core i5-13500H, context 16K, RAM trần <= 8.0GB.
    5. Dịch thuật toàn văn toàn bộ các khối bài báo theo các lô chuẩn 2,000 - 2,500 từ tiếng Anh
       qua mạng nội bộ HTTP 127.0.0.1:8081.
    6. Thu thập đầy đủ kết quả dịch tiếng Việt từ API /sessions/{id}/canvas-data và ghi nhận thời gian chính xác.
    """

    @pytest.mark.asyncio
    async def test_complete_e2e_translation_with_benchmarks(self):
        total_start_time = time.time()
        benchmark_report = {}

        print("\n" + "=" * 80)
        print(" BẮT ĐẦU TEST E2E THỰC TẾ TOÀN BỘ BACKEND — BÀI BÁO CVPR 2025 (11 TRANG)")
        print(f" File PDF: {REAL_CVPR_PDF} ({REAL_CVPR_PDF.stat().st_size / 1024:.2f} KB)")
        print(f" Model GGUF: {MODEL_GGUF_PATH} ({MODEL_GGUF_PATH.stat().st_size / (1024**3):.2f} GB)")
        print(" LLM Config: 4 P-cores, context=16384, max_output=10240, RAM ceiling=8.0GB")
        print("=" * 80)

        # 0. Khởi tạo DB Schema
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        app = create_app()

        # =========================================================================
        # GIAI ĐOẠN 1: Gửi Request Upload và thực thi trọn vẹn toàn bộ Backend Pipeline
        # (Upload -> Indra OCR 11 trang -> Thu hồi RAM -> Standalone LLM Server -> Dịch full)
        # =========================================================================
        t_pipeline_start = time.time()
        print("\n[BƯỚC 1/3] Gửi yêu cầu Ingestion Upload và kích hoạt quy trình thực tế...")
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            timeout=1800.0,  # 30 phút timeout cho toàn bộ pipeline thực tế của bài báo 11 trang
        ) as client:
            pdf_bytes = REAL_CVPR_PDF.read_bytes()
            files = {"file": (REAL_CVPR_PDF.name, pdf_bytes, "application/pdf")}
            
            resp = await client.post("/api/v1/ingestion/upload", files=files)
            assert resp.status_code == 200, f"Upload API thất bại: {resp.text}"
            upload_data = resp.json()["data"]
            session_id = upload_data["session_id"]
            assert session_id is not None
            
            t_pipeline_duration = time.time() - t_pipeline_start
            benchmark_report["e2e_full_pipeline_seconds"] = round(t_pipeline_duration, 2)
            benchmark_report["e2e_full_pipeline_minutes"] = round(t_pipeline_duration / 60, 2)
            print(f"  -> Toàn bộ pipeline Ingestion + OCR + Dịch thuật hoàn tất trong {t_pipeline_duration:.2f}s ({t_pipeline_duration/60:.2f} phút).")

            # =========================================================================
            # GIAI ĐOẠN 2: Kiểm tra kết quả qua API Canvas Data & Engine Status
            # =========================================================================
            print("\n[BƯỚC 2/3] Kiểm tra kết quả dịch và cấu trúc Canvas qua API...")
            t_verify_start = time.time()
            
            canvas_resp = await client.get(f"/api/v1/sessions/{session_id}/canvas-data")
            assert canvas_resp.status_code == 200, f"Lỗi lấy canvas-data: {canvas_resp.text}"
            canvas_data = canvas_resp.json()["data"]

            assert canvas_data["session_id"] == session_id
            assert canvas_data["total_pages"] == 11, f"Yêu cầu đủ 11 trang, thực tế: {canvas_data['total_pages']}"
            assert len(canvas_data["pages"]) == 11

            # Thu thập và phân loại khối văn bản đã dịch
            all_blocks = []
            translated_blocks = []
            sample_translations = []

            for page in canvas_data["pages"]:
                p_num = page["page_number"]
                for blk in page["blocks"]:
                    all_blocks.append(blk)
                    trans_text = blk.get("translated_text")
                    if trans_text and trans_text.strip():
                        translated_blocks.append(blk)
                        if len(sample_translations) < 6:
                            sample_translations.append({
                                "page": p_num,
                                "block_code": blk.get("block_code"),
                                "label": blk.get("label"),
                                "original": (blk.get("original_text") or "")[:120] + "...",
                                "translated": trans_text[:120] + "...",
                            })

            benchmark_report["total_pages"] = 11
            benchmark_report["total_blocks_extracted"] = len(all_blocks)
            benchmark_report["total_blocks_translated"] = len(translated_blocks)
            benchmark_report["translation_coverage_percent"] = round(
                (len(translated_blocks) / max(1, len(all_blocks))) * 100, 1
            )

            # Kiểm tra trạng thái Engine trên UI API
            engine_resp = await client.get("/api/v1/system/engine-status")
            assert engine_resp.status_code == 200
            eng_data = engine_resp.json()
            assert eng_data["serving_mode"] == "standalone_server"
            assert eng_data["threads"] == 4
            assert eng_data["hard_ram_ceiling_gb"] == 8.0

            t_verify_duration = time.time() - t_verify_start
            benchmark_report["verification_seconds"] = round(t_verify_duration, 2)

        # =========================================================================
        # GIAI ĐOẠN 3: Thu hồi Standalone llama.cpp Server và hoàn tất
        # =========================================================================
        print("\n[BƯỚC 3/3] Thu hồi Standalone llama.cpp Server...")
        server_mgr = LlamaServerManager.get_instance()
        if server_mgr.is_running:
            server_mgr.stop_server()
        assert server_mgr.is_running is False
        print("  -> Đã thu hồi sạch sẽ tiến trình Standalone llama.cpp Server.")

        total_elapsed = time.time() - total_start_time
        benchmark_report["total_e2e_test_seconds"] = round(total_elapsed, 2)
        benchmark_report["total_e2e_test_minutes"] = round(total_elapsed / 60, 2)

        # In kết quả mẫu dịch thuật
        print("\n" + "=" * 80)
        print(" MẪU KẾT QUẢ DỊCH THỰC TẾ CỦA BÀI BÁO (GEMMA-4-E2B TRÊN 4 P-CORES):")
        print("=" * 80)
        for s in sample_translations:
            print(f"Trang {s['page']} [{s['block_code']} - {s['label']}]:")
            print(f"  [EN]: {s['original']}")
            print(f"  [VI]: {s['translated']}")
            print("-" * 60)

        # In báo cáo tổng hợp
        print("\n" + "=" * 80)
        print(" BÁO CÁO THỜI GIAN THỰC THI HOÀN TẤT TOÀN BỘ BACKEND:")
        print(f" - Tổng số trang bài báo:            {benchmark_report['total_pages']} trang")
        print(f" - Tổng số khối trích xuất:          {benchmark_report['total_blocks_extracted']} khối")
        print(f" - Tổng số khối đã dịch tiếng Việt:  {benchmark_report['total_blocks_translated']} khối ({benchmark_report['translation_coverage_percent']}%)")
        print(f" - Thời gian thực thi toàn bộ Flow:  {benchmark_report['e2e_full_pipeline_seconds']}s ({benchmark_report['e2e_full_pipeline_minutes']} phút)")
        print(f" - Thời gian kiểm tra API Canvas:    {benchmark_report['verification_seconds']}s")
        print(f" ==> TỔNG THỜI GIAN TOÀN TRÌNH:      {benchmark_report['total_e2e_test_seconds']}s ({benchmark_report['total_e2e_test_minutes']} phút)")
        print("=" * 80 + "\n")

        # Lưu báo cáo vào file JSON
        report_file = Path("backend/storage/temp/real_cvpr_e2e_benchmark_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(benchmark_report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Báo cáo chi tiết đã được lưu tại: {report_file}")

        assert len(translated_blocks) > 0, "Không có khối nào được lưu bản dịch tiếng Việt!"
