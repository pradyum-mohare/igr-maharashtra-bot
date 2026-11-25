from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.automation.parser import DISTRICT_ALIASES
from app.database import get_db
from app.models import AutomationLog, DocumentFile, PropertyRecord, SearchJob
from app.models.schemas import (
    CaptchaSolutionRequest,
    CreateJobRequest,
    JobDetailResponse,
    JobSummaryResponse,
    PropertyRecordDetailResponse,
    PropertyRecordResponse,
)
from app.services.job_queue import submit_job_to_queue

router = APIRouter(prefix="/api", tags=["IGR Automation"])


def add_log(db: Session, job_id: UUID, message: str, level: str = "INFO", step: str | None = None):
    log = AutomationLog(job_id=job_id, level=level, step=step, message=message)
    db.add(log)
    db.commit()


def _to_job_summary(job: SearchJob) -> JobSummaryResponse:
    return JobSummaryResponse(
        id=job.id,
        search_type=job.search_type,
        criteria=job.criteria,
        status=job.status,
        portal_notice=job.portal_notice,
        error_message=job.error_message,
        retry_count=job.retry_count or 0,
        created_at=job.created_at,
        updated_at=job.updated_at,
        record_count=len(job.records),
    )


@router.get("/metadata/districts")
def list_supported_districts():
    """Return supported Maharashtra districts with English & Marathi names."""
    return [
        {"english": key.title(), "marathi": val}
        for key, val in DISTRICT_ALIASES.items()
    ]


@router.post("/jobs", response_model=JobSummaryResponse, status_code=201)
def create_search_job(payload: CreateJobRequest, db: Session = Depends(get_db)):
    job = SearchJob(
        search_type=payload.search_type,
        criteria=payload.criteria,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    add_log(db, job.id, f"Queued {job.search_type} search job.", step="QUEUE")
    submit_job_to_queue(job.id)
    return _to_job_summary(job)


@router.get("/jobs", response_model=list[JobSummaryResponse])
def list_jobs(
    status: str | None = Query(default=None),
    search_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(SearchJob)
    if status:
        query = query.filter(SearchJob.status == status.upper())
    if search_type:
        query = query.filter(SearchJob.search_type == search_type.upper())
    jobs = query.order_by(SearchJob.created_at.desc()).all()
    return [_to_job_summary(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailResponse(
        **_to_job_summary(job).model_dump(),
        captcha_image_base64=job.captcha_image_base64,
        logs=job.logs,
        records=job.records,
    )


@router.post("/jobs/{job_id}/captcha")
def submit_captcha(job_id: UUID, payload: CaptchaSolutionRequest, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "AWAITING_CAPTCHA":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}, not awaiting CAPTCHA")
    job.captcha_solution = payload.solution.strip()
    job.status = "PROCESSING"
    db.commit()
    add_log(db, job.id, "Manual CAPTCHA verification submitted from dashboard.", step="CAPTCHA")
    return {"message": "CAPTCHA solution submitted", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/captcha/refresh")
def refresh_captcha(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "AWAITING_CAPTCHA":
        raise HTTPException(status_code=409, detail="CAPTCHA refresh is only available while awaiting CAPTCHA")
    job.captcha_refresh_requested = True
    db.commit()
    return {"message": "CAPTCHA refresh requested", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise HTTPException(status_code=409, detail=f"Job already in terminal state {job.status}")
    job.cancel_requested = True
    if job.status == "PENDING":
        job.status = "CANCELLED"
    db.commit()
    add_log(db, job.id, "Cancellation requested from dashboard.", level="WARNING", step="CANCEL")
    return {"message": "Cancellation requested", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/retry", response_model=JobSummaryResponse)
def retry_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "PENDING"
    job.error_message = None
    job.portal_notice = None
    job.captcha_solution = None
    job.captcha_image_base64 = None
    job.captcha_refresh_requested = False
    job.cancel_requested = False
    job.retry_count = (job.retry_count or 0) + 1
    db.commit()
    db.refresh(job)
    add_log(db, job.id, f"Retry #{job.retry_count} queued.", step="RETRY")
    submit_job_to_queue(job.id)
    return _to_job_summary(job)


@router.get("/records", response_model=list[PropertyRecordResponse])
def list_records(
    q: str | None = Query(default=None, description="Search by document number, SRO, district, survey/CTS, or property details"),
    year: int | None = Query(default=None),
    district: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(PropertyRecord)
    if year is not None:
        query = query.filter(PropertyRecord.registration_year == year)
    if district:
        query = query.filter(
            or_(
                PropertyRecord.district.ilike(f"%{district}%"),
                PropertyRecord.sro_name.ilike(f"%{district}%"),
            )
        )
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                PropertyRecord.document_number.ilike(term),
                PropertyRecord.sro_name.ilike(term),
                PropertyRecord.district.ilike(term),
                PropertyRecord.tahsil_or_village.ilike(term),
                PropertyRecord.survey_cts_number.ilike(term),
                PropertyRecord.property_details.ilike(term),
            )
        )
    return query.order_by(PropertyRecord.created_at.desc()).all()


@router.get("/records/{record_id}", response_model=PropertyRecordDetailResponse)
def get_record_detail(record_id: UUID, db: Session = Depends(get_db)):
    record = db.query(PropertyRecord).filter(PropertyRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return PropertyRecordDetailResponse(
        id=record.id,
        district=record.district,
        tahsil_or_village=record.tahsil_or_village,
        sro_name=record.sro_name,
        document_number=record.document_number,
        registration_year=record.registration_year,
        registration_date=record.registration_date,
        article_type=record.article_type,
        consideration_amount=float(record.consideration_amount) if record.consideration_amount is not None else None,
        market_value=float(record.market_value) if record.market_value is not None else None,
        party_details=record.party_details,
        property_details=record.property_details,
        survey_cts_number=record.survey_cts_number,
        created_at=record.created_at,
        documents=record.documents,
        raw_html_snapshot=record.raw_html_snapshot,
        job_ids=[j.id for j in record.jobs],
    )


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(DocumentFile).filter(DocumentFile.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path=file_path, filename=doc.file_name, media_type=doc.mime_type)
