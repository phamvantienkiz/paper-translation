from pathlib import Path

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
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    DATABASE_URL: str = "sqlite+aiosqlite:///./paper_translation.db"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "storage")

    @property
    def pages_dir(self) -> Path:
        p = self.STORAGE_DIR / "pages"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def figures_dir(self) -> Path:
        p = self.STORAGE_DIR / "figures"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def raw_pdfs_dir(self) -> Path:
        p = self.STORAGE_DIR / "raw_pdfs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def exports_dir(self) -> Path:
        p = self.STORAGE_DIR / "exports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def temp_dir(self) -> Path:
        p = self.STORAGE_DIR / "temp"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_dir(self) -> Path:
        p = self.STORAGE_DIR / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def indra_models_dir(self) -> Path:
        p = self.STORAGE_DIR / "models" / "indra_ocr"
        p.mkdir(parents=True, exist_ok=True)
        return p

    MAX_UPLOAD_SIZE_BYTES: int = 52_428_800  # 50 MB

    # =========================================================================
    # Cấu hình AI / LLM - Chiến lược Local-First Standalone Serving
    # Model: gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf
    # Tối ưu hóa 4 P-cores trên Intel Core i5-13500H, RAM trần <= 8.0GB
    # Context window 16K (16384) / 8K (8192) tokens
    # =========================================================================
    LLM_PROVIDER: str = "llama_cpp"  # llama_cpp, gemini, openai, ollama, lm_studio, self_hosted
    LLM_MODEL_NAME: str = "gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf"
    LLM_LOCAL_N_CTX: int = 16384  # Chuẩn 16K context window
    LLM_LOCAL_MAX_N_CTX: int = 16384  # Khóa trần cứng 16K context
    LLM_LOCAL_THREADS: int = 4  # Tối ưu chính xác 4 P-cores của Intel Core i5-13500H
    LLM_LOCAL_N_BATCH: int = 512  # Batch size tối ưu cho standalone server
    LLM_LOCAL_MAX_OUTPUT_TOKENS: int = 10240  # Dự phòng output tiếng Việt nở 2.0x - 2.5x
    LLM_LOCAL_N_GPU_LAYERS: int = -1  # Tự động nạp GPU/iGPU nếu có, fallback CPU 4 P-cores
    LLM_HARD_RAM_CEILING_GB: float = 8.0  # Giới hạn trần cứng 8GB RAM

    # Standalone llama.cpp Server Service config
    LLM_SERVER_HOST: str = "127.0.0.1"
    LLM_SERVER_PORT: int = 8081
    LLM_SERVER_TIMEOUT_SECONDS: float = 900.0  # Nâng lên 900s (15 phút) để đáp ứng các lô suy luận dịch thuật lớn trên CPU 4 P-cores
    LLM_SERVER_AUTO_START: bool = True

    LLM_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY_SECONDS: float = 2.0
    LLM_MAX_OUTPUT_TOKENS: int = 65536
    LLM_MAX_CONTEXT_TOKENS: int = 1_000_000

    # Khả năng tương thích ngược
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    @property
    def llm_model_path(self) -> Path:
        """Đường dẫn tệp trọng số GGUF mô hình ngôn ngữ cục bộ."""
        return self.models_dir / self.LLM_MODEL_NAME

    def get_estimated_ram_usage_gb(self, n_ctx: int | None = None) -> float:
        """Ước tính mức chiếm dụng RAM dựa trên kích thước context window cho Gemma-4-E2B."""
        ctx = n_ctx or self.LLM_LOCAL_N_CTX
        # Trọng số Gemma-4-E2B (~2.62GB) + KV cache Q8_0 (~0.9GB ở 16K) + Compute buffers (~0.6GB)
        # 8192 ctx: ~3.5GB, 16384 ctx: ~4.2GB (nằm gọn trong trần cứng 8.0GB RAM)
        return round(2.62 + (ctx / 16384) * 1.58, 2)

    @property
    def standalone_server_url(self) -> str:
        """URL nội bộ của standalone llama.cpp server."""
        return f"http://{self.LLM_SERVER_HOST}:{self.LLM_SERVER_PORT}"

    @property
    def effective_api_key(self) -> str:
        """Lấy API key theo thứ tự ưu tiên: LLM_API_KEY > GEMINI_API_KEY > OPENAI_API_KEY."""
        return self.LLM_API_KEY or self.GEMINI_API_KEY or self.OPENAI_API_KEY

    @property
    def is_local_provider(self) -> bool:
        """Kiểm tra xem mô hình hiện tại có phải chạy trên Local / Self-hosted không."""
        provider = self.LLM_PROVIDER.lower()
        if provider in ("ollama", "llama_cpp", "lm_studio", "self_hosted"):
            return True
        base = self.LLM_API_BASE.lower()
        return any(h in base for h in ("localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.0."))

    @property
    def normalized_llm_endpoint(self) -> str:
        """
        Chuẩn hóa endpoint theo chuẩn OpenAI Chat Completions (/chat/completions).
        Tự động nhận diện và sửa lỗi đường dẫn của Gemini, Ollama, LM Studio, Llama.cpp.
        """
        base = self.LLM_API_BASE.strip().rstrip("/")
        # Tự động sửa URL của Google Gemini nếu người dùng nhập thiếu
        if "generativelanguage.googleapis.com" in base:
            if not base.endswith("/openai") and not base.endswith("/openai/chat/completions"):
                base = "https://generativelanguage.googleapis.com/v1beta/openai"

        # Tự động thêm /v1 cho Ollama (11434), LM Studio (1234), Llama.cpp (8080) nếu thiếu
        if any(port in base for port in (":11434", ":1234", ":8080")) and not base.endswith("/v1") and not base.endswith("/chat/completions"):
            base = f"{base}/v1"

        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"


settings = Settings()
