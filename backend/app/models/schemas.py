from datetime import datetime, date
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    search_type: Literal["PROPERTY", "DOCUMENT"]
    criteria: dict[str, Any] = Field(..., min_length=1)


class CaptchaSolutionRequest(BaseModel):
    solution: str = Field(..., min_length=1, max_length=30)


class LogResponse(BaseModel):
    id: int
    level: str
    step: str | None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int | None
    downloaded_at: datetime

    class Config:
        from_attributes = True


class PropertyRecordResponse(BaseModel):
    id: UUID
    sro_name: str
    document_number: str
    registration_year: int
    registration_date: date | None
    article_type: str | None
    consideration_amount: float | None
    market_value: float | None
    party_details: dict[str, Any] | None
    property_details: str | None
    survey_cts_number: str | None
    documents: list[DocumentResponse] = []

    class Config:
        from_attributes = True


class JobSummaryResponse(BaseModel):
    id: UUID
    search_type: str
    criteria: dict[str, Any]
    status: str
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    record_count: int = 0

    class Config:
        from_attributes = True


class JobDetailResponse(JobSummaryResponse):
    captcha_image_base64: str | None = None
    logs: list[LogResponse] = []
    records: list[PropertyRecordResponse] = []