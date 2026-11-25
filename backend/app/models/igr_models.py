import uuid
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Date, DateTime,
    Numeric, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class JobRecordLink(Base):
    __tablename__ = "job_records"

    job_id = Column(UUID(as_uuid=True), ForeignKey("search_jobs.id", ondelete="CASCADE"), primary_key=True)
    record_id = Column(UUID(as_uuid=True), ForeignKey("property_records.id", ondelete="CASCADE"), primary_key=True)


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_type = Column(String(50), nullable=False)  # PROPERTY | DOCUMENT
    criteria = Column(JSONB, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")  # PENDING | PROCESSING | AWAITING_CAPTCHA | COMPLETED | FAILED
    captcha_image_base64 = Column(Text, nullable=True)
    captcha_solution = Column(String(30), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    logs = relationship("AutomationLog", back_populates="job", cascade="all, delete-orphan", order_by="AutomationLog.id")
    records = relationship("PropertyRecord", secondary="job_records", back_populates="jobs")


class PropertyRecord(Base):
    __tablename__ = "property_records"
    __table_args__ = (
        UniqueConstraint("sro_name", "document_number", "registration_year", name="uq_sro_doc_year"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sro_name = Column(String(255), nullable=False)
    document_number = Column(String(100), nullable=False)
    registration_year = Column(Integer, nullable=False)
    registration_date = Column(Date, nullable=True)
    article_type = Column(String(255), nullable=True)
    consideration_amount = Column(Numeric(15, 2), nullable=True)
    market_value = Column(Numeric(15, 2), nullable=True)
    party_details = Column(JSONB, nullable=True)
    property_details = Column(Text, nullable=True)
    survey_cts_number = Column(String(255), nullable=True)
    raw_html_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("SearchJob", secondary="job_records", back_populates="records")
    documents = relationship("DocumentFile", back_populates="record", cascade="all, delete-orphan")


class DocumentFile(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("property_records.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    mime_type = Column(String(100), default="application/pdf")
    file_size_bytes = Column(BigInteger, nullable=True)
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("PropertyRecord", back_populates="documents")


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("search_jobs.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20), nullable=False, default="INFO")
    step = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("SearchJob", back_populates="logs")