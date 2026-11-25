from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://igr_user:igr_password@localhost:5432/igr_db"
    igr_portal_url: str = "https://freesearchigrservice.maharashtra.gov.in/"
    storage_dir: str = "./storage/documents"
    headless: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def resolved_storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()