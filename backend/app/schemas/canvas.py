
from pydantic import BaseModel, ConfigDict, Field


class CanvasBlockResponse(BaseModel):
    id: str
    block_code: str
    reading_order: int
    label: str
    bbox_norm: list[float] = Field(description="[x0, y0, x1, y1] normalized to [0.0, 1.0]")
    is_translatable: bool
    original_text: str
    translated_text: str | None = None
    figure_image_url: str | None = None
    is_user_edited: bool = False

    model_config = ConfigDict(from_attributes=True)


class CanvasPageResponse(BaseModel):
    page_number: int
    width_pt: float
    height_pt: float
    page_image_url: str
    blocks: list[CanvasBlockResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CanvasDataResponse(BaseModel):
    session_id: str
    title: str | None = None
    total_pages: int = 0
    pages: list[CanvasPageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
