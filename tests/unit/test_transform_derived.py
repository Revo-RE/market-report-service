import pandas as pd

from market_report.application.services.transform import TransformService
from market_report.config.schemas import TableConfig


def test_transform_derives_first_by_quarter():
    raw = {
        "raw": pd.DataFrame(
            {
                "Project": ["Alpha", "Alpha", "Beta"],
                "Quarter": ["2022 - Q3", "2021 - Q4", "2022 - Q1"],
                "Value": [2, 1, 3],
            }
        )
    }
    configs = [
        TableConfig(
            name="historico",
            source_tab="raw",
            column_mappings={"Project": "Project", "Quarter": "Quarter", "Value": "Value"},
        ),
        TableConfig(
            name="proy_nuevos",
            source_tab="raw",
            derived_from="historico",
            group_by=["Project"],
            order_by="Quarter",
            order_by_kind="quarter",
            column_mappings={"Project": "Project", "Quarter": "Quarter", "Value": "Value"},
        ),
    ]

    service = TransformService()
    normalized = service.normalize(raw, configs)

    assert len(normalized["historico"]) == 3
    assert len(normalized["proy_nuevos"]) == 2
    alpha_row = normalized["proy_nuevos"].set_index("Project").loc["Alpha"]
    assert alpha_row["Quarter"] == "2021 - Q4"
