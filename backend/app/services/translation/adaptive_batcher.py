import math
import re

from app.models.ocr_block import OcrBlockModel
from app.services.translation.glossary import build_system_instruction


class AdaptiveBatcher:
    """
    Bộ đóng gói phân lô thích ứng (Adaptive Batching) và bóc tách bản dịch bảo toàn mã khối:
    - Gom nhóm văn bản thông minh hướng ngưỡng <= 5 batch (tối ưu 2–4 batch).
    - Tính toán ngân sách token đầu vào (~3,500 token/batch) tối ưu cho ngữ cảnh 8K (n_ctx=8192).
    - Thiết kế prompt theo kỹ thuật Prompt Engineering bảo toàn mã khối [[BLK_XXXX]], LaTeX $..$, và bảng.
    - Bóc tách bản dịch qua Regex và tự động kích hoạt Fallback đơn lẻ nếu thiếu khối.
    """

    BLOCK_REGEX = re.compile(r"\[\[(BLK_\d+)\]\]\s*([\s\S]*?)(?=(?:\[\[BLK_\d+\]\]|$))")

    def __init__(
        self,
        max_batches: int = 7,
        max_tokens_per_batch: int = 1600,
        max_blocks_per_batch: int = 25,
        min_blocks_per_batch: int = 4,
    ):
        self.max_batches = max_batches
        self.max_tokens_per_batch = max_tokens_per_batch
        self.max_blocks_per_batch = max_blocks_per_batch
        self.min_blocks_per_batch = min_blocks_per_batch

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Ước tính số lượng token sơ bộ (1 token ~= 4 ký tự tiếng Anh)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def create_batches(self, blocks: list[OcrBlockModel]) -> list[list[OcrBlockModel]]:
        """
        Gom danh sách khối thành các batch thích ứng hướng ngưỡng <= 5 batch:
        - Đếm tổng token T của toàn bộ các khối cần dịch.
        - Phân bổ thành 1 đến 5 batch sao cho mỗi batch cân bằng và không vượt quá ngân sách context 8K.
        """
        if not blocks:
            return []

        total_tokens = sum(self.estimate_tokens(b.original_text or "") for b in blocks)

        # Tính toán số lượng batch mục tiêu
        if total_tokens <= self.max_tokens_per_batch:
            target_batches = 1
        elif total_tokens <= self.max_tokens_per_batch * 2:
            target_batches = 2
        elif total_tokens <= self.max_tokens_per_batch * 3:
            target_batches = 3
        elif total_tokens <= self.max_tokens_per_batch * 4:
            target_batches = 4
        else:
            target_batches = min(
                self.max_batches,
                max(1, math.ceil(total_tokens / self.max_tokens_per_batch)),
            )

        # Đảm bảo không nhiều batch hơn số khối
        target_batches = max(1, min(target_batches, len(blocks)))

        tokens_per_batch_target = math.ceil(total_tokens / target_batches)

        batches: list[list[OcrBlockModel]] = []
        current_batch: list[OcrBlockModel] = []
        current_tokens = 0

        for block in blocks:
            b_tokens = self.estimate_tokens(block.original_text or "")

            # Điều kiện chuyển batch:
            # 1. Đã có khối trong batch hiện tại
            # 2. Vẫn còn slot batch (chưa đạt target_batches)
            # 3. Hoặc batch hiện tại đã đạt mục tiêu token, hoặc vượt quá số khối tối đa
            reach_max_blocks = len(current_batch) >= self.max_blocks_per_batch
            reach_token_ceiling = current_tokens + b_tokens > self.max_tokens_per_batch
            balanced_split = (
                len(batches) < target_batches - 1
                and current_tokens + b_tokens > tokens_per_batch_target
            )

            should_split = len(current_batch) > 0 and (
                reach_max_blocks or reach_token_ceiling or balanced_split
            )

            if should_split:
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
        Tạo messages ChatML chuẩn cho mô hình Qwen3 theo kỹ thuật Prompt Engineering:
        - Định danh Persona chuyên gia dịch thuật bài báo khoa học chuẩn quốc tế.
        - Phân định rõ ràng Quy tắc Bảo tồn (Strict Invariants): mã [[BLK_XXXX]], LaTeX, HTML table.
        - Chỉ dẫn ngữ phong học thuật chuẩn mực, súc tích, tự nhiên trong tiếng Việt.
        - Đầu ra thuần Markdown bám sát từng khối, loại bỏ hoàn toàn lời dẫn / giải thích.
        """
        glossary_rules = build_system_instruction()

        system_content = (
            "Bạn là một chuyên gia dịch thuật bài báo khoa học chuẩn quốc tế, có kiến thức sâu rộng về Khoa học Máy tính, Trí tuệ Nhân tạo và Kỹ thuật.\n"
            "Nhiệm vụ của bạn là dịch chính xác toàn bộ các khối văn bản học thuật từ tiếng Anh sang tiếng Việt học thuật chuẩn mực, lưu loát và tự nhiên.\n\n"
            "### QUY TẮC BẮT BUỘC (STRICT INVARIANTS):\n"
            "1. BẢO TOÀN ĐỊNH DANH KHỐI: Mỗi khối bắt đầu bằng định danh chính xác dạng [[BLK_XXXX]]. Giữ nguyên 100% tất cả các mã [[BLK_XXXX]] theo đúng thứ tự xuất hiện.\n"
            "2. BẢO TOÀN CÔNG THỨC TOÁN HỌC: Giữ nguyên vẹn 100% mọi công thức LaTeX inline ($...$), display ($$...$$ hoặc \\[...\\]) và ký hiệu toán học. Tuyệt đối không dịch hoặc làm biến dạng công thức toán.\n"
            "3. BẢO TOÀN CẤU TRÚC BẢNG & MÃ: Giữ nguyên cấu trúc bảng HTML (<table>, <tr>, <td>) hoặc bảng Markdown, mã nguồn, URL và số liệu đo đạc.\n"
            "4. THUẬT NGỮ CHUYÊN NGÀNH: Dịch tự nhiên sang tiếng Việt chuyên ngành, nhưng giữ nguyên các thuật ngữ tiếng Anh chuẩn quốc tế phổ biến không cần dịch (ví dụ: Transformer, Attention, Self-Attention, Fine-tuning, Token, Embedding, Backbone, Loss function, Dataset, Benchmark, Bounding Box, v.v.).\n"
            "5. ĐỊNH DẠNG ĐẦU RA: Chỉ trả về nội dung dịch dưới dạng Markdown bọc trong các mã [[BLK_XXXX]]. Tuyệt đối KHÔNG viết lời chào, lời mở đầu, giải thích hay kết luận.\n\n"
            f"### HƯỚNG DẪN THUẬT NGỮ DỰ ÁN:\n{glossary_rules}"
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
            "Bạn là chuyên gia dịch thuật bài báo khoa học. "
            f"BẮT BUỘC: Dịch nội dung của khối [[{block.block_code}]] sang tiếng Việt học thuật lưu loát. "
            f"Bắt đầu phản hồi bằng [[{block.block_code}]] kèm nội dung dịch. "
            "Giữ nguyên 100% công thức LaTeX ($...$, $$...$$), bảng biểu và không thêm bất kỳ lời dẫn nào."
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
