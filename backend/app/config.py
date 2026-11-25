from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://igr_user:igr_password@localhost:5432/igr_db"
    igr_portal_url: str = "https://freesearchigrservice.maharashtra.gov.in/"
    storage_backend: str = "local"
    storage_dir: str = "./storage/documents"
    headless: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    job_concurrency: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def resolved_storage_path(self) -> Path:
        path = Path(self.storage_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def parsed_cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or ["*"]


settings = Settings()
