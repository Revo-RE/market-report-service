from __future__ import annotations

from pathlib import Path

from market_report.ports.storage import Storage


class S3Storage(Storage):
    """Premium adapter stub for S3 storage."""

    def prepare_run_dir(self, run_id: str) -> Path:
        raise NotImplementedError("TODO: Implement S3 storage adapter.")

    def save_artifact(self, source_path: Path, relative_path: str) -> Path:
        raise NotImplementedError("TODO: Implement S3 storage adapter.")
