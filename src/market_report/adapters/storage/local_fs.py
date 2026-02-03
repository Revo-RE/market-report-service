from __future__ import annotations

from pathlib import Path

from market_report.ports.storage import Storage


class LocalFileSystemStorage(Storage):
    """Persist artifacts to the local filesystem."""

    def __init__(self, base_dir: str = "outputs"):
        self._base_dir = Path(base_dir)
        self._run_dir: Path | None = None

    def prepare_run_dir(self, run_id: str) -> Path:
        self._run_dir = self._base_dir / run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        return self._run_dir

    def save_artifact(self, source_path: Path, relative_path: str) -> Path:
        if self._run_dir is None:
            raise RuntimeError("Run directory not initialized. Call prepare_run_dir first.")
        destination = self._run_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_path.read_bytes())
        return destination
