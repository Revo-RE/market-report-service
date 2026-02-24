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

        filter_df = self._load_filter(filter_path)
        if filter_df is None or filter_df.empty:
            filter_df = self._default_filter(raw_clean)
        ids = self._build_ids(raw_clean, ids_cols, filter_df)
        historico = self._build_historico(raw_clean, hist_cols, start_quarter, display_start_quarter)
        data = self._build_data(raw_clean, ids, data_cols, filter_df)

        filtro = self._build_filter_sheet(filter_df)
        return {"Ids": ids, "Historico": historico, "Data": data, "Filtro_Proyectos": filtro}

    def _build_ids(self, raw: pd.DataFrame, columns: list[str], filter_df: pd.DataFrame | None) -> pd.DataFrame:
        df = raw[["Proyecto", "Desarrollador"]].dropna(subset=["Proyecto"]).drop_duplicates()
        if filter_df is not None and "Proyecto" in filter_df.columns:
            df = df.merge(filter_df[["Proyecto"]], on="Proyecto", how="inner")
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
        latest = latest.merge(ids[["_key", "ID"]], on="_key", how="left")

        if filter_df is not None and "Proyecto" in filter_df.columns:
            filter_df = filter_df.copy()
            filter_df["_key"] = filter_df["Proyecto"].map(normalize_key)
            latest = latest.merge(filter_df[["_key"]], on="_key", how="inner")

        latest["Stock_Inicial"] = latest["Unidades Totales"]
        latest["Ventas"] = latest["Unidades Totales"] - latest["Unidades Inventario"]
        latest["Meses_Inventario"] = latest.get("Meses de Inventario")
        latest["Meses_Mercado"] = latest.get("Meses en el Mercado")
        latest["Inventario"] = latest.get("Unidades Inventario")
        latest["Ticket"] = latest.get("Precio Promedio Inv.")
        latest["$xm2"] = latest.get("$M2 Promedio Inv")
        latest["Superficie"] = latest.get("M2 Promedio Inv")
        latest["Fecha_Inicio"] = latest.get("Fecha Inicio Venta")
        latest["Ultimo_Levantamiento"] = latest.get("Último Levantamiento")
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
                if "Filtro_Proyectos" not in xl.sheet_names:
                    return None
                df = xl.parse("Filtro_Proyectos")
            if df is None or df.empty:
                return None
            if "Proyecto" not in df.columns:
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
            try:
                ws = sheet.worksheet("Filtro_Proyectos")
            except Exception:
                return None
            records = ws.get_all_records()
            return pd.DataFrame(records) if records else pd.DataFrame()
        except Exception:
            return None

    def _default_filter(self, raw: pd.DataFrame) -> pd.DataFrame:
        base = raw[["Proyecto"]].dropna(subset=["Proyecto"]).drop_duplicates()
        base = base.reset_index(drop=True)
        return base

    def _build_filter_sheet(self, filter_df: pd.DataFrame) -> pd.DataFrame:
        df = filter_df.copy()
        if "Proyecto" not in df.columns:
            df["Proyecto"] = None
        return df[["Proyecto"]]

    def _build_historico(
        self,
        raw: pd.DataFrame,
        columns: list[str],
        start_quarter: str | None,
        display_start_quarter: str | None,
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
