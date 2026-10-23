from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.models.ocr_block import OcrBlockModel
from app.services.translation.adaptive_batcher import AdaptiveBatcher
from app.services.translation.llama_service import LlamaCppService


class TestLlamaCppService:
    def setup_method(self):
        LlamaCppService.reset()

    def teardown_method(self):
        LlamaCppService.reset()

    def test_hard_ram_ceiling_violation_raises_error(self):
        """Kiểm tra rào chắn trần cứng: Cấm n_ctx > 16384 (<= 4.0GB RAM)."""
        with pytest.raises(ValueError, match="vượt quá giới hạn trần cứng"):
            LlamaCppService(n_ctx=32768)

    def test_missing_model_file_raises_filenotfound(self, tmp_path):
        """Kiểm tra xử lý lỗi an toàn khi không tìm thấy tệp mô hình GGUF."""
        fake_path = tmp_path / "non_existent_model.gguf"
        with pytest.raises(FileNotFoundError, match="Không tìm thấy tệp mô hình GGUF"):
            LlamaCppService(model_path=fake_path, n_ctx=4096)

    @patch("llama_cpp.Llama")
    def test_singleton_initialization_and_unload(self, mock_llama_cls, tmp_path):
        """Kiểm tra mô hình Singleton và thu hồi bộ nhớ qua unload()."""
        mock_model_file = tmp_path / "test_model.gguf"
        mock_model_file.write_text("dummy")

        mock_instance = MagicMock()
        mock_llama_cls.return_value = mock_instance

        # Lần gọi 1
        service1 = LlamaCppService.get_instance(model_path=mock_model_file, n_ctx=8192)
        assert service1.is_loaded is True

        # Lần gọi 2 phải trả về cùng một instance (Singleton)
        service2 = LlamaCppService.get_instance(model_path=mock_model_file, n_ctx=8192)
        assert service1 is service2
        assert mock_llama_cls.call_count == 1

        # Thu hồi tài nguyên
        service1.unload()
        assert service1.is_loaded is False
        assert LlamaCppService._instance is None


class TestAdaptiveBatcher:
    def test_batching_groups_blocks_correctly(self):
        """Kiểm tra gom lô thích ứng từ 6 đến 8 khối và giới hạn token."""
        batcher = AdaptiveBatcher(max_blocks_per_batch=6, min_blocks_per_batch=3, max_tokens_per_batch=100)
        
        blocks = [
            OcrBlockModel(
                id=f"b_{i}",
                session_id="s1",
                page_id="p1",
                page_number=1,
                block_code=f"BLK_{i:04d}",
                reading_order=i,
                label="text",
                bbox_x0=0.0,
                bbox_y0=0.0,
                bbox_x1=1.0,
                bbox_y1=1.0,
                is_translatable=True,
                original_text=f"This is test paragraph number {i} with some content.",
            )
            for i in range(15)
        ]

        batches = batcher.create_batches(blocks)
        assert len(batches) >= 2
        for b in batches:
            assert len(b) <= 6

    def test_parse_response_with_missing_block_fallback(self):
        """Kiểm tra bóc tách Regex và phát hiện khối bị sót để kích hoạt Fallback."""
        batcher = AdaptiveBatcher()

        blocks = [
            OcrBlockModel(
                id="1", session_id="s", page_id="p", page_number=1, block_code="BLK_0001",
                reading_order=1, label="text", bbox_x0=0, bbox_y0=0, bbox_x1=1, bbox_y1=1,
                is_translatable=True, original_text="Hello world"
            ),
            OcrBlockModel(
                id="2", session_id="s", page_id="p", page_number=1, block_code="BLK_0002",
                reading_order=2, label="text", bbox_x0=0, bbox_y0=0, bbox_x1=1, bbox_y1=1,
                is_translatable=True, original_text="Deep learning"
            ),
            OcrBlockModel(
                id="3", session_id="s", page_id="p", page_number=1, block_code="BLK_0003",
                reading_order=3, label="text", bbox_x0=0, bbox_y0=0, bbox_x1=1, bbox_y1=1,
                is_translatable=True, original_text="Missing translation"
            ),
        ]

        # Model chỉ sinh BLK_0001 và BLK_0002, bỏ quên BLK_0003
        model_output = "[[BLK_0001]]\nXin chào thế giới\n\n[[BLK_0002]]\nHọc sâu"

        translated_map, missing = batcher.parse_response(model_output, blocks)

        assert translated_map["BLK_0001"] == "Xin chào thế giới"
        assert translated_map["BLK_0002"] == "Học sâu"
        assert len(missing) == 1
        assert missing[0].block_code == "BLK_0003"

    def test_batching_scientific_paper_strictly_under_5_batches(self):
        """Kiểm tra gom lô bài báo khoa học 120 khối (~4000 tokens) luôn nằm trong khoảng 2-4 batch, không quá 5 batch."""
        batcher = AdaptiveBatcher(max_batches=5, max_tokens_per_batch=3500)

        # Giả lập 120 khối văn bản của 1 bài báo khoa học 11 trang
        blocks = [
            OcrBlockModel(
                id=f"blk_{i}",
                session_id="s1",
                page_id="p1",
                page_number=1 + (i // 15),
                block_code=f"BLK_{i:04d}",
                reading_order=i,
                label="text",
                bbox_x0=0.0,
                bbox_y0=0.0,
                bbox_x1=0.5,
                bbox_y1=1.0,
                is_translatable=True,
                original_text="Deep convolutional neural network architectures demonstrate state-of-the-art accuracy on computer vision benchmarks with residual connections." * 2,
            )
            for i in range(120)
        ]

        batches = batcher.create_batches(blocks)
        # Số batch phải <= 5 (tối ưu 2-4 batch), không được phân mảnh thành 27 batch
        assert len(batches) <= 5
        assert len(batches) >= 2
        # Tất cả các khối đều được bao gồm
        total_batched_blocks = sum(len(b) for b in batches)
        assert total_batched_blocks == 120

    def test_smart_filter_skips_references_and_watermarks(self):
        """Kiểm tra logic lọc thông minh: Bỏ qua watermark rác và toàn bộ mục References."""
        from app.services.translation.gemini_translator import GeminiTranslator

        translator = GeminiTranslator()
        blocks = [
            OcrBlockModel(
                id="1", session_id="s", page_id="p", page_number=1, block_code="BLK_0001",
                reading_order=1, label="page header", bbox_x0=0, bbox_y0=0, bbox_x1=1, bbox_y1=0.05,
                is_translatable=True, original_text="arXiv:2305.12345v1 [cs.CV] 19 May 2023"
            ),
            OcrBlockModel(
                id="2", session_id="s", page_id="p", page_number=1, block_code="BLK_0002",
                reading_order=2, label="title", bbox_x0=0, bbox_y0=0.1, bbox_x1=1, bbox_y1=0.2,
                is_translatable=True, original_text="Attention Is All You Need"
            ),
            OcrBlockModel(
                id="3", session_id="s", page_id="p", page_number=1, block_code="BLK_0003",
                reading_order=3, label="text", bbox_x0=0, bbox_y0=0.2, bbox_x1=1, bbox_y1=0.3,
                is_translatable=True, original_text="The dominant sequence transduction models are based on complex recurrent networks."
            ),
            OcrBlockModel(
                id="4", session_id="s", page_id="p", page_number=2, block_code="BLK_0004",
                reading_order=4, label="section header", bbox_x0=0, bbox_y0=0.1, bbox_x1=1, bbox_y1=0.15,
                is_translatable=True, original_text="References"
            ),
            OcrBlockModel(
                id="5", session_id="s", page_id="p", page_number=2, block_code="BLK_0005",
                reading_order=5, label="text", bbox_x0=0, bbox_y0=0.15, bbox_x1=1, bbox_y1=0.3,
                is_translatable=True, original_text="[1] J. Smith, Modern Deep Learning, 2021."
            ),
            OcrBlockModel(
                id="6", session_id="s", page_id="p", page_number=2, block_code="BLK_0006",
                reading_order=6, label="text", bbox_x0=0, bbox_y0=0.3, bbox_x1=1, bbox_y1=0.45,
                is_translatable=True, original_text="[2] A. Vaswani et al., NIPS 2017."
            ),
        ]

        translator.apply_smart_filter(blocks)

        # BLK_0001 (watermark/header): is_translatable = False
        assert blocks[0].is_translatable is False
        # BLK_0002 (title): is_translatable = True
        assert blocks[1].is_translatable is True
        # BLK_0003 (core text): is_translatable = True
        assert blocks[2].is_translatable is True
        # BLK_0004 (references header): is_translatable = False
        assert blocks[3].is_translatable is False
        # BLK_0005 & BLK_0006 (references items): is_translatable = False
        assert blocks[4].is_translatable is False
        assert blocks[5].is_translatable is False


@pytest.mark.asyncio
class TestSystemEngineAPI:
    async def test_get_engine_status(self):
        """Kiểm tra endpoint GET /api/v1/system/engine-status trả về đúng thông số."""
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/system/engine-status")
            assert resp.status_code == 200
            data = resp.json()
            assert "active_provider" in data
            assert data["hard_ram_ceiling_gb"] == 4.0
            assert "estimated_ram_usage_gb" in data

    async def test_engine_switch_validation(self):
        """Kiểm tra validation khi chuyển đổi engine."""
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Chuyển sang provider không hợp lệ
            resp_invalid = await client.post("/api/v1/system/engine-switch", json={"provider": "invalid_engine"})
            assert resp_invalid.status_code == 400

            # 2. Vượt quá trần cứng 16384 context
            resp_overflow = await client.post(
                "/api/v1/system/engine-switch",
                json={"provider": "llama_cpp", "context_window": 32000},
            )
            assert resp_overflow.status_code == 400
            assert "vượt quá giới hạn trần cứng" in resp_overflow.json()["detail"]

            # 3. Chuyển sang Gemini thành công
            resp_gemini = await client.post("/api/v1/system/engine-switch", json={"provider": "gemini"})
            assert resp_gemini.status_code == 200
            assert resp_gemini.json()["active_provider"] == "gemini"
            assert resp_gemini.json()["is_local"] is False

            # 4. Chuyển về Local LLM (nếu có file model Qwen3 có sẵn trong storage/models)
            resp_local = await client.post(
                "/api/v1/system/engine-switch",
                json={"provider": "llama_cpp", "context_window": 8192},
            )
            assert resp_local.status_code == 200
            assert resp_local.json()["active_provider"] == "llama_cpp"
            assert resp_local.json()["is_local"] is True
            assert resp_local.json()["context_window"] == 8192
