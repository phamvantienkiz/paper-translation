from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BlockUpdateRequest(BaseModel):
    translated_text: str = Field(..., min_length=1, description="Nội dung dịch đã chỉnh sửa")

    model_config = ConfigDict(extra="ignore")


class BlockResponse(BaseModel):
    id: str
    session_id: str
    page_id: str
    page_number: int
    block_code: str
    reading_order: int
    label: str
    bbox_x0: float
    bbox_y0: float
    bbox_x1: float
    bbox_y1: float
    is_translatable: bool
    original_text: str
    translated_text: str | None = None
    figure_image_path: str | None = None
    is_user_edited: bool = False
    last_edited_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
