from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Tìm tệp .env tại thư mục gốc của project hoặc trong backend/
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Paper Translation"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    DATABASE_URL: str = "sqlite+aiosqlite:///./paper_translation.db"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "storage")

    MAX_UPLOAD_SIZE_BYTES: int = 52_428_800  # 50 MB

    # =========================================================================
    # Cấu hình AI / LLM thống nhất theo chuẩn OpenAI-Compatible
    # Tương thích 100% với:
    # 1. Google Gemini (qua endpoint https://generativelanguage.googleapis.com/v1beta/openai)
    # 2. OpenAI ChatGPT (qua endpoint https://api.openai.com/v1)
    # 3. Local Model (Ollama http://localhost:11434/v1 hoặc Llama.cpp http://localhost:8080/v1)
    # 4. Các nhà cung cấp khác (Groq, DeepSeek, OpenRouter, Anthropic proxy, v.v.)
    # =========================================================================
    LLM_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT_SECONDS: float = 60.0

    # Khả năng tương thích ngược
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    @property
    def effective_api_key(self) -> str:
        """Lấy API key theo thứ tự ưu tiên: LLM_API_KEY > GEMINI_API_KEY > OPENAI_API_KEY."""
        return self.LLM_API_KEY or self.GEMINI_API_KEY or self.OPENAI_API_KEY


settings = Settings()
