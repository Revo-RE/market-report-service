# Quick Start - Generar Consolidado desde Google Drive

## Pasos Rápidos

### 1. Configurar credenciales

```bash
export GOOGLE_SERVICE_ACCOUNT_FILE=/Users/poiowtf/market-report-service/credentials.json
```

### 2. Verificar que las carpetas estén compartidas

Asegúrate de que la service account tenga acceso a:
- **Carpeta de entrada** (18 archivos): `https://drive.google.com/drive/u/1/folders/1Npx2u4QrHciP50lBe_tige1YRZhw_jNW`
- **Carpeta de salida** (donde se guardará el consolidado): `https://drive.google.com/drive/u/1/folders/1e-8X3B1pIQ023Zaie5wNzqSKSXr45o9l`

Comparte ambas carpetas con: `axel-56@gleaming-vine-456821-m8.iam.gserviceaccount.com`

### 3. Ejecutar el pipeline

**Opción A: Usar el script de ejecución (recomendado)**
```bash
cd /Users/poiowtf/market-report-service
./run_pipeline.sh
```

O especificar otra configuración:
```bash
./run_pipeline.sh configs/projects/el_cabo_consolidado.json
```

**Opción B: Ejecutar directamente**
```bash
cd /Users/poiowtf/market-report-service
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
export GOOGLE_SERVICE_ACCOUNT_FILE="${PWD}/credentials.json"
python3 -m market_report.cli --config configs/projects/el_cabo_consolidado_drive.json
```

### 4. Revisar resultados

El pipeline generará:
- ✅ Excel consolidado: `outputs/{run_id}/Los_Cabos_Insumos_Consolidado.xlsx`
- ✅ CSVs por pestaña: `outputs/{run_id}/pipeline_tabs/*.csv`
- ✅ Reportes de comparación: `artifacts/diff_reports/*.json`
- ✅ El Excel se subirá automáticamente a Google Drive

## Solución de Problemas

### Error: "Google Sheets authentication failed"
- Verifica que `GOOGLE_SERVICE_ACCOUNT_FILE` esté configurado
- Verifica que el archivo `credentials.json` exista y sea válido

### Error: "No Excel/Sheets files found in folder"
- Verifica que la carpeta de Google Drive esté compartida con la service account
- Verifica que la URL de la carpeta sea correcta en la configuración

### Error: "File not found" al subir a Drive
- Verifica que la carpeta de destino esté compartida con la service account
- Verifica que la URL de destino sea correcta en `output.drive_folder_url`

## Estructura de Salida

```
outputs/
└── {run_id}/
    ├── Los_Cabos_Insumos_Consolidado.xlsx  # Excel consolidado
    ├── pipeline_tabs/                       # CSVs por pestaña
    │   ├── Histórico_Mercado.csv
    │   ├── SanJosé_ID.csv
    │   └── ...
    └── artifacts/
        └── diff_reports/                    # Comparaciones con golden
            ├── Histórico_Mercado_diff.json
            └── ...
```
