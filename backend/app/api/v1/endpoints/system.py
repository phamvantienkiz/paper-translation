from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.translation.llama_service import LlamaCppService

router = APIRouter(prefix="/system", tags=["System Engine"])


class EngineStatusResponse(BaseModel):
    active_provider: str
    is_local: bool
    model_name: str
    context_window: int
    hard_ram_ceiling_gb: float
    estimated_ram_usage_gb: float
    ocr_loaded: bool
    llm_loaded: bool


class EngineSwitchRequest(BaseModel):
    provider: str = Field(..., description="'llama_cpp' hoặc 'gemini'")
    context_window: int | None = Field(
        None, description="Kích thước ngữ cảnh (n_ctx), tối đa 16384 tokens"
    )


@router.get("/engine-status", response_model=EngineStatusResponse)
async def get_engine_status() -> EngineStatusResponse:
    """
    Truy xuất trạng thái hoạt động của Engine dịch thuật (Local LLM vs Cloud API)
    và các thông số tài nguyên phần cứng thời gian thực.
    """
    is_local = settings.LLM_PROVIDER.lower() in ("llama_cpp", "local", "qwen")
    model_name = settings.LLM_MODEL_NAME if is_local else settings.LLM_MODEL
    context_window = settings.LLM_LOCAL_N_CTX if is_local else settings.LLM_MAX_CONTEXT_TOKENS

    llm_loaded = False
    if is_local and LlamaCppService._instance is not None:
        llm_loaded = LlamaCppService._instance.is_loaded

    # Ước tính mức RAM sử dụng (nếu chạy local LLM)
    estimated_ram = settings.get_estimated_ram_usage_gb(settings.LLM_LOCAL_N_CTX) if is_local else 0.0

    return EngineStatusResponse(
        active_provider=settings.LLM_PROVIDER,
        is_local=is_local,
        model_name=model_name,
        context_window=context_window,
        hard_ram_ceiling_gb=settings.LLM_HARD_RAM_CEILING_GB,
        estimated_ram_usage_gb=estimated_ram,
        ocr_loaded=False,  # OCR luôn được giải phóng sau giai đoạn bóc tách
        llm_loaded=llm_loaded,
    )


@router.post("/engine-switch", response_model=EngineStatusResponse)
async def switch_engine(payload: EngineSwitchRequest) -> EngineStatusResponse:
    """
    Chuyển đổi Engine dịch thuật giữa Local LLM (llama.cpp Qwen3) và Cloud API (Gemini).
    Rào chắn: Bắt buộc tuân thủ giới hạn context_window <= 16384 tokens (<= 4.0GB RAM).
    """
    target_provider = payload.provider.strip().lower()

    if target_provider not in ("llama_cpp", "gemini", "openai"):
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{payload.provider}' không hợp lệ. Chỉ chấp nhận 'llama_cpp' hoặc 'gemini'.",
        )

    if target_provider == "llama_cpp":
        # Kiểm tra tệp mô hình GGUF
        if not settings.llm_model_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Không tìm thấy tệp mô hình GGUF tại {settings.llm_model_path}. Không thể chuyển sang Local LLM.",
            )

        if payload.context_window is not None:
            if payload.context_window > settings.LLM_LOCAL_MAX_N_CTX:
                raise HTTPException(
                    status_code=400,
                    detail=f"Context window ({payload.context_window}) vượt quá giới hạn trần cứng cho phép "
                    f"({settings.LLM_LOCAL_MAX_N_CTX} tokens / <= 4.0GB RAM).",
                )
            settings.LLM_LOCAL_N_CTX = payload.context_window

    elif target_provider == "gemini":
        # Nếu chuyển sang Cloud, thu hồi bộ nhớ Local LLM để giải phóng RAM
        LlamaCppService.reset()

    settings.LLM_PROVIDER = target_provider

    return await get_engine_status()
