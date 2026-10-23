from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.translation.llama_server_manager import LlamaServerManager


class LlamaInternalClient:
    """
    Python Client giao tiếp với Standalone llama.cpp Server qua mạng nội bộ Loopback (127.0.0.1).

    Tuân thủ chuẩn OpenAI Chat Completions (/v1/chat/completions):
    - Đảm bảo server đang chạy trước khi gửi request.
    - Gửi request phân lô 2000 - 2500 từ tiếng Anh.
    - Cấp phát max_tokens = 10240 cho tiếng Việt (dự phòng gấp 2.0x - 2.5x Input).
    - Tự động bóc tách và làm sạch thẻ ChatML / reasoning.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        server_manager: LlamaServerManager | None = None,
    ):
        self.base_url = (base_url or settings.standalone_server_url).rstrip("/")
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
        self.server_manager = server_manager or LlamaServerManager.get_instance()
        self._custom_timeout = timeout_seconds

    @property
    def timeout(self) -> float:
        return self._custom_timeout if self._custom_timeout is not None else settings.LLM_SERVER_TIMEOUT_SECONDS

    async def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> str:
        """Gửi yêu cầu Chat Completion bất đồng bộ tới Standalone llama.cpp Server nội bộ."""
        # Đảm bảo tiến trình server đang chạy và sẵn sàng
        await self.server_manager.ensure_server_running()

        target_max_tokens = max_tokens or settings.LLM_LOCAL_MAX_OUTPUT_TOKENS  # 10240
        target_temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        stop_tokens = stop or ["<|im_end|>", "<|endoftext|>", "<end_of_turn>", "<eos>"]

        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": target_max_tokens,
            "temperature": target_temp,
            "stop": stop_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.chat_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    raw_text = msg.get("content", "")
                    if "</think>" in raw_text:
                        raw_text = raw_text.split("</think>")[-1].strip()
                    return raw_text
                return ""
            except httpx.HTTPError as e:
                logger.error(f"Lỗi kết nối Standalone llama.cpp Server tại {self.chat_endpoint}: {e}")
                raise RuntimeError(
                    f"Không thể giao tiếp với Standalone llama.cpp Server ({e})."
                ) from e
