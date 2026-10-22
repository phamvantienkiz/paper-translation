import re
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.services.translation.glossary import IT_AI_GLOSSARY, build_system_instruction


class BaseTranslator(ABC):
    @abstractmethod
    async def translate_text(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        """Dịch một đoạn văn bản và bảo toàn các token toán học <<<MATH_TOKEN_XXXX>>>."""
        pass


class MockTranslator(BaseTranslator):
    """
    Translator ngoại tuyến / mô phỏng:
    Được sử dụng khi chưa thiết lập API Key hoặc phục vụ chạy kiểm thử (Unit / Integration Tests).
    Đảm bảo 100% bảo toàn các token <<<MATH_TOKEN_XXXX>>> và dịch các thuật ngữ IT/AI theo Glossary.
    """

    COMMON_PATTERNS = [
        (r"\bIn this paper\b", "Trong bài báo này"),
        (r"\bWe propose\b", "Chúng tôi đề xuất"),
        (r"\bWe present\b", "Chúng tôi trình bày"),
        (r"\bWe define\b", "Chúng tôi định nghĩa"),
        (r"\bWe evaluate\b", "Chúng tôi đánh giá"),
        (r"\bIntroduction\b", "Giới thiệu"),
        (r"\bRelated Work\b", "Các nghiên cứu liên quan"),
        (r"\bMethodology\b", "Phương pháp nghiên cứu"),
        (r"\bExperiments\b", "Thực nghiệm"),
        (r"\bResults\b", "Kết quả"),
        (r"\bConclusion\b", "Kết luận"),
        (r"\bAbstract\b", "Tóm tắt"),
        (r"\bFigure\b", "Hình"),
        (r"\bTable\b", "Bảng"),
        (r"\barchitecture\b", "kiến trúc"),
        (r"\bmodel\b", "mô hình"),
        (r"\bparameters\b", "các tham số"),
        (r"\btraining\b", "huấn luyện"),
        (r"\bevaluation\b", "đánh giá"),
        (r"\bperformance\b", "hiệu năng"),
    ]

    async def translate_text(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        if not text.strip():
            return text

        result = text
        # 1. Thay thế các mẫu câu học thuật phổ biến
        for pat, rep in self.COMMON_PATTERNS:
            result = re.sub(pat, rep, result, flags=re.IGNORECASE)

        # 2. Thay thế các thuật ngữ chuyên ngành IT/AI theo Glossary (ưu tiên cụm từ dài trước)
        sorted_glossary = sorted(IT_AI_GLOSSARY.items(), key=lambda x: len(x[0]), reverse=True)
        for term, translated_term in sorted_glossary:
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            result = pattern.sub(translated_term, result)

        return result


class OpenAICompatibleTranslator(BaseTranslator):
    """
    Bộ dịch thống nhất theo chuẩn OpenAI Chat Completions API (/chat/completions).
    Tương thích 100% với:
    - Google Gemini: endpoint https://generativelanguage.googleapis.com/v1beta/openai
      (Model mặc định: gemini-3.5-flash-lite)
    - OpenAI: endpoint https://api.openai.com/v1 (gpt-4o-mini, gpt-4o, ...)
    - Ollama: endpoint http://localhost:11434/v1 (qwen2.5:7b, llama3.1, ...)
    - Llama.cpp / vLLM / LocalAI: endpoint http://localhost:8080/v1
    - DeepSeek, Groq, OpenRouter, Anthropic proxy, ...
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        timeout: float = 60.0,
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

        clean_base = self.api_base.rstrip("/")

        # Tự động chuẩn hóa nếu người dùng dán URL Google Gemini không đúng định dạng OpenAI-compatible
        if "generativelanguage.googleapis.com" in clean_base:
            if not clean_base.endswith("/openai") and not clean_base.endswith("/openai/chat/completions"):
                logger.warning(
                    f"Cấu hình LLM_API_BASE '{clean_base}' của Google Gemini chưa đúng chuẩn OpenAI-Compatible. "
                    "Tự động chuẩn hóa về 'https://generativelanguage.googleapis.com/v1beta/openai'."
                )
                clean_base = "https://generativelanguage.googleapis.com/v1beta/openai"

        if clean_base.endswith("/chat/completions"):
            self.endpoint = clean_base
        else:
            self.endpoint = f"{clean_base}/chat/completions"

    async def translate_text(self, text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
        if not text.strip():
            return text

        system_instruction = build_system_instruction()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text},
            ],
            "temperature": self.temperature,
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key.lower() != "none":
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(self.endpoint, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        raw_content = choices[0].get("message", {}).get("content", "").strip()
                        # Loại bỏ wrapper markdown codeblock nếu model tự bọc
                        if raw_content.startswith("```") and raw_content.endswith("```"):
                            lines = raw_content.splitlines()
                            if len(lines) >= 3:
                                raw_content = "\n".join(lines[1:-1]).strip()
                        return raw_content
                logger.warning(
                    f"LLM API [{self.endpoint}] trả về HTTP {res.status_code}: {res.text[:300]}"
                )
        except Exception as e:
            logger.error(f"Lỗi kết nối tới LLM API [{self.endpoint}]: {e}")

        # Tự động fallback sang MockTranslator nếu gọi API gặp sự cố mạng hoặc lỗi xác thực
        fallback = MockTranslator()
        return await fallback.translate_text(text, source_lang, target_lang)


class TranslationFactory:
    """Factory khởi tạo Translator tương ứng theo cấu hình tệp .env."""

    @staticmethod
    def get_translator() -> BaseTranslator:
        api_key = settings.effective_api_key
        api_base = settings.LLM_API_BASE
        is_local = "localhost" in api_base or "127.0.0.1" in api_base

        # Kích hoạt OpenAICompatibleTranslator nếu có API Key hoặc chạy Local endpoint (Ollama/Llama.cpp)
        if api_key or is_local:
            logger.info(
                f"Sử dụng OpenAICompatibleTranslator | Endpoint: {api_base} | Model: {settings.LLM_MODEL}"
            )
            return OpenAICompatibleTranslator(
                api_base=api_base,
                api_key=api_key or "ollama",
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )

        logger.info(
            "Chưa cấu hình LLM_API_KEY trong .env. Tự động sử dụng MockTranslator ngoại tuyến với Glossary IT/AI."
        )
        return MockTranslator()
