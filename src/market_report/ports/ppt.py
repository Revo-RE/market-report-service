from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

from market_report.config.schemas import PptConfig


class PptRenderer(ABC):
    """Port for generating PowerPoint decks."""

    @abstractmethod
    def render(self, ppt_config: PptConfig, chart_paths: Dict[str, Path], output_path: Path) -> Path:
        """Build a PPTX deck and return the file path."""
        raise NotImplementedError
