from __future__ import annotations

from pathlib import Path
from typing import Dict

from market_report.config.schemas import PptConfig
from market_report.ports.ppt import PptRenderer


class PptService:
    """Coordinate PPT rendering."""

    def __init__(self, renderer: PptRenderer):
        self._renderer = renderer

    def render(self, ppt_config: PptConfig, chart_paths: Dict[str, Path], output_path: Path) -> Path:
        return self._renderer.render(ppt_config, chart_paths, output_path)
