import asyncio
import inspect
import re
from collections.abc import Callable, Coroutine
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.models.ocr_block import OcrBlockModel
from app.services.translation.glossary import build_system_instruction
from app.services.translation.translator import BaseTranslator, MockTranslator

ProgressCallback = Callable[[int, int, str], Coroutine[Any, Any, None] | None]


class ContextLengthExceededError(Exception):
    """Ngoại lệ khi kích thước prompt vượt quá Context Window của model."""

    pass


class GeminiTranslator:
    """
    Dịch vụ dịch thuật toàn văn chuẩn hóa OpenAI-Compatible (/v1/chat/completions):
    1. Tương thích 100% với Google Gemini, OpenAI ChatGPT, và các mô hình cục bộ
       (Ollama, LM Studio, Llama.cpp, vLLM, self-hosted translation models).
    2. Tự động xử lý sự cố (Retries, Exponential Backoff, Rate Limit 429, Server 5xx, Network Timeout).
    3. Hỗ trợ Callback theo thời gian thực (ProgressCallback) cho giao diện và Server-Sent Events.
    4. Thích ứng kích thước ngữ cảnh (Adaptive Batching): Dịch toàn bài 1 lần (Single-Call)
       với model ngữ cảnh lớn (Gemini 1M) hoặc tự động chia khối thông minh (Chunking) với local models.
    """

    REFERENCES_PATTERN = re.compile(
        r"^(?:[0-9IVX]+\.?\s*)?(?:references|bibliography|tài liệu tham khảo)\b",
        re.IGNORECASE,
    )
    BLOCK_TOKEN_PATTERN = re.compile(
        r"\[\[(BLK_\d{4})\]\]\s*([\s\S]*?)(?=(?:\[\[BLK_\d{4}\]\]|$))"
    )

    def __init__(self, translator: BaseTranslator | None = None):
        self.translator = translator

    def apply_smart_filter(self, blocks: list[OcrBlockModel]) -> None:
        """
        Bộ lọc thông minh:
        - Đánh dấu is_translatable = False cho:
          1. 'page header', 'page footer'
          2. 'figure', 'picture'
          3. Toàn bộ các khối từ tiêu đề 'References' hoặc 'Bibliography' trở đi.
        - Đánh dấu is_translatable = True cho các khối nội dung bài báo khoa học cần dịch.
        """
        in_references = False

        for b in blocks:
            text = (b.original_text or "").strip()
            label = (b.label or "").lower()

            # Kiểm tra tiêu đề bắt đầu mục References / Bibliography
            if not in_references and (
                self.REFERENCES_PATTERN.match(text)
                or (label == "section header" and text.lower() in ("references", "bibliography"))
            ):
                in_references = True
                b.is_translatable = False
                continue

            if in_references:
                b.is_translatable = False
                continue

            if label in ("page header", "page footer", "figure", "picture"):
                b.is_translatable = False
                continue

            if not text:
                b.is_translatable = False
                continue

            b.is_translatable = True

    def pack_blocks(self, blocks: list[OcrBlockModel]) -> str:
        """Đóng gói danh sách khối cần dịch thành chuỗi có cấu trúc [[BLK_XXXX]]."""
        packed_parts: list[str] = []
        for b in blocks:
            if b.is_translatable and b.original_text.strip():
                packed_parts.append(f"[[{b.block_code}]]\n{b.original_text.strip()}")
        return "\n\n".join(packed_parts)

    def parse_translated_text(self, raw_output: str) -> dict[str, str]:
        """Bóc tách chuỗi phản hồi và ánh xạ theo từng mã [[BLK_XXXX]]."""
        result: dict[str, str] = {}
        # Loại bỏ code block formatting nếu model tự bọc ```markdown ... ```
        clean_text = raw_output
        if clean_text.startswith("```") and clean_text.endswith("```"):
            lines = clean_text.splitlines()
            if len(lines) >= 3:
                clean_text = "\n".join(lines[1:-1]).strip()

        matches = self.BLOCK_TOKEN_PATTERN.findall(clean_text)
        for code, content in matches:
            result[code.strip()] = content.strip()
        return result

    def _build_system_prompt(self) -> str:
        base_prompt = build_system_instruction()
        extra_rules = (
            "\n\nBỔ SUNG QUY TẮC BẮT BUỘC CHO BỐ CỤC VĂN BẢN HỌC THUẬT:\n"
            "1. Dữ liệu đầu vào gồm các khối được đánh dấu bằng mã [[BLK_XXXX]].\n"
            "2. BẠN PHẢI GIỮ NGUYÊN 100% CÁC THẺ MÃ [[BLK_XXXX]] TRƯỚC MỖI KHỐI ĐƯỢC DỊCH.\n"
            "3. Tuyệt đối không xóa, không gộp và không sửa đổi bất kỳ ký tự nào trong thẻ [[BLK_XXXX]].\n"
            "4. GIỮ NGUYÊN 100% MỌI CÔNG THỨC TOÁN HỌC LaTeX dạng $...$, $$...$$ hoặc môi trường equation.\n"
            "5. GIỮ NGUYÊN cấu trúc bảng HTML <table>...</table> nếu có."
        )
        return base_prompt + extra_rules

    async def _emit_progress(
        self,
        callback: ProgressCallback | None,
        current: int,
        total: int,
        message: str,
    ) -> None:
        if callback:
            try:
                res = callback(current, total, message)
                if inspect.isawaitable(res):
                    await res
            except Exception as e:
                logger.warning(f"Lỗi khi thực thi callback tiến độ dịch: {e}")

    async def _call_completion_api(
        self,
        prompt_text: str,
        max_tokens: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[str, str]:
        """
        Gọi API Chat Completions chuẩn OpenAI kèm cơ chế Retries và Exponential Backoff.
        Hỗ trợ Gemini, OpenAI, Ollama, LM Studio, Llama.cpp và self-hosted models.
        """
        api_key = settings.effective_api_key
        is_local = settings.is_local_provider
        endpoint = settings.normalized_llm_endpoint

        if not api_key and not is_local:
            logger.info("Chưa cấu hình API Key và không phải Local runtime. Sử dụng MockTranslator.")
            mock_tr = MockTranslator()
            mocked = await mock_tr.translate_text(prompt_text)
            return mocked, "stop"

        target_max_tokens = max_tokens or settings.LLM_MAX_OUTPUT_TOKENS
        system_instruction = self._build_system_prompt()
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": target_max_tokens,
        }

        headers = {"Content-Type": "application/json"}
        if api_key and api_key.lower() not in ("none", "null", ""):
            headers["Authorization"] = f"Bearer {api_key}"

        max_retries = max(1, settings.LLM_MAX_RETRIES)
        retry_delay = max(0.5, settings.LLM_RETRY_DELAY_SECONDS)

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                    res = await client.post(endpoint, json=payload, headers=headers)

                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            choice = choices[0]
                            finish_reason = choice.get("finish_reason", "stop")
                            content = choice.get("message", {}).get("content", "").strip()
                            return content, finish_reason

                    # Xử lý Rate Limit (HTTP 429)
                    if res.status_code == 429:
                        raw_retry = res.headers.get("Retry-After")
                        wait_sec = float(raw_retry) if raw_retry and raw_retry.isdigit() else retry_delay * (2 ** (attempt - 1))
                        msg = f"Đạt giới hạn gọi API (HTTP 429). Đang thử lại lần {attempt}/{max_retries} sau {wait_sec:.1f}s..."
                        logger.warning(f"[{endpoint}] {msg}")
                        await self._emit_progress(progress_callback, 0, 100, msg)
                        await asyncio.sleep(wait_sec)
                        continue

                    # Xử lý lỗi máy chủ tạm thời (HTTP 500, 502, 503, 504)
                    if res.status_code in (500, 502, 503, 504):
                        wait_sec = retry_delay * (2 ** (attempt - 1))
                        msg = f"Máy chủ AI phản hồi HTTP {res.status_code}. Thử lại lần {attempt}/{max_retries} sau {wait_sec:.1f}s..."
                        logger.warning(f"[{endpoint}] {msg}")
                        await self._emit_progress(progress_callback, 0, 100, msg)
                        await asyncio.sleep(wait_sec)
                        continue

                    # Xử lý khi bài báo vượt quá độ dài Context Window của Local Model
                    if res.status_code == 400:
                        err_text = res.text.lower()
                        if any(k in err_text for k in ("context", "token", "length", "too large")):
                            raise ContextLengthExceededError(
                                f"Độ dài bài báo vượt quá giới hạn ngữ cảnh của model: {res.text[:200]}"
                            )

                    logger.warning(f"LLM API [{endpoint}] trả về HTTP {res.status_code}: {res.text[:300]}")
                    break

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                wait_sec = retry_delay * (2 ** (attempt - 1))
                msg = f"Sự cố mạng ({type(net_err).__name__}). Đang thử lại lần {attempt}/{max_retries} sau {wait_sec:.1f}s..."
                logger.warning(f"[{endpoint}] {msg}")
                await self._emit_progress(progress_callback, 0, 100, msg)
                if attempt < max_retries:
                    await asyncio.sleep(wait_sec)
                    continue

            except ContextLengthExceededError:
                raise

            except Exception as unk_err:
                logger.error(f"Lỗi không xác định khi gọi LLM API [{endpoint}]: {unk_err}")
                break

        # Fallback an toàn sang MockTranslator nếu mọi lần thử đều thất bại
        logger.warning(f"Không thể kết nối LLM API [{endpoint}] sau {max_retries} lần thử. Áp dụng fallback MockTranslator.")
        mock_tr = MockTranslator()
        mocked = await mock_tr.translate_text(prompt_text)
        return mocked, "stop"

    async def translate_blocks(
        self,
        blocks: list[OcrBlockModel],
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, str]:
        """
        Thực hiện toàn bộ quy trình dịch:
        1. Áp dụng Smart Pre-Filter bỏ qua references & header/footer.
        2. Tự động lựa chọn chiến lược phù hợp:
           - Large Context Cloud (Google Gemini 1M Context): Single-Call toàn bài + Auto-Continuation.
           - Local Models (Ollama, LM Studio, Llama.cpp, self-hosted): Tự động phân đoạn thích ứng (Adaptive Batching).
        3. Phát Callback tiến độ liên tục sau mỗi phân đoạn.
        """
        self.apply_smart_filter(blocks)

        translatable_blocks = [b for b in blocks if b.is_translatable]
        total_blocks = len(translatable_blocks)
        if total_blocks == 0:
            return {}

        # Nếu có injected translator (mock hoặc custom translator từ tests)
        if self.translator:
            result: dict[str, str] = {}
            for idx, b in enumerate(translatable_blocks, start=1):
                result[b.block_code] = await self.translator.translate_text(b.original_text)
                await self._emit_progress(
                    progress_callback,
                    idx,
                    total_blocks,
                    f"Đang dịch phân đoạn {idx}/{total_blocks}...",
                )
            return result

        # Xác định chế độ: Local model (context nhỏ 4k-8k) -> Adaptive Batching
        total_chars = sum(len(b.original_text) for b in translatable_blocks)
        is_local = settings.is_local_provider
        use_batching = is_local

        if use_batching:
            logger.info(
                f"Sử dụng chiến lược Adaptive Batching cho {settings.LLM_PROVIDER} "
                f"({total_blocks} khối, {total_chars} ký tự)..."
            )
            return await self._translate_in_batches(
                translatable_blocks, progress_callback=progress_callback
            )

        # Chế độ Single-Call toàn văn (mặc định cho Google Gemini 1M Context Window)
        try:
            return await self._translate_single_call(
                translatable_blocks, progress_callback=progress_callback
            )
        except ContextLengthExceededError:
            logger.warning(
                "Single-Call bị từ chối do chạm trần ngữ cảnh. Tự động chuyển đổi sang Adaptive Batching..."
            )
            return await self._translate_in_batches(
                translatable_blocks, progress_callback=progress_callback
            )

    async def _translate_single_call(
        self,
        translatable_blocks: list[OcrBlockModel],
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, str]:
        total_blocks = len(translatable_blocks)
        packed_prompt = self.pack_blocks(translatable_blocks)

        await self._emit_progress(
            progress_callback,
            0,
            total_blocks,
            f"Đang gửi toàn văn {total_blocks} khối tới {settings.LLM_MODEL}...",
        )

        raw_output, finish_reason = await self._call_completion_api(
            packed_prompt,
            max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            progress_callback=progress_callback,
        )

        parsed_translations = self.parse_translated_text(raw_output)

        # Auto-Continuation Guard nếu phản hồi bị cắt cụt do chạm trần output tokens
        missing_blocks = [
            b for b in translatable_blocks if b.block_code not in parsed_translations
        ]

        if missing_blocks and finish_reason == "length":
            logger.warning(
                f"Phản hồi chạm trần Output Token. Kích hoạt Auto-Continuation Guard cho {len(missing_blocks)} khối..."
            )
            await self._emit_progress(
                progress_callback,
                len(parsed_translations),
                total_blocks,
                f"Đang gọi tiếp nối (Auto-Continuation) cho {len(missing_blocks)} khối còn thiếu...",
            )
            continuation_prompt = self.pack_blocks(missing_blocks)
            cont_output, _ = await self._call_completion_api(
                continuation_prompt, progress_callback=progress_callback
            )
            cont_parsed = self.parse_translated_text(cont_output)
            parsed_translations.update(cont_parsed)

        # Fallback an toàn cho những khối vẫn còn thiếu
        for b in translatable_blocks:
            if b.block_code not in parsed_translations:
                parsed_translations[b.block_code] = b.original_text

        await self._emit_progress(
            progress_callback,
            total_blocks,
            total_blocks,
            f"Hoàn tất dịch thuật {total_blocks}/{total_blocks} khối bố cục.",
        )
        return parsed_translations

    async def _translate_in_batches(
        self,
        translatable_blocks: list[OcrBlockModel],
        batch_size: int = 8,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, str]:
        """
        Dịch theo từng lô (Batching) thích ứng với Local Model (Ollama, LM Studio, Llama.cpp)
        có kích thước cửa sổ ngữ cảnh giới hạn.
        """
        total_blocks = len(translatable_blocks)
        parsed_translations: dict[str, str] = {}

        # Chia nhỏ danh sách khối thành các batch vừa vặn
        batches: list[list[OcrBlockModel]] = []
        current_batch: list[OcrBlockModel] = []
        current_batch_chars = 0

        for b in translatable_blocks:
            b_len = len(b.original_text)
            # Nếu một batch vượt quá ~1500 tokens (6000 ký tự) hoặc quá batch_size khối
            if current_batch and (len(current_batch) >= batch_size or current_batch_chars + b_len > 6000):
                batches.append(current_batch)
                current_batch = [b]
                current_batch_chars = b_len
            else:
                current_batch.append(b)
                current_batch_chars += b_len

        if current_batch:
            batches.append(current_batch)

        logger.info(f"Đã chia {total_blocks} khối thành {len(batches)} batches nhỏ để dịch tuần tự.")

        for batch_idx, batch in enumerate(batches, start=1):
            batch_prompt = self.pack_blocks(batch)
            msg = f"Đang dịch batch {batch_idx}/{len(batches)} ({len(parsed_translations)}/{total_blocks} khối)..."
            await self._emit_progress(
                progress_callback,
                len(parsed_translations),
                total_blocks,
                msg,
            )

            raw_out, _ = await self._call_completion_api(
                batch_prompt,
                max_tokens=4096,
                progress_callback=progress_callback,
            )
            batch_parsed = self.parse_translated_text(raw_out)
            parsed_translations.update(batch_parsed)

            # Fallback nếu khối nào trong batch bị thiếu
            for b in batch:
                if b.block_code not in parsed_translations:
                    parsed_translations[b.block_code] = b.original_text

            await self._emit_progress(
                progress_callback,
                len(parsed_translations),
                total_blocks,
                f"Đã hoàn thành batch {batch_idx}/{len(batches)}.",
            )

        return parsed_translations


UniversalTranslator = GeminiTranslator
