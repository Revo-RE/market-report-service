# Market Report Service

Servicio para generar reportes de mercado inmobiliario a partir de datos de Google Sheets o archivos Excel locales.

## Características del MVP

- ✅ **Ingesta de datos**: Desde Google Sheets API o archivos Excel locales
- ✅ **Transformación/Normalización**: Conversión a tablas canónicas con mapeo de columnas
- ✅ **QC (Quality Control)**: Validaciones robustas (columnas faltantes, tipos inválidos, rangos, vacíos críticos)
- ✅ **Cálculo de métricas**: Inventario, absorción, precios
- ✅ **Render de gráficas**: Generación de imágenes con matplotlib
- ✅ **Comparación con referencia**: Validación contra consolidado de referencia

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración Rápida

1. **Configura las credenciales de Google** (ver sección siguiente)
2. **Comparte los Google Sheets/Drive** con el email de la service account
3. **Ejecuta el pipeline**:

```bash
export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json
python -m market_report.cli --config configs/projects/el_cabo_google_drive.json
```

## Configuración de Google Sheets API

Para usar Google Sheets o Google Drive como fuente de datos, necesitas configurar autenticación:

### Opción 1: Service Account (Recomendado)

1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
2. Habilita las APIs:
   - Google Sheets API
   - Google Drive API
3. Crea una Service Account y descarga el archivo JSON de credenciales
4. Comparte los Google Sheets/Drive folders con el email de la service account (ej: `axel-56@gleaming-vine-456821-m8.iam.gserviceaccount.com`)
5. Configura la variable de entorno apuntando al archivo de credenciales:

```bash
# Opción A: Usar ruta absoluta
export GOOGLE_SERVICE_ACCOUNT_FILE=/Users/tu-usuario/credentials.json

# Opción B: Si lo copias al proyecto (NO recomendado para producción)
export GOOGLE_SERVICE_ACCOUNT_FILE=./credentials.json
```

**⚠️ IMPORTANTE**: 
- **NO** subas el archivo `credentials.json` al repositorio (debe estar en `.gitignore`)
- El archivo contiene credenciales sensibles
- Comparte los Google Sheets/Drive folders con el email de la service account (ej: `axel-56@gleaming-vine-456821-m8.iam.gserviceaccount.com`)

El archivo `credentials.json` debe tener este formato:

```json
{
  "type": "service_account",
  "project_id": "tu-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "tu-service-account@project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

**Importante**: Asegúrate de compartir los Google Sheets y carpetas de Drive con el email de la service account para que tenga acceso de lectura.

### Opción 2: OAuth2

Sigue las instrucciones en [gspread documentation](https://gspread.readthedocs.io/en/latest/oauth2.html)

## Uso

### Ejecutar pipeline para generar consolidado desde Google Drive

**Paso 1: Configurar credenciales**
```bash
export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json
```

**Paso 2: Ejecutar pipeline**
```bash
python -m market_report.cli --config configs/projects/el_cabo_consolidado_drive.json
```

El pipeline:
1. ✅ Lee los 18 archivos Excel desde Google Drive
2. ✅ Genera todas las pestañas del golden (33 pestañas)
3. ✅ Compara contra el golden de referencia
4. ✅ Genera el Excel consolidado: `Los_Cabos_Insumos_Consolidado.xlsx`
5. ✅ Sube el consolidado a Google Drive (carpeta destino configurada)
6. ✅ Exporta CSVs por pestaña para auditoría

### Configuraciones disponibles

- `el_cabo_consolidado_drive.json`: **Recomendado** - Lee 18 sheets desde Google Drive y genera consolidado
- `el_cabo_consolidado.json`: Lee archivos Excel locales desde `files/elcabo_files/` y genera consolidado
- `el_cabo_excel.json`: Configuración básica con Excel locales (sin replicación completa)
- `el_cabo_google_drive.json`: Configuración genérica con Google Drive

### Estructura de configuración

```json
{
  "project_name": "El Cabo",
  "google_drive_folder": {
    "folder_url": "https://drive.google.com/drive/u/1/folders/FOLDER_ID",
    "sheet_name": "Sheet1",
    "table_key": "raw"
  },
  "reference": {
    "path": "files/elcabo_consolidado/Los Cabos_Insumosv01.xlsx",
    "sheet": "Histórico_Mercado",
    "table": "historico_mercado"
  },
  "tables": [...],
  "charts": [...],
  "ppt": {...}
}
```

## Estructura del Proyecto

```
market-report-service/
├── src/market_report/
│   ├── adapters/          # Adaptadores para fuentes de datos, renderers, etc.
│   ├── application/         # Servicios de aplicación (pipeline, transform, quality, metrics)
│   ├── config/           # Configuración y schemas
│   ├── domain/           # Lógica de dominio (calculators, models, rules)
│   └── ports/            # Interfaces/contratos
├── configs/projects/     # Configuraciones de proyectos
├── files/                # Archivos de datos y referencias
└── templates/            # Plantillas PPTX
```

## Componentes Principales

### Pipeline

El pipeline orquesta todo el flujo:
1. Carga de datos desde fuente configurada
2. Normalización a tablas canónicas
3. Validación QC
4. Comparación con referencia (si está configurada)
5. Cálculo de métricas
6. Generación de gráficas
7. Generación de PPT

### Quality Control

Validaciones implementadas:
- Columnas requeridas presentes
- Campos críticos no vacíos
- Tipos de datos válidos (numéricos donde corresponde)
- Rangos razonables para métricas numéricas
- Comparación detallada con consolidado de referencia

### Métricas

Calculadas automáticamente:
- **Inventario**: Unidades totales, inventario, meses de inventario, meses en mercado
- **Absorción**: Absorción total, promedio, por trimestre
- **Precios**: Precio promedio inventario, precio por M2, M2 promedio

## Desarrollo

### Ejecutar tests

```bash
pytest tests/
```

### Agregar nueva fuente de datos

Implementa la interfaz `DataSource` en `ports/data_source.py`:

```python
class MyDataSource(DataSource):
    def load(self) -> Dict[str, pd.DataFrame]:
        # Tu implementación
        pass
```

## Enlaces de Referencia

- Carpeta con 18 sheets: https://drive.google.com/drive/u/1/folders/1Npx2u4QrHciP50lBe_tige1YRZhw_jNW
- Consolidado de referencia: https://docs.google.com/spreadsheets/d/1pRJEQVUIKI6OvhxWJ3vNekAZEpDOKFKM/edit?gid=923663102#gid=923663102
- Carpeta de salida consolidado: https://drive.google.com/drive/u/1/folders/1e-8X3B1pIQ023Zaie5wNzqSKSXr45o9l
