#!/usr/bin/env python3
"""Script de prueba para verificar la subida a Google Drive."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from market_report.adapters.storage.google_drive_upload import GoogleDriveUploader

def main():
    # Set credentials
    creds_file = Path(__file__).parent / "credentials.json"
    if not creds_file.exists():
        print(f"❌ No se encontró credentials.json en {creds_file}")
        return 1
    
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = str(creds_file)
    
    # Test file (use the latest generated Excel)
    output_dir = Path(__file__).parent / "outputs"
    latest_run = sorted(output_dir.glob("*/"))[-1] if output_dir.exists() else None
    
    if not latest_run:
        print("❌ No se encontró ningún archivo generado. Ejecuta el pipeline primero.")
        return 1
    
    excel_file = latest_run / "Los_Cabos_Insumos_Consolidado.xlsx"
    if not excel_file.exists():
        print(f"❌ No se encontró el archivo Excel en {excel_file}")
        return 1
    
    # Folder URL
    folder_url = "https://drive.google.com/drive/u/1/folders/1e-8X3B1pIQ023Zaie5wNzqSKSXr45o9l"
    
    print(f"📤 Subiendo {excel_file} a Google Drive...")
    print(f"📁 Carpeta: {folder_url}")
    
    try:
        uploader = GoogleDriveUploader()
        file_id = uploader.upload_file(excel_file, folder_url, "Los_Cabos_Insumos_Consolidado.xlsx")
        print(f"✅ Archivo subido exitosamente!")
        print(f"🔗 File ID: {file_id}")
        print(f"🌐 URL: https://drive.google.com/file/d/{file_id}/view")
        return 0
    except Exception as e:
        print(f"❌ Error al subir: {e}")
        print("\n💡 Verifica que:")
        print("   1. La cuenta de servicio tenga acceso a la carpeta de Google Drive")
        print("   2. El archivo credentials.json sea válido")
        print("   3. Tengas conexión a internet")
        return 1

if __name__ == "__main__":
    sys.exit(main())
