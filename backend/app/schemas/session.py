from datetime import datetime
from typing import Any, Dict, List, Optional
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
    arxiv_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    status: str
    progress_percent: int
    created_at: datetime
    updated_at: datetime


class SessionWithSegmentsResponse(SessionDetailResponse):
    segments: List[SegmentResponse] = []


class ArxivIngestRequest(BaseModel):
    arxiv_input: str  # Can be URL or ID (e.g. 1706.03762 or https://arxiv.org/abs/1706.03762)


class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
