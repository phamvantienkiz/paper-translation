from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.segment import SegmentResponse


class SessionCreateResponse(BaseModel):
    session_id: str
    file_name: str
    source_type: str
    status: str
    message: str


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: str
    file_name: str
    file_size_bytes: int
    arxiv_id: str | None = None
    title: str | None = None
    authors: str | None = None
    abstract: str | None = None
    total_pages: int = 0
    status: str
    progress_percent: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionWithSegmentsResponse(SessionDetailResponse):
    segments: list[SegmentResponse] = []


class ArxivIngestRequest(BaseModel):
    arxiv_input: str  # Can be URL or ID (e.g. 1706.03762 or https://arxiv.org/abs/1706.03762)


class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    message: str | None = None
    error: dict[str, Any] | None = None
    request_id: str | None = None
