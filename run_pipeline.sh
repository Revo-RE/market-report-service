#!/bin/bash

# Script para ejecutar el pipeline de Market Report

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Market Report Pipeline ===${NC}\n"

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Debes ejecutar este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Configurar PYTHONPATH
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Verificar credenciales
if [ -z "$GOOGLE_SERVICE_ACCOUNT_FILE" ]; then
    if [ -f "credentials.json" ]; then
        export GOOGLE_SERVICE_ACCOUNT_FILE="${PWD}/credentials.json"
        echo -e "${YELLOW}⚠️  Usando credentials.json del directorio actual${NC}"
    else
        echo -e "${RED}Error: GOOGLE_SERVICE_ACCOUNT_FILE no está configurado y credentials.json no existe${NC}"
        echo -e "${YELLOW}Ejecuta: export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json${NC}"
        exit 1
    fi
fi

# Verificar que el archivo de credenciales existe
if [ ! -f "$GOOGLE_SERVICE_ACCOUNT_FILE" ]; then
    echo -e "${RED}Error: Archivo de credenciales no encontrado: $GOOGLE_SERVICE_ACCOUNT_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Credenciales configuradas: $GOOGLE_SERVICE_ACCOUNT_FILE${NC}"

# Configuración por defecto
CONFIG_FILE="${1:-configs/projects/el_cabo_consolidado_drive.json}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Archivo de configuración no encontrado: $CONFIG_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Usando configuración: $CONFIG_FILE${NC}\n"

# Ejecutar el pipeline
echo -e "${GREEN}Ejecutando pipeline...${NC}\n"
python3 -m market_report.cli --config "$CONFIG_FILE"

echo -e "\n${GREEN}✅ Pipeline completado${NC}"
