from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd

from market_report.domain.calculators.aggregations import (
    ensure_columns,
    normalize_key,
    quarter_key,
    round_or_keep,
    short_id,
    weighted_avg,
)


@dataclass
class CalculationEngineService:
    """Compute Ids, Historico, and Data tables for MVP output."""

    _IDS_COLUMNS = ["Proyecto", "Desarrollador", "ID"]
    _HIST_COLUMNS = [
        "Trimestre",
        "Proyectos_A",
        "Proyectos_N",
        "Stock_Inicial_A",
        "Stock_Inicial_N",
        "Inventario",
        "Ticket",
        "$xm2",
        "Superficie",
        "Ventas",
        "Absorcion",
        "Meses_Inventario",
    ]
    _DATA_COLUMNS = [
        "Proyecto",
        "Desarrollador",
        "ID",
        "Stock_Inicial",
        "Ventas",
        "Absorcion",
        "Absorcion_H",
        "Meses_Inventario",
        "Meses_Mercado",
        "Inventario",
        "Ticket",
        "$xm2",
        "Superficie",
        "Segmento",
        "Estatus",
        "Latitud",
        "Longitud",
        "Fecha_Inicio",
        "Ultimo_Levantamiento",
        "Alberca",
        "Asadores",
        "Bar",
        "Canchas Deportivas",
        "Casa Club",
        "Fogatero",
        "Gimnasio",
        "Jacuzzi",
        "Ludoteca",
        "Pet Zone",
        "Pista de Jogging ",
        "Sala de Cine",
        "Salón de Usos Multiples",
        "Salón de Yoga",
        "Sauna",
        "Spa",
        "Terraza",
    ]
    _TIPOLOGIAS_COLUMNS = [
        "Codigo COL",
        "ID",
        "Proyecto",
        "Desarrollador",
        "Tipo de Modelo",
        "Nombre Modelo",
        "Ticket",
        "$xm2",
        "Superficie",
        "Dormitorios",
        "Bathroom",
        "Cajones",
        "Stock Inicial",
        "Inventario",
        "Meses en Mercado",
        "Ventas",
        "Absorcion",
    ]

    _AMENITY_MAP = {
        "Alberca": "Alberca",
        "Asadores": "Asadores",
        "Bar": "Bar",
        "Canchas Deportivas": "Canchas Deportivas",
        "Casa Club": "Casa Club",
        "Fogatero": "Fogatero",
        "Gimnasio": "Gimnasio",
        "Jacuzzi": "Jacuzzi",
        "Ludoteca/ Juegos Infantiles": "Ludoteca",
        "Pet Zone": "Pet Zone",
        "Pista de Jogging / Vitapista": "Pista de Jogging ",
        "Sala de Cine / TV": "Sala de Cine",
        "Salón de Usos Multiples": "Salón de Usos Multiples",
        "Salón de Yoga": "Salón de Yoga",
        "Sauna": "Sauna",
        "Spa": "Spa",
        "Terraza": "Terraza",
    }

    def build_minimal(
        self,
        raw_clean: pd.DataFrame,
        layout: Dict[str, list[str]] | None,
        start_quarter: str | None,
        display_start_quarter: str | None,
        filter_path: str | None = None,
    ) -> Dict[str, pd.DataFrame]:
        layout = layout or {}
        ids_cols = layout.get("Ids", self._IDS_COLUMNS)
        hist_cols = layout.get("Historico", self._HIST_COLUMNS)
        data_cols = layout.get("Data", self._DATA_COLUMNS)
        tip_cols = layout.get("Tipologias", self._TIPOLOGIAS_COLUMNS)

        filter_df = self._load_filter(filter_path)
        if filter_df is None or filter_df.empty:
            filter_df = self._default_filter(raw_clean)
        ids = self._build_ids(raw_clean, ids_cols, filter_df)
        historico = self._build_historico(raw_clean, hist_cols, start_quarter, display_start_quarter, filter_df)
        data = self._build_data(raw_clean, ids, data_cols, filter_df)
        tipologias_raw = self._load_tipologias(filter_path)
        tipologias = self._build_tipologias(raw_clean, ids, tipologias_raw, tip_cols, filter_df)

        return {
            "Ids": ids,
            "Historico": historico,
            "Data": data,
            "Tipologias": tipologias,
        }

    def _build_ids(self, raw: pd.DataFrame, columns: list[str], filter_df: pd.DataFrame | None) -> pd.DataFrame:
        base_cols = [c for c in ["Codigo COL", "Proyecto", "Desarrollador"] if c in raw.columns]
        df = raw[base_cols].dropna(subset=["Proyecto"]).drop_duplicates()
        if filter_df is not None:
            df = self._apply_filter(df, filter_df)
        df = df.reset_index(drop=True)
        df["ID"] = df["Proyecto"].map(short_id)
        return ensure_columns(df, columns)

    def _build_data(
        self, raw: pd.DataFrame, ids: pd.DataFrame, columns: list[str], filter_df: pd.DataFrame | None
    ) -> pd.DataFrame:
        df = raw.copy().dropna(subset=["Proyecto", "Último Trimestre"])
        df["_key"] = df["Proyecto"].map(normalize_key)
        df["_quarter_key"] = df["Último Trimestre"].map(quarter_key)
        df = df.sort_values(["_key", "_quarter_key"]).reset_index(drop=True)

        last_quarter = df["_quarter_key"].max()
        latest = df.groupby("_key", as_index=False).tail(1).copy()
        if pd.notna(last_quarter):
            latest = latest[latest["_quarter_key"] == last_quarter]
        ids = ids.copy()
        ids["_key"] = ids["Proyecto"].map(normalize_key)
        latest = latest.merge(ids[["_key", "ID"]], on="_key", how="inner")

        if filter_df is not None:
            latest = self._apply_filter(latest, filter_df, use_key=True)

        latest["Stock_Inicial"] = latest["Unidades Totales"]
        latest["Ventas"] = latest["Unidades Totales"] - latest["Unidades Inventario"]
        latest["Meses_Inventario"] = latest.get("Meses de Inventario")
        latest["Meses_Mercado"] = latest.get("Meses en el Mercado")
        latest["Inventario"] = latest.get("Unidades Inventario")
        latest["Ticket"] = latest.get("Precio Promedio Inv.")
        latest["$xm2"] = latest.get("$M2 Promedio Inv")
        latest["Superficie"] = latest.get("M2 Promedio Inv")
        latest["Segmento"] = latest.get("Segmento")
        latest["Fecha_Inicio"] = self._format_datetime(latest.get("Fecha Inicio Venta"))
        latest["Ultimo_Levantamiento"] = self._format_datetime(latest.get("Último Levantamiento"))
        for source_col, dest_col in self._AMENITY_MAP.items():
            if source_col in latest.columns:
                latest[dest_col] = latest.get(source_col)

        ventas_2025 = self._ventas_ultimo_ano(df)
        latest = latest.merge(ventas_2025, on="_key", how="left")
        latest["Meses_Ultimo_Ano"] = latest["Meses_Mercado"].apply(
            lambda value: min(value, 12) if pd.notna(value) and value > 0 else None
        )
        latest["Absorcion"] = latest.apply(
            lambda row: row["Ventas_Ultimo_Ano"] / row["Meses_Ultimo_Ano"]
            if pd.notna(row.get("Ventas_Ultimo_Ano")) and row.get("Meses_Ultimo_Ano") not in (0, None)
            else None,
            axis=1,
        )
        latest["Absorcion_H"] = latest.apply(
            lambda row: row["Ventas"] / row["Meses_Mercado"]
            if row.get("Meses_Mercado") not in (0, None) and pd.notna(row.get("Ventas"))
            else None,
            axis=1,
        )

        latest.loc[latest["Absorcion"] == 0, "Meses_Inventario"] = "N/A"

        output = pd.DataFrame()
        for col in columns:
            if col in latest.columns:
                output[col] = latest[col].values
            else:
                output[col] = None
        output = output.dropna(subset=["Proyecto"]).reset_index(drop=True)
        output = ensure_columns(output, columns)
        amenity_cols = [
            "Alberca",
            "Asadores",
            "Bar",
            "Canchas Deportivas",
            "Casa Club",
            "Fogatero",
            "Gimnasio",
            "Jacuzzi",
            "Ludoteca",
            "Pet Zone",
            "Pista de Jogging ",
            "Sala de Cine",
            "Salón de Usos Multiples",
            "Salón de Yoga",
            "Sauna",
            "Spa",
            "Terraza",
        ]
        for col in amenity_cols:
            if col in output.columns:
                output[col] = (
                    output[col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map({"si": 1, "sí": 1, "true": 1, "1": 1, "no": 0, "false": 0, "0": 0})
                    .fillna(0)
                    .astype(int)
                )
        output = self._apply_rounding_data(output)
        return output

    def _load_filter(self, filter_path: str | None) -> pd.DataFrame | None:
        if not filter_path:
            return None
        try:
            if "docs.google.com/spreadsheets" in filter_path:
                df = self._load_filter_from_google_sheet(filter_path)
            else:
                xl = pd.ExcelFile(filter_path)
                sheet = self._pick_filter_sheet(xl.sheet_names)
                if not sheet:
                    return None
                df = xl.parse(sheet, header=None)
                df = self._coerce_filter_df(df.values.tolist())
            if df is None or df.empty:
                return None
            if "Proyecto" not in df.columns:
                return None
            return df
        except Exception:
            return None

    def _load_tipologias(self, path: str | None) -> pd.DataFrame | None:
        if not path:
            return None
        try:
            if "docs.google.com/spreadsheets" in path:
                df = self._load_tipologias_from_google_sheet(path)
            else:
                xl = pd.ExcelFile(path)
                sheet = self._pick_tipologias_sheet(xl.sheet_names)
                if not sheet:
                    return None
                df = xl.parse(sheet, header=None)
                df = self._coerce_tipologias_df(df.values.tolist())
            if df is None or df.empty:
                return None
            return df
        except Exception:
            return None

    def _load_filter_from_google_sheet(self, url: str) -> pd.DataFrame | None:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            import os
            from pathlib import Path
        except Exception:
            return None
        try:
            key = url.split("/d/")[1].split("/")[0]
        except Exception:
            return None
        try:
            gid = None
            if "gid=" in url:
                gid_part = url.split("gid=")[1]
                gid = gid_part.split("&")[0].split("#")[0]
                gid = int(gid) if gid and gid.isdigit() else None
            cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "credentials.json"
            if not Path(cred_path).exists():
                return None
            creds = Credentials.from_service_account_file(
                cred_path,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                    "https://www.googleapis.com/auth/drive.readonly",
                ],
            )
            client = gspread.authorize(creds)
            sheet = client.open_by_key(key)
            ws = None
            if gid is not None:
                try:
                    ws = sheet.get_worksheet_by_id(gid)
                    values = ws.get_all_values()
                    header_len = self._filter_header_len(values)
                    if header_len is None or header_len > 6:
                        ws = None
                except Exception:
                    ws = None
            if ws is None:
                candidates = {self._normalize_title(n): n for n in self._filter_sheet_candidates()}
                for w in sheet.worksheets():
                    title_norm = self._normalize_title(w.title)
                    if title_norm in candidates:
                        values = w.get_all_values()
                        header_len = self._filter_header_len(values)
                        if header_len is not None and header_len <= 6:
                            ws = w
                            break
            if ws is None:
                best = None
                best_len = None
                for w in sheet.worksheets():
                    values = w.get_all_values()
                    header_len = self._filter_header_len(values)
                    if header_len is None:
                        continue
                    if header_len > 6:
                        continue
                    if best is None or header_len < best_len:
                        best = w
                        best_len = header_len
                ws = best
            if ws is None:
                return None
            values = ws.get_all_values()
            return self._coerce_filter_df(values)
        except Exception:
            return None

    def _load_tipologias_from_google_sheet(self, url: str) -> pd.DataFrame | None:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            import os
            from pathlib import Path
        except Exception:
            return None
        try:
            key = url.split("/d/")[1].split("/")[0]
        except Exception:
            return None
        try:
            gid = None
            if "gid=" in url:
                gid_part = url.split("gid=")[1]
                gid = gid_part.split("&")[0].split("#")[0]
                gid = int(gid) if gid and gid.isdigit() else None
            cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "credentials.json"
            if not Path(cred_path).exists():
                return None
            creds = Credentials.from_service_account_file(
                cred_path,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                    "https://www.googleapis.com/auth/drive.readonly",
                ],
            )
            client = gspread.authorize(creds)
            sheet = client.open_by_key(key)
            ws = None
            if gid is not None:
                try:
                    ws = sheet.get_worksheet_by_id(gid)
                except Exception:
                    ws = None
            for name in self._tipologias_sheet_candidates():
                try:
                    ws = sheet.worksheet(name)
                    break
                except Exception:
                    continue
            if ws is None:
                return None
            values = ws.get_all_values()
            return self._coerce_tipologias_df(values)
        except Exception:
            return None

    def _default_filter(self, raw: pd.DataFrame) -> pd.DataFrame:
        base = raw[["Proyecto"]].dropna(subset=["Proyecto"]).drop_duplicates()
        base = base.reset_index(drop=True)
        return base

    def _filter_sheet_candidates(self) -> list[str]:
        return ["Filtro_Proyectos", "Filtro proyecto", "Filtro proyectos", "Filtro Proyectos"]

    def _tipologias_sheet_candidates(self) -> list[str]:
        return ["Tipologias", "Tipologías", "Tipologia", "Tipología"]

    def _pick_filter_sheet(self, sheet_names: list[str]) -> str | None:
        for name in self._filter_sheet_candidates():
            if name in sheet_names:
                return name
        return None

    def _pick_tipologias_sheet(self, sheet_names: list[str]) -> str | None:
        for name in self._tipologias_sheet_candidates():
            if name in sheet_names:
                return name
        return None

    def _coerce_filter_df(self, values: list[list[str]]) -> pd.DataFrame | None:
        if not values:
            return None
        header_idx = None
        for idx, row in enumerate(values):
            if any(str(cell).strip().lower() == "proyecto" for cell in row):
                header_idx = idx
                break
        if header_idx is None:
            return None
        header = [str(cell).strip() for cell in values[header_idx]]
        data = values[header_idx + 1 :]
        df = pd.DataFrame(data, columns=header)
        if "Proyecto" not in df.columns:
            return None
        for col in ["Proyecto", "Codigo COL"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        df = df[df["Proyecto"] != ""]
        return df.reset_index(drop=True)

    def _filter_header_len(self, values: list[list[str]]) -> int | None:
        if not values:
            return None
        for row in values:
            if any(str(cell).strip().lower() == "proyecto" for cell in row):
                header = [str(cell).strip() for cell in row]
                if "Proyecto" not in header:
                    return None
                return sum(1 for cell in header if cell)
        return None

    def _apply_filter(
        self,
        df: pd.DataFrame,
        filter_df: pd.DataFrame,
        use_key: bool = False,
    ) -> pd.DataFrame:
        flt = filter_df.copy()
        if "Codigo COL" in flt.columns and "Codigo COL" in df.columns:
            flt["_code"] = flt["Codigo COL"].astype(str).str.strip().str.lower()
            df["_code"] = df["Codigo COL"].astype(str).str.strip().str.lower()
            if not set(df["_code"]).intersection(set(flt["_code"])):
                return df
            return df.merge(flt[["_code"]], on="_code", how="inner")
        if use_key:
            flt["_key"] = flt["Proyecto"].map(normalize_key)
            if "_key" in df.columns and not set(df["_key"]).intersection(set(flt["_key"])):
                return df
            return df.merge(flt[["_key"]], on="_key", how="inner")
        if "Proyecto" in df.columns and not set(df["Proyecto"]).intersection(set(flt["Proyecto"])):
            return df
        return df.merge(flt[["Proyecto"]], on="Proyecto", how="inner")

    def _normalize_title(self, title: str) -> str:
        return str(title).strip().lower().replace("_", "").replace(" ", "")

    def _build_tipologias(
        self,
        raw: pd.DataFrame,
        ids: pd.DataFrame,
        tipologias_raw: pd.DataFrame | None,
        columns: list[str],
        filter_df: pd.DataFrame | None,
    ) -> pd.DataFrame:
        if tipologias_raw is None or tipologias_raw.empty:
            return ensure_columns(pd.DataFrame(), columns)

        df = raw.copy().dropna(subset=["Proyecto", "Último Trimestre"])
        df["_key"] = df["Proyecto"].map(normalize_key)
        df["_quarter_key"] = df["Último Trimestre"].map(quarter_key)
        df = df.sort_values(["_key", "_quarter_key"]).reset_index(drop=True)

        last_quarter = df["_quarter_key"].max()
        latest = df.groupby("_key", as_index=False).tail(1).copy()
        if pd.notna(last_quarter):
            latest = latest[latest["_quarter_key"] == last_quarter]

        ids = ids.copy()
        ids["_key"] = ids["Proyecto"].map(normalize_key)
        latest = latest.merge(ids[["_key", "ID"]], on="_key", how="left")

        tip = tipologias_raw.copy()
        tip["_key"] = tip["Proyecto"].map(normalize_key)
        if filter_df is not None:
            tip = self._apply_filter(tip, filter_df, use_key=True)
        # Ensure only projects present in Ids (already filtered) are kept
        tip = tip[tip["_key"].isin(set(ids["_key"]))].copy()
        latest = latest.merge(tip, on="_key", how="inner", suffixes=("", "_tip"))

        latest["Codigo COL"] = latest.get("Codigo COL")
        latest["Tipo de Modelo"] = self._pick_col(latest, ["Tipo de Modelo_tip", "Tipo de Modelo", "Modelo_tip"])
        latest["Nombre Modelo"] = self._pick_col(latest, ["Nombre Modelo_tip", "Nombre Modelo"])
        latest["Dormitorios"] = self._normalize_dormitorios(
            self._pick_col(latest, ["Dormitorios_tip", "Dormitorios", "Dormitorios/Recámaras", "Recámaras"])
        )
        latest["Bathroom"] = self._pick_col(latest, ["Bathroom_tip", "Baños_tip", "Banos_tip", "Bathroom", "Baños", "Banos"])
        latest["Cajones"] = self._pick_col(
            latest,
            ["Cajones_tip", "Cajones", "Cajones Estacionamiento", "Estacionamientos", "Cajones Estacionamiento_tip"],
        )
        latest["Ticket"] = self._pick_col(latest, ["Precio Promedio Inv.", "Precio Promedio Inv._tip"])
        latest["$xm2"] = self._pick_col(latest, ["$M2 Promedio Inv", "$M2 Promedio Inv_tip", "M2 Promedio Inv_tip"])
        latest["Superficie"] = self._pick_col(latest, ["M2 Promedio Inv", "Metrajes (M2)_tip"])
        latest["Stock Inicial"] = pd.to_numeric(
            self._pick_col(latest, ["Unidades Totales_tip", "Unidades Totales"]),
            errors="coerce",
        )
        latest["Inventario"] = pd.to_numeric(
            self._pick_col(latest, ["Unidades Inventario_tip", "Unidades Inventario"]),
            errors="coerce",
        )
        latest["Meses en Mercado"] = pd.to_numeric(
            self._pick_col(latest, ["Meses en el Mercado_tip", "Meses en el Mercado"]),
            errors="coerce",
        )

        latest["Ventas"] = latest["Stock Inicial"] - latest["Inventario"]
        latest["Absorcion"] = latest.apply(
            lambda row: row["Ventas"] / row["Meses en Mercado"]
            if pd.notna(row.get("Ventas")) and row.get("Meses en Mercado") not in (0, None)
            else None,
            axis=1,
        )
        latest["Tipo de Modelo"] = latest.apply(
            lambda row: self._normalize_tipologia(row.get("Tipo de Modelo"), row.get("Dormitorios")),
            axis=1,
        )

        output = pd.DataFrame()
        for col in columns:
            if col in latest.columns:
                output[col] = latest[col].values
            else:
                output[col] = None
        output = output.dropna(subset=["Proyecto"]).reset_index(drop=True)
        output = ensure_columns(output, columns)
        if "Absorcion" in output.columns:
            output["Absorcion"] = pd.to_numeric(output["Absorcion"], errors="coerce").round(2)
        return output

    def _ventas_trimestre(self, hist: pd.DataFrame) -> pd.DataFrame:
        tmp = hist.copy()
        tmp["_key"] = tmp["Proyecto"].map(normalize_key)
        tmp["_quarter_key"] = tmp["Último Trimestre"].map(quarter_key)
        tmp = tmp.sort_values(["_key", "_quarter_key"])
        tmp["sold"] = tmp["Unidades Totales"] - tmp["Unidades Inventario"]
        diff = tmp.groupby("_key")["sold"].diff()
        tmp["ventas_trimestre"] = diff
        tmp.loc[diff.isna(), "ventas_trimestre"] = tmp.loc[diff.isna(), "sold"]
        latest = tmp.groupby("_key", as_index=False).tail(1)
        return latest[["_key", "ventas_trimestre"]].rename(columns={"ventas_trimestre": "Ventas"})

    def _build_tipologias_moi(
        self,
        raw: pd.DataFrame,
        tipologias_raw: pd.DataFrame | None,
    ) -> pd.DataFrame:
        if tipologias_raw is None or tipologias_raw.empty:
            return pd.DataFrame()

        df = raw.copy().dropna(subset=["Proyecto", "Último Trimestre"])
        df["_key"] = df["Proyecto"].map(normalize_key)
        df["_quarter_key"] = df["Último Trimestre"].map(quarter_key)
        df = df.sort_values(["_key", "_quarter_key"]).reset_index(drop=True)
        last_quarter = df["_quarter_key"].max()
        latest = df.groupby("_key", as_index=False).tail(1).copy()
        if pd.notna(last_quarter):
            latest = latest[latest["_quarter_key"] == last_quarter]

        tip = tipologias_raw.copy()
        tip["_key"] = tip["Proyecto"].map(normalize_key)
        latest = latest.merge(tip, on="_key", how="inner")

        latest["Stock Inicial"] = latest.get("Unidades Totales")
        latest["Inventario"] = latest.get("Unidades Inventario")
        latest["Ventas"] = latest["Stock Inicial"] - latest["Inventario"]
        latest["Meses en Mercado"] = latest.get("Meses en el Mercado")
        latest["Tipo de Modelo"] = latest.apply(
            lambda row: self._normalize_tipologia(row.get("Tipo de Modelo"), row.get("Dormitorios")),
            axis=1,
        )

        grouped = []
        for tipo, group in latest.groupby("Tipo de Modelo"):
            inventario = pd.to_numeric(group.get("Inventario"), errors="coerce").sum()
            stock = pd.to_numeric(group.get("Stock Inicial"), errors="coerce").sum()
            ventas = pd.to_numeric(group.get("Ventas"), errors="coerce").sum()
            ticket_m = weighted_avg(group, "Precio Promedio Inv.", "Unidades Inventario") / 1_000_000
            superficie = weighted_avg(group, "M2 Promedio Inv", "Unidades Inventario")
            xm2_k = (ticket_m / superficie) * 1000 if superficie else 0
            meses_mercado = pd.to_numeric(group.get("Meses en Mercado"), errors="coerce").mean()
            absorcion = ventas / meses_mercado if meses_mercado and pd.notna(ventas) else None
            moi = None
            if absorcion and absorcion != 0:
                moi = inventario / absorcion
            elif absorcion == 0:
                moi = "N/A"
            grouped.append(
                {
                    "Tipo": tipo,
                    "Stock Inicial": stock,
                    "Inventario": inventario,
                    "Ventas": ventas,
                    "Ticket (M)": ticket_m,
                    "$xm2 (k)": xm2_k,
                    "Superficie": superficie,
                    "Absorción": absorcion,
                    "Meses en Mercado": meses_mercado,
                    "Meses de Inv.": moi,
                }
            )

        if not grouped:
            return pd.DataFrame()
        wide_order = [
            "Stock Inicial",
            "Inventario",
            "Ventas",
            "Ticket (M)",
            "$xm2 (k)",
            "Superficie",
            "Absorción",
            "Meses en Mercado",
            "Meses de Inv.",
        ]
        typ_order = ["1R", "1.5R", "2R", "2.5R", "3R", "3.5R+", "4R", "5R"]
        df_g = pd.DataFrame(grouped)
        tipos = [t for t in typ_order if t in df_g["Tipo"].unique()]
        otros = [t for t in df_g["Tipo"].unique() if t not in tipos]
        tipos = tipos + sorted(otros)

        rows = []
        for metric in wide_order:
            row = {"Tipologia": metric}
            for t in tipos:
                value = df_g.loc[df_g["Tipo"] == t, metric]
                row[t] = value.iloc[0] if not value.empty else None
            rows.append(row)
        return pd.DataFrame(rows)

    def _normalize_tipologia(self, tipo: object, dormitorios: object) -> str | None:
        text = str(tipo).strip() if tipo is not None else ""
        if text:
            t = text.lower().replace("recamaras", "").replace("recámara", "").replace("recamara", "").strip()
            t = t.replace(" ", "")
            if "1+1" in t or "1+1e" in t:
                return "1.5R"
            if "1.5" in t:
                return "1.5R"
            if "2.5" in t:
                return "2.5R"
            if "3.5" in t or "3.5+" in t:
                return "3.5R+"
            if t.startswith("1"):
                return "1R"
            if t.startswith("2"):
                return "2R"
            if t.startswith("3"):
                return "3R"
            if t.startswith("4"):
                return "4R"
            if t.startswith("5"):
                return "5R"
        try:
            d = float(str(dormitorios).strip())
            if d == 1:
                return "1R"
            if d == 1.5:
                return "1.5R"
            if d == 2:
                return "2R"
            if d == 2.5:
                return "2.5R"
            if d == 3:
                return "3R"
            if d >= 3.5:
                return "3.5R+"
        except Exception:
            return text or None
        return text or None

    def _coerce_tipologias_df(self, values: list[list[str]]) -> pd.DataFrame | None:
        if not values:
            return None
        header_idx = None
        for idx, row in enumerate(values):
            if any(str(cell).strip().lower() == "proyecto" for cell in row):
                header_idx = idx
                break
        if header_idx is None:
            return None
        header = [str(cell).strip() for cell in values[header_idx]]
        data = values[header_idx + 1 :]
        df = pd.DataFrame(data, columns=header)
        for col in ["Proyecto", "Codigo COL", "Tipo de Modelo", "Nombre Modelo", "Dormitorios", "Bathroom", "Cajones"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        if "Proyecto" not in df.columns:
            return None
        df = df[df["Proyecto"] != ""]
        return df.reset_index(drop=True)

    def _build_historico(
        self,
        raw: pd.DataFrame,
        columns: list[str],
        start_quarter: str | None,
        display_start_quarter: str | None,
        filter_df: pd.DataFrame | None,
    ) -> pd.DataFrame:
        hist = raw.copy()
        required = [
            "Proyecto",
            "Último Trimestre",
            "Unidades Totales",
            "Unidades Inventario",
            "Precio Promedio Inv.",
            "M2 Promedio Inv",
        ]
        hist = hist[[c for c in required if c in hist.columns]].dropna(subset=["Proyecto", "Último Trimestre"])
        if filter_df is not None:
            hist["_key"] = hist["Proyecto"].map(normalize_key)
            hist = self._apply_filter(hist, filter_df, use_key=True)

        for col in ["Unidades Totales", "Unidades Inventario", "Precio Promedio Inv.", "M2 Promedio Inv"]:
            if col in hist.columns:
                hist[col] = pd.to_numeric(hist[col], errors="coerce")

        hist["_key"] = hist["Proyecto"].map(normalize_key)
        hist["_quarter_key"] = hist["Último Trimestre"].map(quarter_key)
        hist = hist.sort_values(["_key", "_quarter_key"])
        global_min_q = hist["_quarter_key"].min()
        hist["sold"] = hist["Unidades Totales"] - hist["Unidades Inventario"]
        diff = hist.groupby("_key")["sold"].diff()
        hist["ventas_trimestre"] = diff
        # If no previous quarter for a project, use sold for new projects, except on the first
        # quarter available in the dataset (avoid inflating the earliest quarter).
        mask_first = diff.isna() & (hist["_quarter_key"] == global_min_q)
        hist.loc[mask_first, "ventas_trimestre"] = None
        hist.loc[diff.isna() & ~mask_first, "ventas_trimestre"] = hist.loc[diff.isna() & ~mask_first, "sold"]

        first_q = hist.groupby("_key")["_quarter_key"].transform("min")
        hist["_is_new"] = hist["_quarter_key"] == first_q

        rows = []
        for quarter, group in hist.groupby("Último Trimestre"):
            proyectos_activos = group["_key"].nunique()
            proyectos_nuevos = group.loc[group["_is_new"], "_key"].nunique()
            stock_activos = group["Unidades Totales"].sum(skipna=True)
            stock_nuevos = group.loc[group["_is_new"], "Unidades Totales"].sum(skipna=True)
            inventario = group["Unidades Inventario"].sum(skipna=True)
            ticket = weighted_avg(group, "Precio Promedio Inv.", "Unidades Inventario") / 1_000_000
            superficie = weighted_avg(group, "M2 Promedio Inv", "Unidades Inventario")
            xm2 = (ticket / superficie) * 1000 if superficie else 0

            ventas_series = group["ventas_trimestre"].dropna()
            ventas = ventas_series.sum() if not ventas_series.empty else None
            absorcion = ventas / 3 if ventas is not None else None
            meses_inv = None
            if absorcion and absorcion != 0:
                meses_inv = inventario / absorcion
            elif absorcion == 0:
                meses_inv = "N/A"

            rows.append(
                {
                    "Trimestre": quarter,
                    "Proyectos_A": proyectos_activos,
                    "Proyectos_N": proyectos_nuevos,
                    "Stock_Inicial_A": stock_activos,
                    "Stock_Inicial_N": stock_nuevos,
                    "Inventario": inventario,
                    "Ticket": ticket,
                    "$xm2": xm2,
                    "Superficie": superficie,
                    "Ventas": ventas,
                    "Absorcion": absorcion,
                    "Meses_Inventario": meses_inv,
                }
            )

        summary = pd.DataFrame(rows)
        summary["_quarter_key"] = summary["Trimestre"].map(quarter_key)
        summary = summary.sort_values("_quarter_key")
        if start_quarter:
            summary = summary.loc[summary["_quarter_key"] >= quarter_key(start_quarter)]
        if display_start_quarter:
            summary = summary.loc[summary["_quarter_key"] >= quarter_key(display_start_quarter)]
        summary = summary.drop(columns=["_quarter_key"], errors="ignore").reset_index(drop=True)
        summary = ensure_columns(summary, columns)
        return self._apply_rounding_historico(summary)


    def _ventas_historicas(self, hist: pd.DataFrame) -> pd.DataFrame:
        tmp = hist.copy()
        tmp["_key"] = tmp["Proyecto"].map(normalize_key)
        tmp["_quarter_key"] = tmp["Último Trimestre"].map(quarter_key)
        tmp = tmp.sort_values(["_key", "_quarter_key"])
        global_min_q = tmp["_quarter_key"].min()
        tmp["sold"] = tmp["Unidades Totales"] - tmp["Unidades Inventario"]
        diff = tmp.groupby("_key")["sold"].diff()
        tmp["ventas_trimestre"] = diff
        mask_first = diff.isna() & (tmp["_quarter_key"] == global_min_q)
        tmp.loc[mask_first, "ventas_trimestre"] = None
        tmp.loc[diff.isna() & ~mask_first, "ventas_trimestre"] = tmp.loc[diff.isna() & ~mask_first, "sold"]
        ventas_hist = tmp.groupby("_key", as_index=False)["ventas_trimestre"].sum(min_count=1)
        return ventas_hist.rename(columns={"ventas_trimestre": "Ventas_H"})

    def _ventas_ultimo_ano(self, hist: pd.DataFrame) -> pd.DataFrame:
        tmp = hist.copy()
        tmp = tmp.dropna(subset=["Proyecto", "Último Trimestre"])
        tmp["_key"] = tmp["Proyecto"].map(normalize_key)
        tmp["_quarter_key"] = tmp["Último Trimestre"].map(quarter_key)
        tmp["Unidades Inventario"] = pd.to_numeric(tmp["Unidades Inventario"], errors="coerce")
        tmp = tmp.sort_values(["_key", "_quarter_key"])

        quarters = sorted(tmp["_quarter_key"].dropna().unique())
        if len(quarters) < 2:
            return pd.DataFrame(columns=["_key", "Ventas_Ultimo_Ano"])

        # Use last 5 quarters (4 trimestre sales) when possible.
        last_quarters = quarters[-5:] if len(quarters) >= 5 else quarters
        inv = (
            tmp[tmp["_quarter_key"].isin(last_quarters)]
            .groupby(["_key", "_quarter_key"], as_index=False)["Unidades Inventario"]
            .first()
        )
        pivot = inv.pivot(index="_key", columns="_quarter_key", values="Unidades Inventario")
        ordered = [q for q in last_quarters if q in pivot.columns]

        ventas = {}
        for key, row in pivot.iterrows():
            total = 0.0
            for idx in range(len(ordered) - 1):
                current = row.get(ordered[idx])
                nxt = row.get(ordered[idx + 1])
                if pd.notna(current) and pd.notna(nxt):
                    diff = current - nxt
                    if diff > 0:
                        total += diff
            ventas[key] = total

        return pd.DataFrame({"_key": list(ventas.keys()), "Ventas_Ultimo_Ano": list(ventas.values())})

    def _apply_rounding_historico(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in ["Proyectos_A", "Proyectos_N", "Stock_Inicial_A", "Stock_Inicial_N", "Inventario", "Ventas"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").round(0)
        for col in ["Ticket", "$xm2", "Superficie", "Absorcion", "Meses_Inventario"]:
            if col in df.columns:
                df[col] = df[col].apply(round_or_keep)
        return df

    def _format_datetime(self, series: pd.Series | None) -> pd.Series | None:
        if series is None:
            return None
        parsed = pd.to_datetime(series, errors="coerce")
        return parsed.dt.strftime("%Y-%m-%d 00:00:00")

    def _pick_col(self, df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
        for name in candidates:
            if name in df.columns:
                return df.get(name)
        return None

    def _normalize_dormitorios(self, series: pd.Series | None) -> pd.Series | None:
        if series is None:
            return None
        vals = series.astype(str).str.strip()
        nums = vals.str.extract(r"(\d+)")[0]
        return pd.to_numeric(nums, errors="coerce")

    def _apply_rounding_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in ["Stock_Inicial", "Ventas", "Inventario", "Meses_Mercado"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").round(0)
        for col in ["Absorcion", "Absorcion_H", "Meses_Inventario", "Ticket", "$xm2", "Superficie"]:
            if col in df.columns:
                df[col] = df[col].apply(round_or_keep)
        for col in ["Latitud", "Longitud"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").round(4)
        return df
