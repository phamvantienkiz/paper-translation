from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MathTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    token_placeholder: str
    raw_latex: str
    is_display_math: bool


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    order_index: int
    segment_type: str
    original_content: str
    translated_content: str | None = None
    media_path: str | None = None
    is_user_edited: bool = False
    last_edited_at: datetime | None = None
    status: str


class SegmentUpdateRequest(BaseModel):
    translated_content: str
