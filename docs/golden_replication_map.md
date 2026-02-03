# Golden Replication Map - El Cabo

## Tab inventory

| Tab | Rows | Cols | Formulas | DiagRefRatio | Category | Depends On |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Histórico_Mercado | 1206 | 21 | 24 | 0.00 | base |  |
| Histórico_ProyNuevos | 125 | 15 | 0 | 0.00 | base |  |
| SanJosé_ID | 71 | 10 | 0 | 0.00 | base |  |
| Insumos_HistóricosSanJosé | 25 | 13 | 47 | 0.00 | derived |  |
| Abs_SanJosé2025 | 40 | 25 | 290 | 0.00 | derived |  |
| Insumos_DiagAnalisAmenSanJosé | 31 | 34 | 67 | 0.00 | derived |  |
| Insumos_TipologíasyMOISanJosé | 261 | 16 | 530 | 0.00 | derived |  |
| SJ_1R | 14 | 16 | 0 | 0.00 | derived |  |
| SJ_1.5R | 4 | 16 | 0 | 0.00 | derived |  |
| SJ_2R | 76 | 16 | 0 | 0.00 | derived |  |
| SJ_3R | 64 | 16 | 0 | 0.00 | derived |  |
| SJ_3.5R | 3 | 16 | 0 | 0.00 | derived |  |
| SJ_4R | 24 | 16 | 0 | 0.00 | derived |  |
| SJ_5R | 3 | 16 | 0 | 0.00 | derived |  |
| Tablas_Tipologías_SJ | 91 | 18 | 172 | 0.01 | derived |  |
| SJ_MESES_1R | 178 | 34 | 9 | 0.00 | mirror? |  |
| SJ_MESES_2R | 178 | 34 | 17 | 0.00 | mirror? |  |
| SJ_MESES_3R | 178 | 34 | 16 | 0.00 | mirror? |  |
| SJ_Abs  | 39 | 57 | 929 | 0.34 | mirror? |  |
| SJ_Stock  | 38 | 53 | 930 | 0.34 | mirror? |  |
| SJ_Inventario  | 39 | 53 | 930 | 0.34 | mirror? |  |
| SJ_Ticket  | 39 | 53 | 900 | 0.35 | mirror? |  |
| SJ_$xm2  | 40 | 53 | 900 | 0.35 | mirror? |  |
| SJ_Superficie | 40 | 53 | 900 | 0.35 | mirror? |  |
| SJ_Meses_Inv | 40 | 53 | 900 | 0.35 | mirror? |  |
| SJ_Stock_Abs   | 38 | 53 | 930 | 0.34 | mirror? |  |
| SJ_Inventario_Abs   | 39 | 53 | 930 | 0.34 | mirror? |  |
| SJ_Ticket_Abs   | 39 | 53 | 929 | 0.34 | mirror? |  |
| SJ_$xm2_Abs   | 40 | 53 | 929 | 0.34 | mirror? |  |
| SJ_Sup_Abs  | 40 | 53 | 929 | 0.34 | mirror? |  |
| SJ_Meses_Inv_Abs  | 42 | 53 | 929 | 0.34 | mirror? |  |
| SJ_Correlaciones | 38 | 25 | 613 | 0.52 | mirror |  |

## Observed dependencies (from formulas)

This section lists tabs that reference other tabs via formulas. Use it to build the DAG.


## Notes / hypotheses to confirm

- `Histórico_Mercado` likely stacks all quarterly raw data (12 core columns) and keeps Unnamed columns empty.
- `Histórico_ProyNuevos` likely dedupes by Proyecto, keeping earliest Último Trimestre.
- `Insumos_*` tabs compute ratios with IFERROR(divide,0) and feed most SJ_* tabs.
- Tabs marked `mirror?` should be validated: confirm if they only re-map blocks (cell references) from `Insumos_DiagAnalisAmenSanJosé`.
- If a tab has no dependencies and 0 formulas, it is likely a base or static lookup tab and must be regenerated from raw data or provided mapping rules.