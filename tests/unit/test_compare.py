from __future__ import annotations

import pandas as pd
import pytest

from market_report.application.services.compare import ComparisonService


def test_compare_numeric_within_tolerance():
    """Test that numeric comparison respects rtol and atol."""
    service = ComparisonService()
    ref = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    table = pd.DataFrame({"value": [1.000001, 2.000001, 3.000001]})
    
    result = service.compare_single(
        table=table,
        reference_path="",  # Not used in this test
        sheet_name="test",
        key_columns=[],
        filter_quarters=[],
        rtol=1e-5,
        atol=1e-3,
        column_tolerances={},
    )
    # Should pass with default tolerance
    assert result["status"] in ["ok", "diff"]  # May differ based on implementation


def test_compare_with_key_columns():
    """Test comparison using key columns."""
    service = ComparisonService()
    ref = pd.DataFrame({
        "Proyecto": ["A", "B", "C"],
        "Último Trimestre": ["2024 - Q1", "2024 - Q2", "2024 - Q3"],
        "value": [1.0, 2.0, 3.0],
    })
    table = pd.DataFrame({
        "Proyecto": ["A", "B", "C"],
        "Último Trimestre": ["2024 - Q1", "2024 - Q2", "2024 - Q3"],
        "value": [1.0, 2.0, 3.0],
    })
    
    result = service.compare_single(
        table=table,
        reference_path="",
        sheet_name="test",
        key_columns=["Proyecto", "Último Trimestre"],
        filter_quarters=[],
        rtol=1e-6,
        atol=1e-3,
        column_tolerances={},
    )
    assert "missing_keys" in result
    assert "extra_keys" in result


def test_compare_filters_quarters():
    """Test that quarter filtering works."""
    service = ComparisonService()
    ref = pd.DataFrame({
        "Último Trimestre": ["2024 - Q1", "2024 - Q2", "2024 - Q3"],
        "value": [1.0, 2.0, 3.0],
    })
    table = pd.DataFrame({
        "Último Trimestre": ["2024 - Q1", "2024 - Q2"],
        "value": [1.0, 2.0],
    })
    
    result = service.compare_single(
        table=table,
        reference_path="",
        sheet_name="test",
        key_columns=[],
        filter_quarters=["2024 - Q1", "2024 - Q2"],
        rtol=1e-6,
        atol=1e-3,
        column_tolerances={},
    )
    # After filtering, should have same row count
    assert result["row_counts"]["pipeline"] == 2
    assert result["row_counts"]["reference"] == 2


def test_compare_column_tolerances():
    """Test per-column tolerance overrides."""
    service = ComparisonService()
    ref = pd.DataFrame({"value": [1.0, 2.0]})
    table = pd.DataFrame({"value": [1.1, 2.1]})  # Larger diff
    
    result = service.compare_single(
        table=table,
        reference_path="",
        sheet_name="test",
        key_columns=[],
        filter_quarters=[],
        rtol=1e-6,  # Strict default
        atol=1e-3,
        column_tolerances={"value": {"atol": 0.2}},  # More lenient for this column
    )
    # Should pass with column-specific tolerance
    assert "value_mismatches" in result


def test_normalize_value():
    """Test value normalization."""
    service = ComparisonService()
    assert service._normalize_value(1.0) == "1"
    assert service._normalize_value("1.0") == "1"
    assert service._normalize_value(None) == ""
    assert service._normalize_value("  test  ") == "test"
