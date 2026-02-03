from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict


class NarrativeEngine(ABC):
    """Port for narrative generation."""

    @abstractmethod
    def generate(self, metrics: Dict[str, object]) -> Dict[str, str]:
        """Return narrative strings keyed by slide/chart identifiers."""
        raise NotImplementedError
