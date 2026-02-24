from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


def normalize_key(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def quarter_key(value: object) -> tuple[int, int]:
    if value is None or pd.isna(value):
        return (9999, 9)
    match = re.search(r"(\d{4})\s*-\s*Q(\d)", str(value))
    if not match:
        return (9999, 9)
    return (int(match.group(1)), int(match.group(2)))


def weighted_avg(df: pd.DataFrame, value_col: str, weight_col: str) -> float:
    if value_col not in df.columns or weight_col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[value_col], errors="coerce")
    weights = pd.to_numeric(df[weight_col], errors="coerce")
    total_weight = weights.sum(skipna=True)
    if total_weight == 0:
        return 0.0
    return (values * weights).sum(skipna=True) / total_weight


def short_id(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().replace(" ", "")
    return text[:4].title()


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df[list(columns)]


def round_or_keep(value: object) -> object:
    if value is None or pd.isna(value):
        return value
    if isinstance(value, str):
        return value
    try:
        return round(float(value), 2)
    except Exception:
        return value

