from datetime import datetime, date
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SearchCriteria(BaseModel):
    model_config = ConfigDict(extra="allow")

    region: Literal["MUMBAI", "REST", "URBAN"] = "MUMBAI"
    year: str | int | None = None
    district: str | None = None
    all_districts: bool = False
    tahsil: str | None = None
    sro: str | None = None
    doc_type: str | None = None  # eFiling | eRegistration | Regular | iSarita 2.0
    area_name: str | None = None
    area: str | None = None
    village: str | None = None
    property_number: str | None = None
    attribute_value: str | None = None
    document_number: str | None = None
    party_name: str | None = None


class CreateJobRequest(BaseModel):
    search_type: Literal["PROPERTY", "DOCUMENT"]
    criteria: dict[str, Any] = Field(..., min_length=1)


class CaptchaSolutionRequest(BaseModel):
    solution: str = Field(..., min_length=1, max_length=30)


class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    step: str | None
    message: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int | None
    downloaded_at: datetime


class PropertyRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    district: str | None = None
    tahsil_or_village: str | None = None
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
    created_at: datetime | None = None
    documents: list[DocumentResponse] = []


class JobSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    search_type: str
    criteria: dict[str, Any]
    status: str
    portal_notice: str | None = None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    record_count: int = 0


class JobDetailResponse(JobSummaryResponse):
    captcha_image_base64: str | None = None
    logs: list[LogResponse] = []
    records: list[PropertyRecordResponse] = []


class PropertyRecordDetailResponse(PropertyRecordResponse):
    raw_html_snapshot: str | None = None
    job_ids: list[UUID] = []
