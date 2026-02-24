from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Quarter:
    year: int
    quarter: int

    @classmethod
    def parse(cls, value: str) -> "Quarter":
        match = re.search(r"(\d{4})\s*-\s*Q(\d)", str(value))
        if not match:
            raise ValueError(f"Invalid quarter format: {value}")
        return cls(int(match.group(1)), int(match.group(2)))

    def key(self) -> tuple[int, int]:
        return (self.year, self.quarter)
