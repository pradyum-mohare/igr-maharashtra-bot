from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401
from app.api.jobs import router as jobs_router
from app.config import settings
from app.database import Base, engine, ensure_schema_columns
from app.services.job_queue import recover_interrupted_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    recover_interrupted_jobs()
    yield


app = FastAPI(
    title="IGR Maharashtra Free Search Automation API",
    description="REST API for automating property & document searches on freesearchigrservice.maharashtra.gov.in",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
