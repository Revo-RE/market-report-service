from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ProjectMetrics:
    stock_inicial: float | None = None
    ventas: float | None = None
    absorcion: float | None = None
    absorcion_historica: float | None = None
    meses_inventario: float | str | None = None
    meses_mercado: float | None = None
    inventario: float | None = None
    ticket: float | None = None
    xm2: float | None = None
    superficie: float | None = None


@dataclass
class Project:
    codigo: str
    proyecto: str
    desarrollador: str | None = None
    municipio: str | None = None
    segmento: str | None = None
    colonia: str | None = None
    direccion: str | None = None
    ultimo_trimestre: str | None = None
    estatus: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    fecha_inicio: str | None = None
    ultimo_levantamiento: str | None = None
    amenidades: Dict[str, Any] = field(default_factory=dict)
    metrics: ProjectMetrics = field(default_factory=ProjectMetrics)
