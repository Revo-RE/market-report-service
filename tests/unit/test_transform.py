import pandas as pd

from market_report.application.services.transform import TransformService
from market_report.config.schemas import TableConfig


def test_transform_normalizes_columns():
    raw = {
        "Inventory": pd.DataFrame({"Unit ID": ["A-1"], "Status": ["Available"]})
    }
    configs = [
        TableConfig(
            name="inventory",
            source_tab="Inventory",
            column_mappings={"unit_id": "Unit ID", "status": "Status"},
        )
    ]
    service = TransformService()
    normalized = service.normalize(raw, configs)

    assert "inventory" in normalized
    assert list(normalized["inventory"].columns) == ["unit_id", "status"]
