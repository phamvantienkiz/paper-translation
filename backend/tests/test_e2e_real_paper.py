from pathlib import Path

import pytest

from app.models.ocr_block import OcrBlockModel
from app.services.parser.indra_ocr_service import IndraOcrService
from app.services.translation.adaptive_batcher import AdaptiveBatcher

REAL_PAPER_PATH = Path("storage/raw_pdfs/Feijoo_DarkIR_Robust_Low-Light_Image_Restoration_CVPR_2025_paper.pdf")


@pytest.fixture(scope="module")
def parsed_doc():
    """Phân tích bài báo thực tế một lần cho toàn bộ module test."""
    ocr = IndraOcrService()
    return ocr.parse_pdf(REAL_PAPER_PATH)


@pytest.mark.skipif(not REAL_PAPER_PATH.exists(), reason="Tệp bài báo thực tế CVPR 2025 không tồn tại.")
class TestRealPaperE2E:

    def test_real_paper_page_count_and_figures(self, parsed_doc):
        """Kiểm tra nhận diện đúng 11 trang và bóc tách được các khối hình vẽ."""
        assert parsed_doc.total_pages == 11
        assert len(parsed_doc.pages) == 11

        figure_blocks = [b for b in parsed_doc.blocks if b.label == "figure"]
        assert len(figure_blocks) >= 1, "Phải trích xuất được ít nhất 1 khối hình vẽ từ bài báo thực tế"

    def test_real_paper_references_exclusion(self, parsed_doc):
        """Kiểm tra loại trừ 100% mục References (từ Trang 9 đến Trang 11)."""
        # Trang 9 đến 11 chứa toàn bộ danh mục tài liệu tham khảo [1]..[56]
        ref_page_blocks = [b for b in parsed_doc.blocks if b.page_number >= 9]
        assert len(ref_page_blocks) >= 3

        # Đảm bảo không có khối nào ở trang References bị đưa vào danh sách dịch
        translatable_on_ref_pages = [b for b in ref_page_blocks if b.is_translatable]
        assert len(translatable_on_ref_pages) == 0, (
            f"Phát hiện {len(translatable_on_ref_pages)} khối trên trang References vẫn bị gắn cờ is_translatable=True"
        )

    def test_real_paper_batching_strictly_under_limit(self, parsed_doc):
        """Kiểm tra gom lô bài báo 11 trang thực tế chỉ phân bổ vào 2 - 4 batch (tối đa 5-7 batch), mỗi batch <= 2500 từ."""
        batcher = AdaptiveBatcher()

        db_blocks = [
            OcrBlockModel(
                id=f"b_{b.block_code}",
                session_id="real_test",
                page_id=f"p_{b.page_number}",
                page_number=b.page_number,
                block_code=b.block_code,
                reading_order=b.reading_order,
                label=b.label,
                bbox_x0=b.bbox_norm[0],
                bbox_y0=b.bbox_norm[1],
                bbox_x1=b.bbox_norm[2],
                bbox_y1=b.bbox_norm[3],
                is_translatable=b.is_translatable,
                original_text=b.text,
            )
            for b in parsed_doc.blocks
        ]

        translatable = [b for b in db_blocks if b.is_translatable and (b.original_text or "").strip()]
        batches = batcher.create_batches(translatable)

        # Số batch phải tối ưu trong khoảng 2 - 4 batch (tối đa 5 - 7 batch)
        assert len(batches) <= 5, f"Số batch ({len(batches)}) vượt quá giới hạn tối đa 5 batch"
        assert len(batches) >= 2, f"Số batch ({len(batches)}) quá ít so với dung lượng bài báo"

        for b in batches:
            words = sum(batcher.count_words(x.original_text or "") for x in b)
            assert words <= 2500, f"Một batch chứa {words} từ, vượt quá trần 2500 từ"

    def test_real_paper_prompt_structure(self, parsed_doc):
        """Kiểm tra cấu trúc Prompt chuẩn ChatML cho Batch 1 bảo toàn các khối."""
        batcher = AdaptiveBatcher()
        db_blocks = [
            OcrBlockModel(
                id=f"b_{b.block_code}",
                session_id="real_test",
                page_id=f"p_{b.page_number}",
                page_number=b.page_number,
                block_code=b.block_code,
                reading_order=b.reading_order,
                label=b.label,
                bbox_x0=b.bbox_norm[0],
                bbox_y0=b.bbox_norm[1],
                bbox_x1=b.bbox_norm[2],
                bbox_y1=b.bbox_norm[3],
                is_translatable=b.is_translatable,
                original_text=b.text,
            )
            for b in parsed_doc.blocks
        ]

        translatable = [b for b in db_blocks if b.is_translatable and (b.original_text or "").strip()]
        batches = batcher.create_batches(translatable)
        batch_1 = batches[0]

        messages = batcher.build_prompt_messages(batch_1)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "STRICT INVARIANTS" in messages[0]["content"]

        user_content = messages[1]["content"]
        for block in batch_1:
            assert f"[[{block.block_code}]]" in user_content
