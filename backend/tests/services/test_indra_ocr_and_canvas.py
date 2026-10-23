import pytest

from app.models.ocr_block import OcrBlockModel
from app.services.parser.indra_ocr_service import IndraOcrService, normalize_bbox
from app.services.translation.gemini_translator import GeminiTranslator
from app.services.translation.translator import MockTranslator


def test_normalize_bbox():
    # Kiểm tra chuẩn hóa Bounding Box trong khoảng [0.0, 1.0]
    box = [50.0, 100.0, 250.0, 300.0]
    w, h = 500.0, 1000.0
    x0, y0, x1, y1 = normalize_bbox(box, w, h)
    assert x0 == 0.1
    assert y0 == 0.1
    assert x1 == 0.5
    assert y1 == 0.3

    # Kiểm tra trường hợp tọa độ vượt biên hoặc đảo ngược
    box_inverted = [300.0, 400.0, 100.0, 200.0]
    x0, y0, x1, y1 = normalize_bbox(box_inverted, w, h)
    assert x0 <= x1
    assert y0 <= y1
    assert 0.0 <= x0 <= 1.0
    assert 0.0 <= y1 <= 1.0


def test_smart_filter_references_and_headers():
    translator = GeminiTranslator()

    blocks = [
        OcrBlockModel(
            id="1",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0001",
            reading_order=0,
            label="page header",
            bbox_x0=0.1,
            bbox_y0=0.02,
            bbox_x1=0.9,
            bbox_y1=0.05,
            is_translatable=True,
            original_text="Conference on Neural Information Processing Systems",
        ),
        OcrBlockModel(
            id="2",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0002",
            reading_order=1,
            label="title",
            bbox_x0=0.1,
            bbox_y0=0.1,
            bbox_x1=0.9,
            bbox_y1=0.15,
            is_translatable=True,
            original_text="Attention Is All You Need",
        ),
        OcrBlockModel(
            id="3",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0003",
            reading_order=2,
            label="figure",
            bbox_x0=0.1,
            bbox_y0=0.2,
            bbox_x1=0.5,
            bbox_y1=0.4,
            is_translatable=True,
            original_text="",
        ),
        OcrBlockModel(
            id="4",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0004",
            reading_order=3,
            label="section header",
            bbox_x0=0.1,
            bbox_y0=0.5,
            bbox_x1=0.5,
            bbox_y1=0.55,
            is_translatable=True,
            original_text="References",
        ),
        OcrBlockModel(
            id="5",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0005",
            reading_order=4,
            label="text",
            bbox_x0=0.1,
            bbox_y0=0.56,
            bbox_x1=0.9,
            bbox_y1=0.65,
            is_translatable=True,
            original_text="Vaswani et al. Attention is all you need. NeurIPS 2017.",
        ),
    ]

    translator.apply_smart_filter(blocks)

    # 1. page header bị loại trừ
    assert blocks[0].is_translatable is False
    # 2. title cần dịch
    assert blocks[1].is_translatable is True
    # 3. figure không dịch chữ
    assert blocks[2].is_translatable is False
    # 4. Tiêu đề References và toàn bộ tài liệu tham khảo phía sau không dịch
    assert blocks[3].is_translatable is False
    assert blocks[4].is_translatable is False


def test_pack_and_parse_blocks():
    translator = GeminiTranslator()

    blocks = [
        OcrBlockModel(
            id="1",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0001",
            reading_order=0,
            label="title",
            bbox_x0=0.1,
            bbox_y0=0.1,
            bbox_x1=0.9,
            bbox_y1=0.15,
            is_translatable=True,
            original_text="Attention Is All You Need",
        ),
        OcrBlockModel(
            id="2",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0002",
            reading_order=1,
            label="text",
            bbox_x0=0.1,
            bbox_y0=0.2,
            bbox_x1=0.9,
            bbox_y1=0.3,
            is_translatable=True,
            original_text="We propose the Transformer architecture.",
        ),
    ]

    packed = translator.pack_blocks(blocks)
    assert "[[BLK_0001]]\nAttention Is All You Need" in packed
    assert "[[BLK_0002]]\nWe propose the Transformer architecture." in packed

    simulated_gemini_output = (
        "[[BLK_0001]]\nCơ Chế Chú Ý Là Tất Cả Những Gì Bạn Cần\n\n"
        "[[BLK_0002]]\nChúng tôi đề xuất kiến trúc Transformer."
    )
    parsed = translator.parse_translated_text(simulated_gemini_output)
    assert parsed["BLK_0001"] == "Cơ Chế Chú Ý Là Tất Cả Những Gì Bạn Cần"
    assert parsed["BLK_0002"] == "Chúng tôi đề xuất kiến trúc Transformer."


@pytest.mark.asyncio
async def test_mocked_gemini_single_call(monkeypatch):
    """
    Kiểm thử pipeline dịch thuật với MOCK Gemini API.
    Tuyệt đối không gọi tới API Gemini thật sự theo chỉ dẫn.
    """
    mock_translator = MockTranslator()
    translator = GeminiTranslator(translator=mock_translator)

    blocks = [
        OcrBlockModel(
            id="b1",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0001",
            reading_order=0,
            label="title",
            bbox_x0=0.1,
            bbox_y0=0.1,
            bbox_x1=0.9,
            bbox_y1=0.15,
            is_translatable=True,
            original_text="Introduction to Deep Learning",
        ),
        OcrBlockModel(
            id="b2",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0002",
            reading_order=1,
            label="text",
            bbox_x0=0.1,
            bbox_y0=0.2,
            bbox_x1=0.9,
            bbox_y1=0.3,
            is_translatable=True,
            original_text="We evaluate the performance of our model.",
        ),
    ]

    result = await translator.translate_blocks(blocks)
    assert "BLK_0001" in result
    assert "BLK_0002" in result
    assert "Giới thiệu" in result["BLK_0001"]
    assert "đánh giá" in result["BLK_0002"]


def test_hardware_resource_cleanup():
    """
    Kiểm thử cơ chế thu hồi tài nguyên phần cứng (RAM, CPU ThreadPool):
    - Khi hoàn tất OCR hoặc khi tác vụ kết thúc, hàm unload() phải được gọi.
    - Toàn bộ worker threads trong ThreadPool phải được dừng ngay lập tức.
    - Toàn bộ tham chiếu InferenceSession phải được xóa để giải phóng RAM.
    """
    ocr_service = IndraOcrService()

    # Mô phỏng đối tượng converter có worker pool và inference sessions
    class DummyPool:
        def __init__(self):
            self.shutdown_called = False

        def shutdown(self, wait=False, cancel_futures=True):
            self.shutdown_called = True

    class DummyOcr:
        def __init__(self):
            self.pool = DummyPool()
            self.det = "onnx_session_det"
            self.rec = "onnx_session_rec"
            self.groups = {"group1": "sess"}
            self.lms = {1: "lm"}

    class DummyConverter:
        def __init__(self):
            self.ocr = DummyOcr()

    ocr_service._converter = DummyConverter()
    ocr_service._init_attempted = True

    # Kích hoạt thu hồi tài nguyên
    ocr_service.unload()

    # Xác minh giải phóng tài nguyên
    assert ocr_service._converter is None
    assert ocr_service._init_attempted is False

    # Kiểm tra hỗ trợ context manager (with)
    with IndraOcrService() as svc:
        svc._converter = DummyConverter()
    assert svc._converter is None


def test_local_model_endpoint_normalization(monkeypatch):
    from app.core.config import Settings

    # 1. Ollama port 11434
    s_ollama = Settings(LLM_API_BASE="http://localhost:11434")
    assert s_ollama.normalized_llm_endpoint == "http://localhost:11434/v1/chat/completions"
    assert s_ollama.is_local_provider is True

    # 2. LM Studio port 1234
    s_lms = Settings(LLM_API_BASE="http://localhost:1234/v1")
    assert s_lms.normalized_llm_endpoint == "http://localhost:1234/v1/chat/completions"
    assert s_lms.is_local_provider is True

    # 3. Llama.cpp port 8080
    s_llama = Settings(LLM_API_BASE="http://localhost:8080")
    assert s_llama.normalized_llm_endpoint == "http://localhost:8080/v1/chat/completions"
    assert s_llama.is_local_provider is True

    # 4. Self-hosted custom server
    s_self = Settings(LLM_API_BASE="http://192.168.1.100:8000/v1", LLM_PROVIDER="self_hosted")
    assert s_self.normalized_llm_endpoint == "http://192.168.1.100:8000/v1/chat/completions"
    assert s_self.is_local_provider is True


@pytest.mark.asyncio
async def test_translation_callback_and_retries(monkeypatch):
    """
    Kiểm thử cơ chế Callback thời gian thực và Retry khi gặp sự cố mạng/máy chủ.
    Sử dụng Mock đối với httpx để không gọi API thật sự.
    """
    from unittest.mock import MagicMock

    import httpx

    progress_events = []

    async def on_progress(current: int, total: int, msg: str):
        progress_events.append((current, total, msg))

    translator = GeminiTranslator()

    # Giả lập lần 1 gặp lỗi HTTP 503 (Server Error), lần 2 trả về 200 OK thành công
    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503
    mock_resp_503.text = "Service Temporarily Unavailable"

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "choices": [
            {
                "message": {"content": "[[BLK_0001]]\nBản dịch thành công sau khi thử lại."},
                "finish_reason": "stop",
            }
        ]
    }

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_resp_503
        return mock_resp_200

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", "dummy_mock_key")
    monkeypatch.setattr("app.core.config.settings.LLM_RETRY_DELAY_SECONDS", 0.01)

    blocks = [
        OcrBlockModel(
            id="1",
            session_id="s1",
            page_id="p1",
            page_number=1,
            block_code="BLK_0001",
            reading_order=0,
            label="text",
            bbox_x0=0.1,
            bbox_y0=0.1,
            bbox_x1=0.9,
            bbox_y1=0.2,
            is_translatable=True,
            original_text="English original text.",
        )
    ]

    result = await translator.translate_blocks(blocks, progress_callback=on_progress)
    assert "BLK_0001" in result
    assert result["BLK_0001"] == "Bản dịch thành công sau khi thử lại."
    assert call_count == 2  # Đã thử lại thành công sau lần 1 lỗi
    assert len(progress_events) >= 1

