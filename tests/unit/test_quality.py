import pandas as pd
import pytest

from market_report.application.services.quality import QCError, QualityService
from market_report.config.schemas import TableConfig


def test_quality_missing_columns():
    tables = {"inventory": pd.DataFrame({"unit_id": ["A-1"]})}
    configs = [
        TableConfig(
            name="inventory",
            source_tab="Inventory",
            column_mappings={"unit_id": "Unit ID", "status": "Status"},
            required_columns=["unit_id", "status"],
            required_fields=["unit_id", "status"],
        )
    ]
    service = QualityService()

    with pytest.raises(QCError) as exc:
        service.validate(tables, configs)

    assert "missing columns" in str(exc.value)
