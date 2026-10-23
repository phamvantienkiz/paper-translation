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
    # Cấu hình AI / LLM - Chiến lược Local-First (mặc định llama_cpp + Qwen3)
    # Tương thích:
    # 1. Local Llama.cpp (mặc định ưu tiên cao nhất, chạy ngoại tuyến)
    # 2. Google Gemini (tùy chọn dự phòng)
    # 3. OpenAI ChatGPT / Ollama / LM Studio
    # =========================================================================
    LLM_PROVIDER: str = "llama_cpp"  # llama_cpp, gemini, openai, ollama, lm_studio, self_hosted
    LLM_MODEL_NAME: str = "Qwen3-1.7B-Q4_K_M.gguf"
    LLM_LOCAL_N_CTX: int = 8192  # Mặc định 8K context (~2.8GB RAM)
    LLM_LOCAL_MAX_N_CTX: int = 16384  # Khóa trần cứng 16K context (<= 4.0GB RAM)
    LLM_LOCAL_THREADS: int = 4
    LLM_LOCAL_N_GPU_LAYERS: int = -1  # Tự động nạp GPU nếu có CUDA, fallback sang 0 nếu CPU
    LLM_HARD_RAM_CEILING_GB: float = 4.0

    LLM_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_TEMPERATURE: float = 0.2
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
        """Ước tính mức chiếm dụng RAM dựa trên kích thước context window."""
        ctx = n_ctx or self.LLM_LOCAL_N_CTX
        # Model weights (~1.03GB) + KV cache + buffers
        # 4096 ctx: ~2.5GB, 8192 ctx: ~2.8GB, 16384 ctx: ~3.8GB
        return round(1.03 + (ctx / 8192) * 1.77, 2)

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
