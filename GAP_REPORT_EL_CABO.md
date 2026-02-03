# Reporte GAP – Pipeline de Reporte de Mercado El Cabo

_Fecha: $(date +%Y-%m-%d)_

## 1) Resumen ejecutivo
- El inventario de entrada es consistente a través de 18 archivos trimestrales (2021_Q2–2025_Q3) con 46 columnas compartidas y `Proyecto` único por trimestre. No hay columnas faltantes/extra a través de los trimestres.
- El workbook golden contiene muchas pestañas; solo dos reflejan directamente los datos raw trimestrales: `Histórico_Mercado` (1,205 filas, 12 columnas principales + 9 columnas placeholder vacías) y `Histórico_ProyNuevos` (124 filas, trimestre más temprano único por proyecto).
- El código actual solo renombra/concatena tablas raw y elimina duplicados de `Historico_ProyNuevos`; **no** reproduce la mayoría de las pestañas derivadas downstream (análisis de San José, agregaciones de absorción/stock/ticket/xm2, tipologías, correlaciones, etc.).
- La comparación automatizada muestra `pipeline.csv` (concat raw) vs `golden.csv` (`Histórico_Mercado`): 26 filas existen solo en golden (trimestres más antiguos 2020–2021_Q1); las filas superpuestas coinciden estructuralmente pero los valores numéricos requieren manejo de tolerancia.

## 2) Inventario Excel de entrada (files/elcabo_files/*.xlsx)
- Archivos: 18 archivos trimestrales 2021_Q2 … 2025_Q3; cada uno tiene la hoja `Sheet1`.
- Columnas (46, presentes en todos los archivos): Codigo COL, Proyecto, Desarrollador, Municipio, Segmento, Colonia, Direccion, Último Trimestre, Absorción por Proyecto, Meses de Inventario, Meses en el Mercado, Unidades Totales, Unidades Inventario, Precio Promedio Inv., $M2 Promedio Inv, M2 Promedio Inv, Estatus, Latitud, Longitud, Fecha Inicio Venta, Último Levantamiento, 24 flags de amenidades.
- Los conteos de filas crecen por trimestre (14 → 105); `Proyecto` es único dentro de cada archivo; `Proyecto` + `Último Trimestre` es una clave estable a través de archivos.

## 3) Auditoría del workbook golden (files/elcabo_consolidado/Los Cabos_Insumosv01.xlsx)
- Pestañas (seleccionadas):
  - **Outputs/staging**: `Histórico_Mercado` (1205x21, 24 fórmulas), `Histórico_ProyNuevos` (125x15, sin fórmulas).
  - **IDs/lookup**: `SanJosé_ID` (71x10), `Insumos_HistóricosSanJosé` (25x13, 47 fórmulas).
  - **Diagnósticos/amenidades**: `Insumos_DiagAnalisAmenSanJosé` (31x34, 67 fórmulas) – contiene ratios calculados como `IFERROR(I2/E2,0)` y `J2/L2`.
  - **Tipologías**: `Insumos_TipologíasyMOISanJosé` (261x16, 530 fórmulas), `Tablas_Tipologías_SJ` (91x18, 172 fórmulas), `SJ_1R…SJ_5R`, `SJ_MESES_*`.
  - **Pestañas de métricas derivadas San José**: `SJ_Abs `, `SJ_Stock `, `SJ_Inventario `, `SJ_Ticket `, `SJ_$xm2 `, `SJ_Superficie`, `SJ_Meses_Inv`, `SJ_Stock_Abs  `, `SJ_Inventario_Abs  `, `SJ_Ticket_Abs  `, `SJ_$xm2_Abs  `, `SJ_Sup_Abs `, `SJ_Meses_Inv_Abs `, `SJ_Correlaciones` (cada una 38–42 filas, 53–57 cols, ~900 fórmulas). Las fórmulas principalmente extraen bloques de `Insumos_DiagAnalisAmenSanJosé` (ej., `=Insumos_DiagAnalisAmenSanJosé!B2` / offsets de fila por métrica).
- Reglas observadas (pseudocódigo):
  - **Histórico_Mercado**: apilado vertical de todos los trimestres; columnas limitadas a 12 campos principales; incluye trimestres más antiguos (2020_Q1–2021_Q1) no presentes en nuestra carpeta raw; las columnas placeholder Unnamed están vacías.
  - **Histórico_ProyNuevos**: por proyecto, mantener el `Último Trimestre` más temprano; mismas columnas que `Histórico_Mercado`; eliminar duplicados por `Proyecto` (trimestre más temprano).
  - **Flujos San José**: las hojas indexan proyectos (probablemente en San José) vía `SanJosé_ID`; `Insumos_HistóricosSanJosé`/`Insumos_TipologíasyMOISanJosé` calculan ratios (absorción/inventario/ticket/$xm2/superficie/meses) usando IFERROR(divide,0); `Insumos_DiagAnalisAmenSanJosé` agrega/normaliza métricas de amenidades + absorción; las pestañas `SJ_*` referencian bloques pre-calculados celda-a-celda para construir diferentes cortes de métricas (Abs, Stock, Inventario, Ticket, $xm2, Sup, Meses Inv, y variantes "_Abs"). La pestaña de correlaciones extrae las mismas entradas para cálculos estadísticos.
  - **Validaciones implícitas**: columnas clave presentes (Proyecto, Último Trimestre); las fórmulas protegen divisiones con IFERROR(...,0); los datos aparecen ordenados por trimestre; no hay duplicados en las claves.

## 4) Mapeo vs código actual
- **Implementado (parcial)**
  - Concatenar carpeta Excel en tabla `raw` vía adaptador `adapters/data_sources/local_excel_folder.py` (lee todos los *.xlsx, sheet1).
  - Normalizar (renombrar/recortar columnas) en `historico_mercado` usando column_mappings en `configs/projects/el_cabo_excel.json` (`TransformService.normalize`).
  - Derivar `historico_proy_nuevos` eliminando duplicados del trimestre más temprano por proyecto con ordenamiento de trimestres (`TransformService.normalize` ruta de tabla derivada).
  - QC básico: verificaciones de columnas requeridas/no-nulas (`application/services/quality.py:validate`).
  - Hook de comparación con referencia existe pero actualmente solo tolera diferencias numéricas/str mínimas.

- **Falta**
  - Todas las tablas específicas de San José, agregaciones de tipologías, cálculos de diagnósticos/amenidades, correlaciones (`Insumos_*`, `SJ_*`, `Tablas_Tipologías_SJ`, `SanJosé_ID`). No hay adaptadores/servicios para generarlas.
  - Reglas de negocio/limpieza más allá de renombrar (sin cálculo IFERROR/ratio, sin filtrado por municipio/segmento, sin normalizaciones de amenidades).
  - Inclusión de datos pre-2021 presentes en golden (26 filas con trimestres 2020–2021_Q1).
  - Mapeos PPT/gráficas para métricas de San José (la config de gráficas es solo placeholder).
  - Lógica de generación de narrativa más allá del stub.

- **Diferente**
  - La comparación con referencia actualmente falla debido a tolerancia estricta y desajuste en conjuntos de filas (golden tiene trimestres más antiguos extra). Necesita tolerancias configurables y filtros de trimestre.
  - El código `QualityService.compare_to_reference` está parcialmente malformado (strings escapados de un patch fallido) y usa tolerancia fija (rtol=1e-6, atol=1e-3); debería ser reparado y parametrizado.
  - La config `el_cabo_excel.json` solo mapea 12 columnas de raw pero deja 34 columnas sin mapear; golden usa 12, pero San José downstream necesita más (amenidades, geos, fechas).

## 5) Comparación automatizada (artefactos producidos)
- Generados `pipeline.csv` (concat raw, 1179 filas x 46 cols) y `golden.csv` (`Histórico_Mercado` limpiado, 1205 filas x 12 cols) en la raíz del repo.
- Conjuntos de columnas: pipeline tiene 46, golden 12 (golden subconjunto de métricas principales).
- Diff de filas en cols comunes (clave `Proyecto`,`Último Trimestre`): 1179 filas coinciden; 26 filas son solo-golden (trimestres más antiguos no en carpeta de entrada); 0 solo-pipeline.
- Estadísticas numéricas (cols comunes): deltas de media ligeros (ej., `Unidades Inventario` 16.03 vs 16.38) impulsados por trimestres más antiguos faltantes; diferencias de valores individuales dentro de ~1e-3 cuando están alineados.

## 6) Top 5 riesgos
- Falta lógica de transformación San José (tipologías, diagnósticos de amenidades, correlaciones) significa que la mayoría del workbook consolidado no se reproduce; las métricas/gráficas downstream serán incorrectas o vacías.
- QC de referencia frágil: `QualityService.compare_to_reference` actualmente roto/estricto; bloqueará el pipeline o pasará por alto silenciosamente problemas de tolerancia numérica.
- Brecha de cobertura de entrada: golden incluye trimestres no presentes en carpeta raw; sin backfill, los conteos de filas y métricas de series temporales divergen.
- Columnas sin mapear (34/46) descartan datos necesarios para análisis de tipología/amenidades/geo.
- Falta de tests alrededor de transformaciones/ordenamiento de trimestres hace que la lógica de dedupe-por-más-temprano sea frágil para nuevos datos.

## 7) Plan de acción (tareas PR)
- [ ] Arreglar implementación `QualityService.compare_to_reference` (limpiar strings, tolerancias configurables, permitir filtros de subconjunto/trimestre) y agregar tests unitarios.
- [ ] Extender capa de transformación para retener las 46 columnas y producir tablas staged para San José (IDs, diagnósticos, tipologías) reflejando fórmulas de hoja golden (divisiones IFERROR, ratios, flags de amenidades).
- [ ] Implementar servicios de agregación para cortes de métricas `SJ_*` extrayendo de bloques de diagnósticos (Abs, Stock, Inventario, Ticket, $xm2, Sup, Meses Inv, variantes Abs) y correlaciones.
- [ ] Ingerir/alinear trimestres históricos pre-2021 (ya sea agregar archivos faltantes o parametrizar comparación a cobertura conocida) para que los conteos de filas de `Histórico_Mercado` coincidan.
- [ ] Conectar configs de gráficas/PPT para nuevas tablas y agregar hooks de narrativa una vez que existan las métricas.

## 8) Recomendaciones de tests
- Unit: ordenamiento de trimestres y dedupe para `historico_proy_nuevos` (trimestre más temprano mantenido), helper de comparación de tolerancia numérica, cálculos de ratios tipo IFERROR (divide-by-zero -> 0).
- Integración: transformación end-to-end produciendo `historico_mercado` y `historico_proy_nuevos` coincidiendo con golden (dentro de tolerancia) usando fixtures para 2–3 trimestres; agregar fixture cubriendo proyecto duplicado a través de trimestres.
- Snapshot: snapshots CSV alineados con golden para `historico_mercado`, `historico_proy_nuevos`, y tablas clave de San José una vez implementadas.
- Regresión: verificaciones basadas en estadísticas (conteos de filas, proyectos únicos, min/max para absorción/meses inv) por release.

## 9) Matriz de reglas (OK/Falta/Diferente)
- OK: concat trimestres raw -> `historico_mercado` (solo estructura); dedupe trimestre-más-temprano -> `historico_proy_nuevos`.
- Falta: diagnósticos/amenidades/tipologías San José (`Insumos_*`), cortes de métricas SJ_*, correlaciones, reglas de normalización de amenidades/geo, mapeos PPT/gráficas, generación de narrativa.
- Diferente: tolerancia/lógica de comparación con referencia; cobertura de trimestres más antiguos; columnas sin mapear descartadas en transformación.

## 10) Notas
- Evidencia de diffs: indicador de merge muestra 26 filas solo-golden (probablemente 2020–2021_Q1). Los diffs numéricos caen dentro de ~1e-3 en filas superpuestas.
- Las columnas placeholder Unnamed en golden están vacías; seguro descartarlas durante la comparación.
