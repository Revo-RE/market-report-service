# Guía: Configurar Google Cloud para Google Drive API

## Paso 1: Crear un nuevo proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Si no tienes cuenta, créala con tu email (valentina@revore.mx)
3. Haz clic en el selector de proyectos (arriba a la izquierda)
4. Haz clic en **"Nuevo Proyecto"**
5. Ingresa un nombre (ej: `market-report-service`)
6. Haz clic en **"Crear"**

## Paso 2: Habilitar Google Drive API

1. En el menú lateral, ve a **"APIs y servicios" > "Biblioteca"**
2. Busca **"Google Drive API"**
3. Haz clic en **"Google Drive API"**
4. Haz clic en **"HABILITAR"**

## Paso 3: Crear una cuenta de servicio

1. En el menú lateral, ve a **"IAM y administración" > "Cuentas de servicio"**
2. Haz clic en **"+ CREAR CUENTA DE SERVICIO"**
3. Ingresa:
   - **Nombre**: `market-report-drive` (o el que prefieras)
   - **Descripción**: `Cuenta de servicio para subir archivos a Google Drive`
4. Haz clic en **"Crear y continuar"**
5. En "Otorgar acceso a esta cuenta de servicio", haz clic en **"Continuar"** (puedes saltar este paso)
6. Haz clic en **"Listo"**

## Paso 4: Crear y descargar la clave JSON

1. En la lista de cuentas de servicio, haz clic en la que acabas de crear
2. Ve a la pestaña **"Claves"**
3. Haz clic en **"Agregar clave" > "Crear nueva clave"**
4. Selecciona **"JSON"**
5. Haz clic en **"Crear"**
6. Se descargará automáticamente un archivo JSON (guárdalo en un lugar seguro)

## Paso 5: Compartir la carpeta de Google Drive con la cuenta de servicio

1. Abre la carpeta de Google Drive donde quieres subir los archivos:
   https://drive.google.com/drive/u/1/folders/1e-8X3B1pIQ023Zaie5wNzqSKSXr45o9l

2. Haz clic en **"Compartir"** (botón azul arriba a la derecha)

3. En el campo de email, pega el **client_email** de tu archivo JSON descargado
   - Formato: `nombre-cuenta@proyecto.iam.gserviceaccount.com`
   - Ejemplo: `market-report-drive@tu-proyecto.iam.gserviceaccount.com`

4. Dale permisos de **"Editor"** o **"Colaborador"**

5. Haz clic en **"Enviar"**

## Paso 6: Actualizar credentials.json

1. Abre el archivo JSON que descargaste
2. Copia todo su contenido
3. Reemplaza el contenido de `credentials.json` en este proyecto con el nuevo contenido

## Paso 7: Probar la subida

Ejecuta:
```bash
cd /Users/poiowtf/market-report-service
export GOOGLE_SERVICE_ACCOUNT_FILE="${PWD}/credentials.json"
python3 test_upload.py
```

O ejecuta el pipeline completo:
```bash
PYTHONPATH="${PWD}/src" python3 -m market_report.cli --config configs/projects/el_cabo_consolidado_drive.json
```

## Notas importantes

- El archivo JSON de credenciales es **sensible** - no lo subas a Git
- La cuenta de servicio debe tener acceso a la carpeta de Google Drive
- El `client_email` debe ser del formato `xxxxx@proyecto.iam.gserviceaccount.com`
