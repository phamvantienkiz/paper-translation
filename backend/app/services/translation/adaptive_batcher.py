import re

from app.models.ocr_block import OcrBlockModel
from app.services.translation.glossary import build_system_instruction


class AdaptiveBatcher:
    """
    Bộ đóng gói phân lô thích ứng (Adaptive Batching) và bóc tách bản dịch bảo toàn mã khối:
    - Gom nhóm các khối văn bản (6–8 khối / ~1,500 tokens).
    - Bảo toàn định dạng mã khối [[BLK_XXXX]], công thức LaTeX $..$, và bảng biểu <table>.
    - Bóc tách bản dịch qua Regex và tự động kích hoạt Fallback đơn lẻ nếu thiếu khối.
    """

    BLOCK_REGEX = re.compile(r"\[\[(BLK_\d+)\]\]\s*([\s\S]*?)(?=(?:\[\[BLK_\d+\]\]|$))")

    def __init__(
        self,
        max_blocks_per_batch: int = 8,
        min_blocks_per_batch: int = 4,
        max_tokens_per_batch: int = 1500,
    ):
        self.max_blocks_per_batch = max_blocks_per_batch
        self.min_blocks_per_batch = min_blocks_per_batch
        self.max_tokens_per_batch = max_tokens_per_batch

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Ước tính số lượng token sơ bộ (1 token ~= 4 ký tự tiếng Anh)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def create_batches(self, blocks: list[OcrBlockModel]) -> list[list[OcrBlockModel]]:
        """
        Gom danh sách khối thành các batch thích ứng theo số lượng và dung lượng token:
        - Mỗi batch từ 6-8 khối (tối thiểu 1 nếu không còn khối).
        - Tổng số token ước lượng của batch không vượt quá max_tokens_per_batch (~1500).
        """
        batches: list[list[OcrBlockModel]] = []
        current_batch: list[OcrBlockModel] = []
        current_tokens = 0

        for block in blocks:
            b_tokens = self.estimate_tokens(block.original_text or "")
            
            # Nếu thêm block này làm vượt quá số khối tối đa hoặc vượt quá giới hạn token
            if current_batch and (
                len(current_batch) >= self.max_blocks_per_batch
                or (current_tokens + b_tokens > self.max_tokens_per_batch and len(current_batch) >= self.min_blocks_per_batch)
            ):
                batches.append(current_batch)
                current_batch = [block]
                current_tokens = b_tokens
            else:
                current_batch.append(block)
                current_tokens += b_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    def build_prompt_messages(self, batch: list[OcrBlockModel]) -> list[dict[str, str]]:
        """
        Tạo messages ChatML chuẩn cho mô hình Qwen3.
        """
        system_content = (
            build_system_instruction()
            + "\n\nQUY TẮC BẮT BUỘC:\n"
            + "1. Bản dịch tiếng Việt BẮT BUỘC giữ nguyên chính xác các thẻ mã khối dạng [[BLK_XXXX]].\n"
            + "2. Giữ nguyên vẹn 100% công thức toán học LaTeX ($...$, $$...$$) và thẻ cấu trúc HTML (<table>, <tr>, <td>).\n"
            + "3. Chỉ trả về kết quả dịch theo đúng định dạng mã khối [[BLK_XXXX]], không thêm lời mở đầu hay kết luận."
        )

        user_content_lines = []
        for b in batch:
            text = (b.original_text or "").strip()
            user_content_lines.append(f"[[{b.block_code}]]\n{text}")

        user_content = "\n\n".join(user_content_lines)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_single_fallback_messages(self, block: OcrBlockModel) -> list[dict[str, str]]:
        """
        Tạo messages Fallback cho 1 khối đơn lẻ khi batch trước đó bị sót.
        """
        system_content = (
            build_system_instruction()
            + f"\n\nBẮT BUỘC: Dịch nội dung của khối [[{block.block_code}]] sang tiếng Việt. "
            + f"Bắt đầu phản hồi bằng [[{block.block_code}]] kèm nội dung dịch. Giữ nguyên công thức toán học và bảng biểu."
        )
        user_content = f"[[{block.block_code}]]\n{(block.original_text or '').strip()}"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def parse_response(
        self, response_text: str, expected_batch: list[OcrBlockModel]
    ) -> tuple[dict[str, str], list[OcrBlockModel]]:
        """
        Bóc tách các mã khối [[BLK_XXXX]] từ phản hồi của mô hình.
        Trả về:
        - translated_map: {block_code: translated_text}
        - missing_blocks: Danh sách các khối bị thiếu trong phản hồi để kích hoạt fallback.
        """
        translated_map: dict[str, str] = {}
        for match in self.BLOCK_REGEX.finditer(response_text):
            code = match.group(1).strip()
            content = match.group(2).strip()
            if content:
                translated_map[code] = content

        missing_blocks: list[OcrBlockModel] = []
        for b in expected_batch:
            if b.block_code not in translated_map or not translated_map[b.block_code].strip():
                missing_blocks.append(b)

        return translated_map, missing_blocks
