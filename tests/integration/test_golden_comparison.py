from __future__ import annotations

import pandas as pd
import pytest

from market_report.application.services.compare import ComparisonService
from market_report.application.services.transform import TransformService
from market_report.config.schemas import TableConfig


@pytest.fixture
def sample_raw_data():
    """Sample raw data matching El Cabo structure."""
    return pd.DataFrame({
        "Proyecto": ["Proyecto A", "Proyecto B", "Proyecto A"],
        "Desarrollador": ["Dev 1", "Dev 2", "Dev 1"],
        "Último Trimestre": ["2024 - Q1", "2024 - Q2", "2024 - Q3"],
        "Absorción por Proyecto": [1.0, 2.0, 0.5],
        "Meses de Inventario": [10.0, 15.0, 12.0],
        "Unidades Totales": [100, 200, 150],
        "Unidades Inventario": [50, 100, 75],
    })


def test_historico_mercado_structure(sample_raw_data):
    """Test that historico_mercado maintains correct structure."""
    config = TableConfig(
        name="historico_mercado",
        source_tab="raw",
        column_mappings={
            "Proyecto": "Proyecto",
            "Desarrollador": "Desarrollador",
            "Último Trimestre": "Último Trimestre",
            "Absorción por Proyecto": "Absorción por Proyecto",
            "Meses de Inventario": "Meses de Inventario",
            "Unidades Totales": "Unidades Totales",
            "Unidades Inventario": "Unidades Inventario",
        },
        required_columns=["Proyecto", "Último Trimestre"],
        key_columns=["Proyecto", "Último Trimestre"],
    )
    
    service = TransformService()
    normalized = service.normalize({"raw": sample_raw_data}, [config])
    
    result = normalized["historico_mercado"]
    assert len(result) == 3
    assert "Proyecto" in result.columns
    assert "Último Trimestre" in result.columns
    assert result["Proyecto"].nunique() == 2  # 2 unique projects


def test_historico_proy_nuevos_dedupe(sample_raw_data):
    """Test that historico_proy_nuevos keeps earliest quarter per project."""
    base_config = TableConfig(
        name="historico_mercado",
        source_tab="raw",
        column_mappings={"Proyecto": "Proyecto", "Último Trimestre": "Último Trimestre"},
    )
    derived_config = TableConfig(
        name="historico_proy_nuevos",
        source_tab="raw",
        derived_from="historico_mercado",
        group_by=["Proyecto"],
        order_by="Último Trimestre",
        order_by_kind="quarter",
        column_mappings={"Proyecto": "Proyecto", "Último Trimestre": "Último Trimestre"},
    )
    
    service = TransformService()
    normalized = service.normalize({"raw": sample_raw_data}, [base_config, derived_config])
    
    result = normalized["historico_proy_nuevos"]
    assert len(result) == 2  # One row per project
    assert result["Último Trimestre"].iloc[0] == "2024 - Q1"  # Earliest for Proyecto A
    assert result["Último Trimestre"].iloc[1] == "2024 - Q2"  # Earliest for Proyecto B


def test_compare_against_golden_structure(tmp_path, sample_raw_data):
    """Test comparison structure matches expected format."""
    # Create a mock golden file
    golden_path = tmp_path / "golden.xlsx"
    golden_df = pd.DataFrame({
        "Proyecto": ["Proyecto A", "Proyecto B"],
        "Último Trimestre": ["2024 - Q1", "2024 - Q2"],
        "Unidades Totales": [100, 200],
    })
    with pd.ExcelWriter(golden_path, engine="openpyxl") as writer:
        golden_df.to_excel(writer, sheet_name="Histórico_Mercado", index=False)
    
    service = ComparisonService()
    table = pd.DataFrame({
        "Proyecto": ["Proyecto A", "Proyecto B"],
        "Último Trimestre": ["2024 - Q1", "2024 - Q2"],
        "Unidades Totales": [100, 200],
    })
    
    result = service.compare_single(
        table=table,
        reference_path=str(golden_path),
        sheet_name="Histórico_Mercado",
        key_columns=["Proyecto", "Último Trimestre"],
        filter_quarters=[],
        rtol=1e-6,
        atol=1e-3,
        column_tolerances={},
    )
    
    assert "status" in result
    assert "row_counts" in result
    assert "column_diff" in result
    assert result["row_counts"]["pipeline"] == 2
    assert result["row_counts"]["reference"] == 2
