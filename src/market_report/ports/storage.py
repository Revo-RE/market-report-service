from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Storage(ABC):
    """Port for persisting artifacts."""

    @abstractmethod
    def prepare_run_dir(self, run_id: str) -> Path:
        """Create the run directory and return its path."""
        raise NotImplementedError

    @abstractmethod
    def save_artifact(self, source_path: Path, relative_path: str) -> Path:
        """Persist an artifact and return the final path."""
        raise NotImplementedError
