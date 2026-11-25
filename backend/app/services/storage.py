"""Configurable document storage service (local disk by default)."""

from pathlib import Path
from app.config import settings


class DocumentStorageService:
    """Handles storing and resolving extracted Index-II documents."""

    def __init__(self):
        self.backend = settings.storage_backend
        self.base_dir = settings.resolved_storage_path()

    def build_path(self, filename: str) -> Path:
        safe_name = Path(filename).name
        target = self.base_dir / safe_name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def save_bytes(self, filename: str, content: bytes) -> Path:
        path = self.build_path(filename)
        path.write_bytes(content)
        return path

    def save_text(self, filename: str, content: str) -> Path:
        path = self.build_path(filename)
        path.write_text(content, encoding="utf-8")
        return path


storage_service = DocumentStorageService()
