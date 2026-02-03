from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass
class NormalizedTables:
    tables: Dict[str, pd.DataFrame]


@dataclass
class MetricsBundle:
    metrics: Dict[str, object]
