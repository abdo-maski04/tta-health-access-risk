"""Dashboards analytiques GeoVulnera TTA construits sur les données préparées."""

from __future__ import annotations

import html
import math
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.header import page_header
from components.kpi_card import kpi_row
from components.states import empty_state, unavailable_state
from config.settings import REGION_NAME
from config.theme import COLORS, THEME
from map_utils import (
    build_commune_layer,
    build_facility_layer,
    facility_icon_svg,
    get_initial_map,
    render_map,
)

FACILITY_LABELS = {
    "hospital": "Hôpitaux",
    "clinic": "Cliniques",
    "pharmacy": "Pharmacies",
    "doctors": "Médecins",
    "laboratory": "Laboratoires",
    "physiotherapist": "Kinésithérapeutes",
    "healthcare_unspecified": "Autres",
}
FACILITY_ORDER = list(FACILITY_LABELS)
RANKING_FACILITY_FILTERS = {
    "Tous": None,
    "Hôpitaux": ("hospital",),
    "Cliniques": ("clinic",),
    "Pharmacies": ("pharmacy",),
    "Médecins": ("doctors",),
    "Laboratoires": ("laboratory",),
    "Autres": ("healthcare_unspecified", "physiotherapist"),
}
RANKING_METRICS = {
    "Total établissements": "Total établissements",
    "Établissements / 10 000 hab.": "Établissements / 10 000",
    "Population": "Population",
    "Hôpitaux": "Hôpitaux",
    "Pharmacies": "Pharmacies",
}
RANKING_FILTER_DEFAULTS = {
    "ranking_filter_province": "Toutes les provinces",
    "ranking_filter_milieu": "Tous",
    "ranking_filter_search": "",
    "ranking_population_min": 0,
    "ranking_population_max": None,
    "ranking_population_year": None,
    "ranking_facility_type": "Tous",
    "ranking_facility_min": 0,
    "ranking_facility_max": None,
    "ranking_metric": "Total établissements",
}


def _fmt(value: Any, digits: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Données non disponibles"
    if digits:
        return f"{float(value):,.{digits}f}".replace(",", " ")
    return f"{int(value):,}".replace(",", " ")


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    try:
        if numerator is None or denominator is None or float(denominator) <= 0:
            return None
        return float(numerator) / float(denominator)
    except (TypeError, ValueError):
        return None


def _facility_counts(facilities: list[dict], code: str | None = None) -> dict[str, int]:
    counts = Counter(
        str(row.get("facility_type", "healthcare_unspecified"))
        for row in facilities
        if row.get("commune_code") is not None
        and (code is None or str(row.get("commune_code")) == str(code))
    )
    return {kind: counts.get(kind, 0) for kind in FACILITY_ORDER}


def _commune_rows(communes: list[dict], facilities: list[dict]) -> list[dict]:
    rows = []
    for commune in communes:
        counts = _facility_counts(facilities, commune["commune_code"])
        total = sum(counts.values())
        density = commune.get("densite_hab_km2")
        if density is None:
            density = _safe_ratio(commune.get("population_2024"), commune.get("area_km2"))
        rows.append(
            {
                "Code": str(commune["commune_code"]),
                "Commune": commune.get("name_fr", ""),
                "Province": commune.get("province", ""),
                "Milieu": commune.get("milieu", ""),
                "Population 2014": commune.get("population_2014"),
                "Population 2024": commune.get("population_2024"),
                "Superficie km²": commune.get("area_km2"),
                "Densité": density,
                "Total établissements": total,
                "Hôpitaux": counts["hospital"],
                "Cliniques": counts["clinic"],
                "Pharmacies": counts["pharmacy"],
                "Médecins": counts["doctors"],
                "Laboratoires": counts["laboratory"],
                "Autres": counts["healthcare_unspecified"] + counts["physiotherapist"],
                "Établissements / 10 000": _safe_ratio(
                    total * 10000, commune.get("population_2024")
                ),
                "_raw": commune,
            }
        )
    return rows


RANKING_ICON_CONTENT = {
    "trophy": "<path d='M8 21h8m-4-4v4M7 4h10v5a5 5 0 0 1-10 0V4Z'/><path d='M7 6H4v2a4 4 0 0 0 4 4m9-6h3v2a4 4 0 0 1-4 4'/>",
    "communes": "<path d='M3 21V8l5-3 5 3v13M13 21V4l4-2 4 2v17M6 11h.01M10 11h.01M6 15h.01M10 15h.01M16 8h.01M19 8h.01M16 12h.01M19 12h.01M16 16h.01M19 16h.01'/>",
    "facilities": "<path d='M3 21V7l9-4 9 4v14M8 21v-6h8v6M12 8v5m-2.5-2.5h5'/>",
    "province": "<path d='M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z'/><circle cx='12' cy='10' r='2.5'/>",
    "unassigned": "<circle cx='12' cy='12' r='9'/><path d='M12 8v4m0 4h.01'/>",
    "filter": "<path d='M4 5h16l-6.5 7.5V19l-3 1v-7.5L4 5Z'/>",
    "info": "<circle cx='12' cy='12' r='9'/><path d='M12 11v5m0-8h.01'/>",
    "population": "<path d='M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm6-7.8a4 4 0 0 1 0 7.6m2 4h1a4 4 0 0 1 3 2.8V21'/>",
    "chart": "<path d='M4 19V9m5 10V5m5 14v-7m5 7H2'/>",
}

RANKING_CSS = """
<style>
body:has(.tta-ranking) .tta-ranking-heading {
    display:flex; align-items:center; gap:.75rem; margin:.25rem 0 .125rem;
}
body:has(.tta-ranking) .tta-ranking-heading > svg {
    width:1.75rem; height:1.75rem; color:#0D5C75; flex:0 0 1.75rem;
}
body:has(.tta-ranking) .tta-ranking-heading h1 {
    margin:0; color:#0F172A; font-size:clamp(1.25rem, 2vw, 1.6rem);
    font-weight:750;
}
body:has(.tta-ranking) .tta-ranking-subtitle {
    margin:.125rem 0 .875rem; color:#64748B; font-size:.75rem;
}
body:has(.tta-ranking) .tta-ranking-section-title {
    display:flex; align-items:center; gap:.5rem;
    color:#0F172A; font-size:.95rem; font-weight:700; margin:.125rem 0 .625rem;
}
body:has(.tta-ranking) .tta-ranking-section-title svg {
    width:1.125rem; height:1.125rem; color:#0D5C75;
}
body:has(.tta-ranking) .tta-ranking-kpi {
    display:flex; align-items:center; gap:.75rem; min-height:92px; height:100%;
    padding:clamp(.65rem, 1vw, .85rem); background:#FFFFFF;
    border:1px solid #E2E8F0; border-radius:.625rem;
    box-shadow:0 .125rem .5rem rgba(15,23,42,.04);
}
body:has(.tta-ranking) .tta-ranking-kpi-icon {
    display:flex; align-items:center; justify-content:center;
    width:2.625rem; height:2.625rem; flex:0 0 2.625rem; border-radius:.5625rem;
    background:#E6F3F4; color:#0D5C75;
}
body:has(.tta-ranking) .tta-ranking-kpi-icon svg {
    width:1.45rem; height:1.45rem;
}
body:has(.tta-ranking) .tta-ranking-kpi-value {
    color:#0F172A; font-size:clamp(1.15rem, 1.6vw, 1.45rem);
    font-weight:750; line-height:1.05;
}
body:has(.tta-ranking) .tta-ranking-kpi-label {
    color:#334155; font-size:.7rem; font-weight:650; margin-top:.2rem;
}
body:has(.tta-ranking) .tta-ranking-kpi-description {
    color:#64748B; font-size:.62rem; line-height:1.25; margin-top:.125rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
body:has(.tta-ranking) .st-key-ranking-filters,
body:has(.tta-ranking) .st-key-ranking-table-panel,
body:has(.tta-ranking) .st-key-ranking-preview,
body:has(.tta-ranking) .st-key-ranking-chart-top,
body:has(.tta-ranking) .st-key-ranking-chart-bottom,
body:has(.tta-ranking) .st-key-ranking-chart-province {
    box-sizing:border-box; width:100%; min-width:0; height:auto;
    background:#FFFFFF; border:1px solid #E2E8F0; border-radius:.625rem;
    padding:clamp(.65rem, 1vw, .9rem);
    box-shadow:0 .125rem .5rem rgba(15,23,42,.04);
}
body:has(.tta-ranking) .tta-ranking-filter-heading {
    color:#334155; font-size:.7rem; font-weight:700;
    padding:.45rem 0 .3rem; border-bottom:1px solid #E2E8F0;
    margin-bottom:.5rem;
}
body:has(.tta-ranking) .tta-ranking-filter-heading svg {
    width:.95rem; height:.95rem; margin-right:.3rem; vertical-align:middle;
    color:#0D5C75;
}
body:has(.tta-ranking) .tta-ranking-preview-name {
    color:#0F172A; font-size:1.125rem; font-weight:750; margin:.3rem 0 .75rem;
}
body:has(.tta-ranking) .tta-ranking-preview-line {
    display:flex; align-items:center; gap:.45rem; color:#475569;
    font-size:.7rem; margin:.45rem 0;
}
body:has(.tta-ranking) .tta-ranking-preview-line svg {
    width:.95rem; height:.95rem; color:#0D5C75; flex:0 0 .95rem;
}
body:has(.tta-ranking) .tta-ranking-type {
    display:flex; align-items:center; gap:.45rem; padding:.25rem 0;
    color:#475569; font-size:.65rem;
}
body:has(.tta-ranking) .tta-ranking-type-badge {
    display:inline-flex; align-items:center; justify-content:center;
    width:1.25rem; height:1.25rem; border-radius:50%; color:#FFFFFF;
}
body:has(.tta-ranking) .tta-ranking-type-badge svg {
    width:.75rem; height:.75rem;
}
body:has(.tta-ranking) .tta-ranking-type-count {
    margin-left:auto; color:#0F172A; font-weight:700;
}
body:has(.tta-ranking) .tta-ranking-future {
    display:flex; gap:.5rem; align-items:center; margin-top:.875rem;
    padding:.65rem .75rem; color:#1E3A5F; font-size:.65rem;
    background:#EFF6FF; border:1px solid #BFDBFE; border-radius:.5rem;
}
body:has(.tta-ranking) .tta-ranking-future svg {
    width:1.05rem; height:1.05rem; flex:0 0 1.05rem;
}
body:has(.tta-ranking) .tta-ranking-table-wrap {
    width:100%; max-height:410px; overflow-y:auto;
    border:1px solid #E2E8F0; border-radius:.5rem; background:#FFFFFF;
}
body:has(.tta-ranking) .tta-ranking-table {
    width:100%; table-layout:fixed; border-collapse:separate;
    border-spacing:0; color:#1E293B; font-size:.68rem;
}
body:has(.tta-ranking) .tta-ranking-table thead th {
    position:sticky; top:0; z-index:2; padding:.6rem .45rem;
    background:#0A3642; color:#FFFFFF; font-weight:650;
    text-align:left; white-space:normal; overflow-wrap:anywhere; border:0;
}
body:has(.tta-ranking) .tta-ranking-table thead th:first-child {
    border-top-left-radius:.5rem;
}
body:has(.tta-ranking) .tta-ranking-table thead th:last-child {
    border-top-right-radius:.5rem;
}
body:has(.tta-ranking) .tta-ranking-table tbody td {
    padding:.5rem .45rem; color:#1E293B;
    white-space:normal; overflow-wrap:anywhere;
    border-bottom:1px solid #E2E8F0;
}
body:has(.tta-ranking) .tta-ranking-table tbody tr:nth-child(even) {
    background:#F8FAFC;
}
body:has(.tta-ranking) .tta-ranking-table tbody tr:hover {
    background:#EFF6F7;
}
body:has(.tta-ranking) .tta-ranking-table tbody tr.is-selected {
    background:#E6F4F1 !important;
}
body:has(.tta-ranking) .tta-ranking-table tbody tr.is-selected td:first-child {
    border-left:.2rem solid #0D5C75;
}
body:has(.tta-ranking) .tta-ranking-env-badge {
    display:inline-flex; align-items:center; padding:.15rem .6rem;
    border-radius:999px; color:#FFFFFF; font-size:.75rem;
    font-weight:600; line-height:1.35;
}
body:has(.tta-ranking) [data-testid="stBaseButton-primary"],
body:has(.tta-ranking) button[kind="primary"] {
    background:#0D5C75 !important; color:#FFFFFF !important;
    border:0 !important;
}
body:has(.tta-ranking) [data-testid="stBaseButton-primary"]:hover,
body:has(.tta-ranking) button[kind="primary"]:hover {
    background:#0A3642 !important; color:#FFFFFF !important;
}
body:has(.tta-ranking) .stForm button[kind="primary"],
body:has(.tta-ranking) .stFormSubmitButton {
    background:#0D5C75 !important; color:#FFFFFF !important;
    border:none !important;
}
body:has(.tta-ranking) .stForm button[kind="primary"]:hover,
body:has(.tta-ranking) .stFormSubmitButton:hover {
    background:#0A3642 !important; color:#FFFFFF !important;
    border:none !important;
}
body:has(.tta-ranking) [data-testid="stMainBlockContainer"] {
    width:100% !important; max-width:100% !important;
}
body:has(.tta-ranking) .st-key-ranking-table-layout
    [data-testid="stHorizontalBlock"]:has(.st-key-ranking-table-panel) {
    display:grid; grid-template-columns:minmax(0, 2.4fr) minmax(0, 1fr);
    align-items:stretch; gap:clamp(.75rem, 1.5vw, 1.5rem);
}
body:has(.tta-ranking) .st-key-ranking-table-layout
    [data-testid="stHorizontalBlock"]:has(.st-key-ranking-table-panel)
    > [data-testid="column"] {
    width:auto !important; min-width:0 !important; flex:none !important;
}
body:has(.tta-ranking) .st-key-ranking-table-layout
    [data-testid="column"] > [data-testid="stVerticalBlock"] {
    height:auto;
}
body:has(.tta-ranking) .st-key-ranking-table-panel {
    height:auto; min-height:0;
}
body:has(.tta-ranking) .st-key-ranking-preview {
    height:100%; min-height:0;
    display:flex; flex-direction:column; justify-content:space-between;
}
body:has(.tta-ranking) [data-testid="stHorizontalBlock"]:has(.st-key-ranking-chart-top) {
    display:grid; grid-template-columns:repeat(3, minmax(0, 1fr));
    gap:clamp(.75rem, 1.5vw, 1.5rem);
}
body:has(.tta-ranking) [data-testid="stHorizontalBlock"]:has(.st-key-ranking-chart-top)
    > [data-testid="column"] {
    width:auto !important; min-width:0 !important; flex:none !important;
}
body:has(.tta-ranking) .st-key-ranking-filters
    [data-testid="stHorizontalBlock"]:has(.tta-ranking-filter-heading) {
    display:grid; grid-template-columns:repeat(4, minmax(0, 1fr));
    gap:clamp(.5rem, 1vw, 1rem);
}
body:has(.tta-ranking) .st-key-ranking-filters
    [data-testid="stHorizontalBlock"]:has(.tta-ranking-filter-heading)
    > [data-testid="column"] {
    width:auto !important; min-width:0 !important; flex:none !important;
    display:flex; flex-direction:column; height:100%;
}
body:has(.tta-ranking) .st-key-ranking-filters
    [data-testid="stHorizontalBlock"]:has(.tta-ranking-filter-heading)
    > [data-testid="column"]:nth-child(4) {
    justify-content:flex-end;
}
body:has(.tta-ranking) .st-key-ranking-filters
    [data-testid="stHorizontalBlock"]:has(.tta-ranking-filter-heading)
    > [data-testid="column"]:nth-child(4) [data-testid="stVerticalBlock"] {
    height:auto; min-height:0;
}
@media (max-width: 68.75rem) {
    body:has(.tta-ranking) .st-key-ranking-table-layout
        [data-testid="stHorizontalBlock"]:has(.st-key-ranking-table-panel) {
        grid-template-columns:minmax(0, 1fr);
    }
    body:has(.tta-ranking) [data-testid="stHorizontalBlock"]:has(.st-key-ranking-chart-top) {
        grid-template-columns:repeat(2, minmax(0, 1fr));
    }
    body:has(.tta-ranking) .st-key-ranking-filters
        [data-testid="stHorizontalBlock"]:has(.tta-ranking-filter-heading) {
        grid-template-columns:repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 42rem) {
    body:has(.tta-ranking) [data-testid="stHorizontalBlock"]:has(.st-key-ranking-chart-top),
    body:has(.tta-ranking) .st-key-ranking-filters
        [data-testid="stHorizontalBlock"]:has(.tta-ranking-filter-heading) {
        grid-template-columns:minmax(0, 1fr);
    }
}
</style>
"""


def _ranking_icon(name: str, *, size: int = 18) -> str:
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
        "viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        "stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' "
        "aria-hidden='true'>"
        f"{RANKING_ICON_CONTENT[name]}</svg>"
    )


def _ranking_population_years(rows: list[dict]) -> list[int]:
    return [
        year
        for year in (2014, 2024)
        if any(row.get(f"Population {year}") is not None for row in rows)
    ]


def _ranking_facility_count(row: dict, facility_type: str) -> int:
    included_types = RANKING_FACILITY_FILTERS.get(facility_type)
    if included_types is None:
        return int(row["Total établissements"])
    if facility_type == "Autres":
        return int(row["Autres"])
    return sum(int(row.get(FACILITY_LABELS[kind], 0)) for kind in included_types)


def _normalize_ranking_text(value: Any) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", str(value or "").casefold())
        if not unicodedata.combining(char)
    )


def _filter_ranking_rows(
    rows: list[dict],
    *,
    province: str = "Toutes les provinces",
    milieu: str = "Tous",
    search: str = "",
    population_year: int = 2024,
    min_population: int | None = None,
    max_population: int | None = None,
    facility_type: str = "Tous",
    min_facilities: int | None = None,
    max_facilities: int | None = None,
) -> list[dict]:
    needle = _normalize_ranking_text(search.strip())
    result = []
    for row in rows:
        if province != "Toutes les provinces" and row["Province"] != province:
            continue
        if milieu != "Tous" and row["Milieu"] != milieu:
            continue
        if needle and needle not in _normalize_ranking_text(f"{row['Commune']} {row['Code']}"):
            continue
        population = row.get(f"Population {population_year}")
        if min_population is not None and (population is None or population < min_population):
            continue
        if max_population is not None and (population is None or population > max_population):
            continue
        facility_count = _ranking_facility_count(row, facility_type)
        if min_facilities is not None and facility_count < min_facilities:
            continue
        if max_facilities is not None and facility_count > max_facilities:
            continue
        result.append(row)
    return result


def _sort_ranking_rows(rows: list[dict], metric: str, year: int) -> list[dict]:
    sort_field = RANKING_METRICS[metric]
    if sort_field == "Population":
        sort_field = f"Population {year}"

    def sort_key(row: dict) -> tuple[bool, float, str]:
        if sort_field == "Établissements / 10 000":
            value = _safe_ratio(
                row["Total établissements"] * 10000,
                row.get(f"Population {year}"),
            )
        else:
            value = row.get(sort_field)
        numeric_value = float(value) if value is not None else 0.0
        if not math.isfinite(numeric_value):
            return True, 0.0, _normalize_ranking_text(row["Commune"])
        return value is None, -numeric_value, _normalize_ranking_text(row["Commune"])

    return sorted(rows, key=sort_key)


def _reset_ranking_filters(
    population_max: int,
    facility_max: int,
    population_year: int,
) -> None:
    defaults = {
        **RANKING_FILTER_DEFAULTS,
        "ranking_population_max": population_max,
        "ranking_population_year": population_year,
        "ranking_facility_max": facility_max,
    }
    st.session_state.update(defaults)


def _ranking_table_html(
    rows: list[dict],
    selected_code: str,
    population_year: int,
) -> str:
    headers = (
        "#",
        "Commune",
        "Province",
        "Environnement",
        f"Population {population_year}",
        "Total établissements",
        "Hôpitaux",
        "Cliniques",
        "Pharmacies",
        "Établissements / 10 000 hab.",
    )
    header_html = "".join(f"<th>{html.escape(label)}</th>" for label in headers)
    environment_colors = {
        "Urbain": "#0D5C75",
        "Mixte": "#16A34A",
        "Rural": "#D97706",
    }
    row_html = []
    for rank, row in enumerate(rows, start=1):
        population = row.get(f"Population {population_year}")
        ratio = _safe_ratio(row["Total établissements"] * 10000, population)
        selected = str(row["Code"]) == str(selected_code)
        row_html.append(
            f"<tr class='{'is-selected' if selected else ''}' "
            f"aria-selected='{str(selected).lower()}'>"
            f"<td>{rank}</td>"
            f"<td>{html.escape(str(row['Commune']))}</td>"
            f"<td>{html.escape(str(row['Province']))}</td>"
            "<td><span class='tta-ranking-env-badge' "
            f"style='background:{environment_colors.get(row['Milieu'], '#64748B')}'>"
            f"{html.escape(str(row['Milieu']))}</span></td>"
            f"<td>{_fmt(population) if population is not None else '—'}</td>"
            f"<td>{row['Total établissements']}</td>"
            f"<td>{row['Hôpitaux']}</td>"
            f"<td>{row['Cliniques']}</td>"
            f"<td>{row['Pharmacies']}</td>"
            f"<td>{_fmt(ratio, 1) if ratio is not None else '—'}</td>"
            "</tr>"
        )
    return (
        "<div class='tta-ranking-table-wrap'>"
        "<table class='tta-ranking-table'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table></div>"
    )


def _chart(fig: go.Figure, height: int = 300) -> None:
    fig.update_layout(
        height=height,
        margin={"l": 38, "r": 18, "t": 42, "b": 38},
        paper_bgcolor=THEME.surface,
        plot_bgcolor=THEME.surface,
        font={"family": "Inter, Segoe UI, sans-serif", "size": 11, "color": THEME.text},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    fig.update_xaxes(gridcolor=THEME.border, zeroline=False)
    fig.update_yaxes(gridcolor=THEME.border, zeroline=False)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def _unavailable(title: str, message: str) -> None:
    with st.container(border=True):
        unavailable_state(title, message)


def _title(title: str, description: str) -> None:
    page_header(title, description)
    st.caption(f"Dashboard / {title} · {REGION_NAME}")


def _filters(rows: list[dict], key_prefix: str) -> tuple[list[dict], str, str]:
    provinces = sorted({row["Province"] for row in rows})
    milieux = ["Urbain", "Mixte", "Rural"]
    with st.container(border=True):
        st.markdown("**Filtres d’analyse**")
        c1, c2, c3 = st.columns([1.2, 1, 1.5])
        with c1:
            province = st.selectbox(
                "Province", ["Toutes les provinces", *provinces], key=f"{key_prefix}_province"
            )
        with c2:
            milieu = st.selectbox(
                "Milieu territorial", ["Tous", *milieux], key=f"{key_prefix}_milieu"
            )
        with c3:
            search = st.text_input("Rechercher une commune ou un code", key=f"{key_prefix}_search")
    filtered = rows
    if province != "Toutes les provinces":
        filtered = [row for row in filtered if row["Province"] == province]
    if milieu != "Tous":
        filtered = [row for row in filtered if row["Milieu"] == milieu]
    if search.strip():
        needle = search.casefold().strip()
        filtered = [
            row for row in filtered if needle in f"{row['Commune']} {row['Code']}".casefold()
        ]
    return filtered, province, milieu


def render_commune_ranking(communes: list[dict], facilities: list[dict]) -> None:
    rows = _commune_rows(communes, facilities)
    population_years = _ranking_population_years(rows)
    if not population_years:
        empty_state(
            "Population non disponible",
            "Aucune année de population exploitable n’est présente dans les données communales.",
        )
        return
    default_year = 2024 if 2024 in population_years else population_years[-1]
    population_max = max(
        int(row[f"Population {year}"])
        for year in population_years
        for row in rows
        if row.get(f"Population {year}") is not None
    )
    facility_max = max((row["Total établissements"] for row in rows), default=0)
    defaults = {
        **RANKING_FILTER_DEFAULTS,
        "ranking_population_max": population_max,
        "ranking_population_year": default_year,
        "ranking_facility_max": facility_max,
    }
    for key, value in defaults.items():
        if key not in st.session_state or (
            key in {"ranking_population_max", "ranking_facility_max"}
            and st.session_state[key] is None
        ):
            st.session_state[key] = value
    if st.session_state["ranking_population_year"] not in population_years:
        st.session_state["ranking_population_year"] = default_year

    filter_values = {
        "province": st.session_state["ranking_filter_province"],
        "milieu": st.session_state["ranking_filter_milieu"],
        "search": st.session_state["ranking_filter_search"],
        "population_year": st.session_state["ranking_population_year"],
        "min_population": st.session_state["ranking_population_min"],
        "max_population": st.session_state["ranking_population_max"],
        "facility_type": st.session_state["ranking_facility_type"],
        "min_facilities": st.session_state["ranking_facility_min"],
        "max_facilities": st.session_state["ranking_facility_max"],
    }
    filtered = _filter_ranking_rows(rows, **filter_values)
    metric = st.session_state["ranking_metric"]
    ranked = _sort_ranking_rows(filtered, metric, filter_values["population_year"])

    st.markdown(RANKING_CSS, unsafe_allow_html=True)
    page_header(
        "Commune Ranking",
        "Comparer les infrastructures de santé et les indicateurs démographiques des communes de la région.",
        compact=True,
    )
    st.markdown("<div class='tta-ranking'></div>", unsafe_allow_html=True)
    st.caption("Accueil / Classement Communes")

    title_col, refresh_col, export_col, info_col = st.columns(
        [3.4, 1, 1.65, 0.35],
        vertical_alignment="center",
    )
    with title_col:
        st.markdown(
            "<div class='tta-ranking-heading'>"
            f"{_ranking_icon('trophy', size=28)}"
            "<h1>Classement Communes</h1></div>"
            "<div class='tta-ranking-subtitle'>"
            "Comparer les infrastructures de santé et les indicateurs "
            f"démographiques des {len(rows)} communes de la région "
            f"{html.escape(REGION_NAME)}.</div>",
            unsafe_allow_html=True,
        )
    if refresh_col.button("Actualiser", key="ranking_refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    export_rows = []
    for index, row in enumerate(ranked, start=1):
        population = row.get(f"Population {filter_values['population_year']}")
        export_rows.append(
            {
                "Rang": index,
                "Commune": row["Commune"],
                "Code": row["Code"],
                "Province": row["Province"],
                "Environnement": row["Milieu"],
                f"Population {filter_values['population_year']}": population,
                "Total établissements": row["Total établissements"],
                "Hôpitaux": row["Hôpitaux"],
                "Cliniques": row["Cliniques"],
                "Pharmacies": row["Pharmacies"],
                "Médecins": row["Médecins"],
                "Laboratoires": row["Laboratoires"],
                "Autres": row["Autres"],
                "Établissements / 10 000 hab.": _safe_ratio(
                    row["Total établissements"] * 10000,
                    population,
                ),
            }
        )
    export_columns = [
        "Rang",
        "Commune",
        "Code",
        "Province",
        "Environnement",
        f"Population {filter_values['population_year']}",
        "Total établissements",
        "Hôpitaux",
        "Cliniques",
        "Pharmacies",
        "Médecins",
        "Laboratoires",
        "Autres",
        "Établissements / 10 000 hab.",
    ]
    export_csv = (
        pd.DataFrame(export_rows, columns=export_columns).to_csv(index=False).encode("utf-8-sig")
    )
    export_col.download_button(
        "Exporter le classement",
        data=export_csv,
        file_name="classement_communes_tta.csv",
        mime="text/csv",
        key="ranking_export",
        width="stretch",
    )
    with info_col:
        with st.popover("ⓘ"):
            st.write(
                "Les classements sont descriptifs et reposent sur les données "
                "communales et les établissements OSM associés."
            )

    kpi_items = [
        (
            "Total Communes",
            len(rows),
            "Communes incluses dans l’analyse régionale.",
            "communes",
            "#E6F3F4",
        ),
        (
            "Établissements Associés",
            sum(row["Total établissements"] for row in rows),
            "Établissements rattachés à une commune.",
            "facilities",
            "#EAF2FF",
        ),
        (
            "Provinces",
            len({row["Province"] for row in rows}),
            "Provinces et préfectures représentées.",
            "province",
            "#E6F3F4",
        ),
        (
            "Établissements Non Associés",
            sum(facility.get("commune_code") is None for facility in facilities),
            "Hors des polygones communaux.",
            "unassigned",
            "#F1F5F9",
        ),
    ]
    kpi_columns = st.columns(4)
    for column, (label, value, description, icon, _background) in zip(
        kpi_columns,
        kpi_items,
        strict=False,
    ):
        with column:
            st.markdown(
                "<div class='tta-ranking-kpi'>"
                f"<span class='tta-ranking-kpi-icon' style='background:{_background}'>"
                f"{_ranking_icon(icon, size=23)}</span>"
                "<div>"
                f"<div class='tta-ranking-kpi-value'>{_fmt(value)}</div>"
                f"<div class='tta-ranking-kpi-label'>{html.escape(label)}</div>"
                f"<div class='tta-ranking-kpi-description'>{html.escape(description)}</div>"
                "</div></div>",
                unsafe_allow_html=True,
            )

    with st.container(key="ranking-filters"):
        st.markdown(
            "<div class='tta-ranking-section-title'>"
            f"{_ranking_icon('filter')}Filtres de classement</div>",
            unsafe_allow_html=True,
        )
        with st.form("ranking_filters_form"):
            filter_columns = st.columns(4, gap="medium")
            with filter_columns[0]:
                st.markdown(
                    "<div class='tta-ranking-filter-heading'>Filtres géographiques</div>",
                    unsafe_allow_html=True,
                )
                st.selectbox(
                    "Province",
                    ["Toutes les provinces", *sorted({row["Province"] for row in rows})],
                    key="ranking_filter_province",
                )
                st.selectbox(
                    "Milieu territorial",
                    ["Tous", "Urbain", "Mixte", "Rural"],
                    key="ranking_filter_milieu",
                )
                st.text_input(
                    "Commune",
                    placeholder="Rechercher par nom ou code",
                    key="ranking_filter_search",
                )
            with filter_columns[1]:
                st.markdown(
                    "<div class='tta-ranking-filter-heading'>Filtres démographiques</div>",
                    unsafe_allow_html=True,
                )
                population_min_col, population_max_col = st.columns(2, gap="small")
                population_min_col.number_input(
                    "Population min",
                    min_value=0,
                    max_value=population_max,
                    key="ranking_population_min",
                )
                population_max_col.number_input(
                    "Population max",
                    min_value=0,
                    max_value=population_max,
                    key="ranking_population_max",
                )
                st.selectbox(
                    "Année de référence",
                    population_years,
                    key="ranking_population_year",
                )
            with filter_columns[2]:
                st.markdown(
                    "<div class='tta-ranking-filter-heading'>Filtres infrastructures</div>",
                    unsafe_allow_html=True,
                )
                st.selectbox(
                    "Type d’établissement",
                    list(RANKING_FACILITY_FILTERS),
                    key="ranking_facility_type",
                )
                facility_min_col, facility_max_col = st.columns(2, gap="small")
                facility_min_col.number_input(
                    "Établissements min",
                    min_value=0,
                    max_value=facility_max,
                    key="ranking_facility_min",
                )
                facility_max_col.number_input(
                    "Établissements max",
                    min_value=0,
                    max_value=facility_max,
                    key="ranking_facility_max",
                )
            with filter_columns[3]:
                st.markdown(
                    "<div class='tta-ranking-filter-heading'>Critère de classement</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height: 4.6rem;'></div>", unsafe_allow_html=True)
                st.selectbox(
                    "Classer les communes par",
                    list(RANKING_METRICS),
                    key="ranking_metric",
                )
                apply_col, reset_col = st.columns(2, gap="small")
                apply_col.form_submit_button(
                    "Appliquer",
                    type="primary",
                    width="stretch",
                )
                reset_col.form_submit_button(
                    "Réinitialiser",
                    on_click=_reset_ranking_filters,
                    args=(population_max, facility_max, default_year),
                    width="stretch",
                )

    selected_row: dict | None = None
    with st.container(key="ranking-table-layout"):
        table_col, preview_col = st.columns([2.4, 1], gap="medium")
        with table_col:
            with st.container(key="ranking-table-panel"):
                st.markdown(
                    "<div class='tta-ranking-section-title'>"
                    f"{_ranking_icon('chart')}Tableau de classement</div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"{len(ranked)} commune(s) après application des filtres.")
                if not ranked:
                    empty_state(
                        "Aucune commune trouvée",
                        "Ajustez les filtres pour afficher des résultats.",
                    )
                else:
                    labels = [f"{row['Commune']} · {row['Code']}" for row in ranked]
                    previous_code = st.session_state.get("ranking_selected_commune_code")
                    default_label = next(
                        (
                            label
                            for label, row in zip(labels, ranked, strict=True)
                            if row["Code"] == previous_code
                        ),
                        labels[0],
                    )
                    if st.session_state.get("ranking_selected_commune_label") not in labels:
                        st.session_state["ranking_selected_commune_label"] = default_label
                    selected_label = st.selectbox(
                        "Commune sélectionnée pour l’aperçu",
                        labels,
                        key="ranking_selected_commune_label",
                    )
                    selected_row = next(
                        row
                        for row in ranked
                        if f"{row['Commune']} · {row['Code']}" == selected_label
                    )
                    st.session_state["ranking_selected_commune_code"] = selected_row["Code"]
                    st.markdown(
                        _ranking_table_html(
                            ranked,
                            selected_row["Code"],
                            filter_values["population_year"],
                        ),
                        unsafe_allow_html=True,
                    )
        with preview_col:
            with st.container(key="ranking-preview"):
                st.markdown(
                    "<div class='tta-ranking-section-title'>"
                    f"{_ranking_icon('info')}Aperçu Commune Sélectionnée</div>",
                    unsafe_allow_html=True,
                )
                if selected_row is None:
                    empty_state(
                        "Aucune commune",
                        "Aucune commune ne correspond aux filtres actifs.",
                    )
                else:
                    selected_population = selected_row.get(
                        f"Population {filter_values['population_year']}"
                    )
                    st.markdown(
                        f"<div class='tta-ranking-preview-name'>"
                        f"{html.escape(selected_row['Commune'])}</div>"
                        "<div class='tta-ranking-preview-line'>"
                        f"{_ranking_icon('province', size=15)}Province : "
                        f"{html.escape(selected_row['Province'])}</div>"
                        "<div class='tta-ranking-preview-line'>"
                        f"{_ranking_icon('population', size=15)}Population "
                        f"({filter_values['population_year']}) : "
                        f"{_fmt(selected_population)}</div>"
                        "<div class='tta-ranking-preview-line'>"
                        f"{_ranking_icon('facilities', size=15)}Total établissements : "
                        f"{_fmt(selected_row['Total établissements'])}</div>"
                        "<div class='tta-ranking-filter-heading'>Par type</div>",
                        unsafe_allow_html=True,
                    )
                    preview_types = (
                        ("hospital", "Hôpitaux", selected_row["Hôpitaux"]),
                        ("clinic", "Cliniques", selected_row["Cliniques"]),
                        ("pharmacy", "Pharmacies", selected_row["Pharmacies"]),
                        ("doctors", "Médecins", selected_row["Médecins"]),
                        ("laboratory", "Laboratoires", selected_row["Laboratoires"]),
                        ("other", "Autres", selected_row["Autres"]),
                    )
                    for kind, label, count in preview_types:
                        st.markdown(
                            "<div class='tta-ranking-type'>"
                            f"<span class='tta-ranking-type-badge' "
                            f"style='background:{COLORS['risk_facility'][kind]}'>"
                            f"{facility_icon_svg(kind, size=12)}</span>"
                            f"{html.escape(label)}"
                            f"<span class='tta-ranking-type-count'>{count}</span>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                    detail_label = (
                        f"{selected_row['Commune']} · {selected_row['Province']} · "
                        f"{selected_row['Code']}"
                    )
                    st.button(
                        "Voir les détails →",
                        key="ranking_view_details",
                        type="primary",
                        width="stretch",
                        on_click=_open_ranking_commune_details,
                        args=(detail_label,),
                    )

    top10 = sorted(
        ranked,
        key=lambda row: (-row["Total établissements"], row["Commune"].casefold()),
    )[:10]
    bottom10 = sorted(
        ranked,
        key=lambda row: (row["Total établissements"], row["Commune"].casefold()),
    )[:10]
    chart_columns = st.columns(3, gap="medium")
    with chart_columns[0]:
        with st.container(key="ranking-chart-top"):
            st.markdown(
                "<div class='tta-ranking-section-title'>"
                f"{_ranking_icon('chart')}Top 10 — Plus grand nombre d’établissements</div>",
                unsafe_allow_html=True,
            )
            if top10:
                colors = [
                    f"rgba(13, 92, 117, {0.72 + 0.28 * index / max(1, len(top10) - 1):.2f})"
                    for index in range(len(top10))
                ]
                figure = go.Figure(
                    go.Bar(
                        x=[row["Total établissements"] for row in top10],
                        y=[row["Commune"] for row in top10],
                        orientation="h",
                        marker_color=colors,
                        text=[row["Total établissements"] for row in top10],
                        textposition="outside",
                        cliponaxis=False,
                    )
                )
                figure.update_yaxes(autorange="reversed")
                _ranking_chart(figure)
            else:
                empty_state("Aucune donnée", "Aucun résultat disponible.")
    with chart_columns[1]:
        with st.container(key="ranking-chart-bottom"):
            st.markdown(
                "<div class='tta-ranking-section-title'>"
                f"{_ranking_icon('chart')}Bottom 10 — Plus faible nombre d’établissements</div>",
                unsafe_allow_html=True,
            )
            if bottom10:
                figure = go.Figure(
                    go.Bar(
                        x=[row["Total établissements"] for row in bottom10],
                        y=[row["Commune"] for row in bottom10],
                        orientation="h",
                        marker_color=[
                            f"rgba(217, 119, 6, {0.72 + 0.28 * index / max(1, len(bottom10) - 1):.2f})"
                            for index in range(len(bottom10))
                        ],
                        text=[row["Total établissements"] for row in bottom10],
                        textposition="outside",
                        cliponaxis=False,
                    )
                )
                figure.update_yaxes(autorange="reversed")
                max_val = max(
                    (row["Total établissements"] for row in bottom10),
                    default=0,
                )
                figure.update_xaxes(
                    range=[0, max(1, max_val * 1.15)],
                    rangemode="tozero",
                )
                _ranking_chart(figure)
            else:
                empty_state("Aucune donnée", "Aucun résultat disponible.")
    with chart_columns[2]:
        with st.container(key="ranking-chart-province"):
            st.markdown(
                "<div class='tta-ranking-section-title'>"
                f"{_ranking_icon('province')}Comparaison provinciale</div>",
                unsafe_allow_html=True,
            )
            provincial: dict[str, dict[str, int]] = defaultdict(
                lambda: {"facilities": 0, "hospitals": 0}
            )
            for row in filtered:
                provincial[row["Province"]]["facilities"] += row["Total établissements"]
                provincial[row["Province"]]["hospitals"] += row["Hôpitaux"]
            provinces = sorted(
                provincial,
                key=lambda name: (-provincial[name]["facilities"], name.casefold()),
            )
            if provinces:
                figure = go.Figure()
                figure.add_bar(
                    x=provinces,
                    y=[provincial[name]["facilities"] for name in provinces],
                    name="Total établissements",
                    marker_color="#178582",
                    text=[provincial[name]["facilities"] for name in provinces],
                    textposition="outside",
                )
                figure.add_bar(
                    x=provinces,
                    y=[provincial[name]["hospitals"] for name in provinces],
                    name="Hôpitaux",
                    marker_color="#0A3642",
                    text=[provincial[name]["hospitals"] for name in provinces],
                    textposition="outside",
                )
                figure.update_layout(barmode="group")
                _ranking_chart(figure, height=300)
            else:
                empty_state("Aucune province", "Aucun résultat disponible.")

    st.markdown(
        "<div class='tta-ranking-future'>"
        f"{_ranking_icon('info', size=17)}"
        "<span><strong>Future Risk &amp; Accessibility Indicators</strong> — "
        "Validated risk scores and healthcare accessibility indicators are not "
        "yet available. This dashboard focuses on descriptive demographic and "
        "healthcare infrastructure data.</span></div>",
        unsafe_allow_html=True,
    )


def _ranking_chart(fig: go.Figure, height: int = 290) -> None:
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 20, "t": 30, "b": 20},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Inter, Segoe UI, sans-serif", "size": 9, "color": "#334155"},
        autosize=True,
        showlegend=(len(fig.data) > 1),
        legend={"orientation": "h", "y": 1.04, "x": 0},
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "displaylogo": False, "responsive": True},
    )


def _open_ranking_commune_details(label: str) -> None:
    st.session_state["details_commune"] = label
    st.session_state["pending_navigation_page"] = "Commune Details"


def _commune_picker(communes: list[dict], key: str) -> dict | None:
    options = {
        f"{row['name_fr']} · {row['province']} · {row['commune_code']}": row for row in communes
    }
    choice = st.selectbox("Sélectionner une commune", list(options), key=key)
    return options.get(choice)


def render_commune_details(
    communes: list[dict], commune_geojson: dict, facilities: list[dict]
) -> None:
    """Dashboard 4: Détails Commune - profil démographique, territorial et infrastructures de santé."""

    def _commune_label(row: dict) -> str:
        return (
            f"{row.get('name_fr', '')} · {row.get('province', '')} · {row.get('commune_code', '')}"
        )

    sorted_communes = sorted(communes, key=lambda r: str(r.get("name_fr", "")).casefold())
    labels = [_commune_label(r) for r in sorted_communes]
    label_to_row = {label: row for label, row in zip(labels, sorted_communes, strict=True)}

    stored = st.session_state.get("details_commune")
    if stored and stored in label_to_row:
        selected_row = label_to_row[stored]
        selected_index = labels.index(stored)
    else:
        selected_row = sorted_communes[0]
        selected_index = 0
        st.session_state["details_commune"] = _commune_label(selected_row)

    code = str(selected_row["commune_code"])
    name_fr = selected_row.get("name_fr", "Commune")
    province = selected_row.get("province", "")
    milieu = selected_row.get("milieu", "")
    population_2014 = selected_row.get("population_2014")
    population_2024 = selected_row.get("population_2024")
    area_km2 = selected_row.get("area_km2")
    density = selected_row.get("densite_hab_km2")
    if density is None and population_2024 and area_km2:
        density = population_2024 / area_km2

    commune_facilities = [f for f in facilities if str(f.get("commune_code")) == code]
    total_facilities = len(commune_facilities)
    facility_counts = Counter(
        str(row.get("facility_type", "healthcare_unspecified")) for row in commune_facilities
    )

    province_communes = [r for r in communes if r.get("province") == province]
    province_pop_2024 = [
        r.get("population_2024") for r in province_communes if r.get("population_2024")
    ]
    province_areas = [r.get("area_km2") for r in province_communes if r.get("area_km2")]
    province_total_pop = sum(v for v in province_pop_2024 if isinstance(v, (int, float)))
    province_total_area = sum(v for v in province_areas if isinstance(v, (int, float)))
    province_avg_density = (
        (province_total_pop / province_total_area) if province_total_area else None
    )

    province_facilities = [
        f
        for f in facilities
        if str(f.get("commune_code")) in {str(r["commune_code"]) for r in province_communes}
    ]
    province_total_facilities = len(province_facilities)
    province_avg_facilities = (
        province_total_facilities / len(province_communes) if province_communes else 0
    )

    region_total_pop = sum(
        r.get("population_2024") or 0
        for r in communes
        if isinstance(r.get("population_2024"), (int, float))
    )
    region_total_area = sum(
        r.get("area_km2") or 0 for r in communes if isinstance(r.get("area_km2"), (int, float))
    )
    region_avg_density = region_total_pop / region_total_area if region_total_area else None
    region_total_facilities = len(facilities)
    region_avg_facilities = region_total_facilities / len(communes) if communes else 0

    def _safe_ratio(numerator, denominator):
        try:
            if numerator is None or denominator is None or float(denominator) <= 0:
                return None
            return float(numerator) / float(denominator)
        except (TypeError, ValueError):
            return None

    def _fmt_int(value):
        if value is None:
            return "Non disponible"
        return f"{int(value):,}".replace(",", " ")

    def _fmt_float(value, digits=1):
        if value is None:
            return "Non disponible"
        return f"{float(value):,.{digits}f}".replace(",", " ")

    ratio_commune = _safe_ratio(total_facilities * 10000, population_2024)
    province_pop_for_ratio = sum(r.get("population_2024") or 0 for r in province_communes)
    ratio_province = _safe_ratio(province_total_facilities * 10000, province_pop_for_ratio)
    region_pop_for_ratio = region_total_pop
    ratio_region = _safe_ratio(region_total_facilities * 10000, region_pop_for_ratio)
    DETAILS_CSS = """
    <style>
    body:has(.tta-details) .tta-details-breadcrumb {
        display:flex; align-items:center; gap:.5rem; color:#64748B; font-size:.75rem;
        margin:.25rem 0 .5rem;
    }
    body:has(.tta-details) .tta-details-breadcrumb svg { width:1rem; height:1rem; color:#0D5C75; }
    body:has(.tta-details) .tta-details-breadcrumb span.tta-details-current { color:#0F172A; font-weight:700; }
    body:has(.tta-details) .tta-details-title-group { display:flex; align-items:center; gap:.75rem; }
    body:has(.tta-details) .tta-details-title-group svg { width:1.5rem; height:1.5rem; color:#0D5C75; }
    body:has(.tta-details) .tta-details-title-group h1 {
        margin:0; color:#0F172A; font-size:1.5rem; font-weight:750; line-height:1.2;
    }
    body:has(.tta-details) .tta-details-title-group p {
        margin:0; color:#64748B; font-size:.8rem; line-height:1.4;
    }
    body:has(.tta-details) .tta-details-hero {
        display:flex; gap:1.5rem; align-items:flex-start;
        background: linear-gradient(135deg, #F0FDFA 0%, #E6F4F1 100%);
        border:1px solid #CCFBF1; border-radius:12px; padding:1.25rem 1.5rem;
        margin:0 0 1.25rem; box-sizing:border-box; width:100%;
    }
    body:has(.tta-details) .tta-details-hero-thumb {
        flex:0 0 140px; width:140px; height:110px; border-radius:10px;
        background:#FFFFFF; border:1px solid #E2E8F0; display:flex;
        align-items:center; justify-content:center; overflow:hidden;
    }
    body:has(.tta-details) .tta-details-hero-thumb svg { width:48px; height:48px; color:#0D5C75; }
    body:has(.tta-details) .tta-details-hero-center { flex:1; min-width:0; }
    body:has(.tta-details) .tta-details-hero-name {
        color:#0F172A; font-size:1.75rem; font-weight:800; line-height:1.2; margin:0 0 .25rem;
    }
    body:has(.tta-details) .tta-details-hero-meta {
        color:#475569; font-size:.85rem; display:flex; gap:1rem; flex-wrap:wrap; margin:0 0 .625rem;
    }
    body:has(.tta-details) .tta-details-hero-meta span { white-space:nowrap; }
    body:has(.tta-details) .tta-details-hero-pill {
        display:inline-flex; align-items:center; gap:.35rem;
        padding:.2rem .7rem; border-radius:999px; font-size:.75rem; font-weight:700; color:#FFFFFF;
    }
    body:has(.tta-details) .tta-details-hero-note {
        color:#64748B; font-size:.8rem; margin:.35rem 0 0;
    }
    body:has(.tta-details) .tta-details-kpi {
        background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px;
        padding:.85rem 1rem; height:100%; min-height:92px; box-sizing:border-box;
        box-shadow:0 1px 3px rgba(15,23,42,.04);
    }
    body:has(.tta-details) .tta-details-kpi-icon {
        display:flex; align-items:center; justify-content:center;
        width:2.25rem; height:2.25rem; border-radius:.5625rem; background:#E6F3F4; color:#0D5C75;
    }
    body:has(.tta-details) .tta-details-kpi-icon svg { width:1.25rem; height:1.25rem; }
    body:has(.tta-details) .tta-details-kpi-value {
        color:#0F172A; font-size:1.5rem; font-weight:800; line-height:1.15; margin:.25rem 0 .125rem;
    }
    body:has(.tta-details) .tta-details-kpi-label {
        color:#475569; font-size:.7rem; font-weight:700; line-height:1.3; margin:0;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    body:has(.tta-details) .tta-details-kpi-sub {
        color:#94A3B8; font-size:.62rem; line-height:1.3; margin:.125rem 0 0;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    body:has(.tta-details) .tta-details-card {
        background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px;
        padding:1rem; height:100%; min-height:0; box-sizing:border-box;
        box-shadow:0 1px 3px rgba(15,23,42,.04);
    }
    body:has(.tta-details) .tta-details-card-title {
        display:flex; align-items:center; gap:.5rem; color:#0F172A;
        font-size:.95rem; font-weight:750; margin:0 0 .75rem;
    }
    body:has(.tta-details) .tta-details-card-title svg { width:1.125rem; height:1.125rem; color:#0D5C75; }
    body:has(.tta-details) .tta-details-map-wrap { width:100%; height:420px; border-radius:8px; overflow:hidden; border:1px solid #E2E8F0; }
    body:has(.tta-details) .tta-details-empty {
        background:#FFFFFF; border:1px dashed #E2E8F0; border-radius:10px;
        color:#64748B; padding:2rem; text-align:center;
    }
    body:has(.tta-details) .tta-details-table-wrap { width:100%; overflow:auto; border-radius:8px; border:1px solid #E2E8F0; }
    body:has(.tta-details) .tta-details-table { width:100%; border-collapse:separate; border-spacing:0; font-size:.75rem; color:#1E293B; }
    body:has(.tta-details) .tta-details-table thead th {
        background:#0A3642; color:#FFFFFF; font-weight:700; text-align:left;
        padding:.6rem .5rem; border:0; white-space:normal;
    }
    body:has(.tta-details) .tta-details-table tbody td {
        padding:.5rem .5rem; border-bottom:1px solid #F1F5F9; vertical-align:top;
    }
    body:has(.tta-details) .tta-details-table tbody tr:last-child td { border-bottom:0; }
    body:has(.tta-details) .tta-details-table tbody tr:nth-child(even) { background:#F8FAFC; }
    body:has(.tta-details) .tta-details-facility-badge {
        display:inline-flex; align-items:center; justify-content:center;
        width:1.5rem; height:1.5rem; border-radius:50%; color:#FFFFFF; font-size:.7rem;
    }
    body:has(.tta-details) .tta-details-info-banner {
        background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px;
        padding:.85rem 1rem; margin:1.25rem 0 0; display:flex; align-items:flex-start; gap:.75rem;
    }
    body:has(.tta-details) .tta-details-info-banner svg { width:1.25rem; height:1.25rem; color:#0D5C75; flex:0 0 1.25rem; margin-top:.05rem; }
    body:has(.tta-details) .tta-details-info-banner p { color:#1E3A5F; font-size:.85rem; line-height:1.5; margin:0; }
    body:has(.tta-details) [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        width:auto !important; min-width:0 !important; flex:none !important;
    }
    @media (max-width: 68.75rem) {
        body:has(.tta-details) .tta-details-hero { flex-direction:column; }
        body:has(.tta-details) .tta-details-hero-thumb { width:100%; height:auto; aspect-ratio:16/9; }
    }
    </style>
    """
    st.markdown(DETAILS_CSS, unsafe_allow_html=True)
    st.markdown("<div class='tta-details'></div>", unsafe_allow_html=True)

    header_left, header_right = st.columns([3.2, 1.8], vertical_alignment="center")
    with header_left:
        st.markdown(
            "<div class='tta-details-breadcrumb'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.5' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M3 12l2-2m0 0l7-7 7 7M5 12v13a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V2m0 0l7-7 7 7M7 17l1-1'/></svg>"
            f"<span>Accueil</span> / <span>Détails Commune</span> / "
            f"<span class='tta-details-current'>{html.escape(str(name_fr))}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='tta-details-title-group'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.5' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z'/><circle cx='12' cy='10' r='2.5'/></svg>"
            "<div><h1>Détails Commune</h1>"
            "<p>Explorer le profil démographique, les caractéristiques territoriales et les infrastructures de santé de chaque commune</p></div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with header_right:
        with st.container(key="details-nav"):
            nav_cols = st.columns([2, 1, 1, 1], gap="small", vertical_alignment="center")
            with nav_cols[0]:
                selected_label = st.selectbox(
                    "Sélectionner une commune...",
                    labels,
                    index=selected_index,
                    key="details_commune_selector",
                    label_visibility="collapsed",
                )
            with nav_cols[1]:
                if st.button("◀ Précédent", key="details_prev", width="stretch"):
                    new_index = (selected_index - 1) % len(sorted_communes)
                    st.session_state["details_commune"] = labels[new_index]
                    st.rerun()
            with nav_cols[2]:
                if st.button("Suivant ▶", key="details_next", width="stretch"):
                    new_index = (selected_index + 1) % len(sorted_communes)
                    st.session_state["details_commune"] = labels[new_index]
                    st.rerun()
            with nav_cols[3]:
                if st.button("Effacer", key="details_clear", width="stretch"):
                    st.session_state.pop("details_commune", None)
                    st.session_state["details_commune"] = _commune_label(sorted_communes[0])
                    st.rerun()

    if selected_label != _commune_label(selected_row):
        selected_row = label_to_row[selected_label]
        code = str(selected_row["commune_code"])
        name_fr = selected_row.get("name_fr", "Commune")
        province = selected_row.get("province", "")
        milieu = selected_row.get("milieu", "")
        population_2014 = selected_row.get("population_2014")
        population_2024 = selected_row.get("population_2024")
        area_km2 = selected_row.get("area_km2")
        density = selected_row.get("densite_hab_km2")
        if density is None and population_2024 and area_km2:
            density = population_2024 / area_km2
        commune_facilities = [f for f in facilities if str(f.get("commune_code")) == code]
        total_facilities = len(commune_facilities)
        facility_counts = Counter(
            str(f.get("facility_type", "healthcare_unspecified")) for f in commune_facilities
        )

    milieu_pill_colors = {"Urbain": "#0D5C75", "Mixte": "#16A34A", "Rural": "#D97706"}
    milieu_pill_color = milieu_pill_colors.get(milieu, "#64748B")

    thumb_svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
        "stroke-linejoin='round' aria-hidden='true'>"
        "<path d='M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z'/><circle cx='12' cy='10' r='2.5'/>"
        "<path d='M9 14l2-2 4 4'/><path d='M20 10v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5z'/></svg>"
    )

    hero_left, hero_center, hero_right = st.columns([0.8, 2.2, 1.5], gap="medium")
    with hero_left:
        st.markdown(
            f"<div class='tta-details-hero-thumb'>{thumb_svg}</div>",
            unsafe_allow_html=True,
        )
    with hero_center:
        st.markdown(
            f"<div class='tta-details-hero-name'>{html.escape(str(name_fr))}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='tta-details-hero-meta'>"
            f"<span><b>Code :</b> {html.escape(str(code))}</span>"
            f"<span><b>Province :</b> {html.escape(str(province))}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span class='tta-details-hero-pill' style='background:{milieu_pill_color}'>"
            f"{html.escape(str(milieu))}</span>"
            f" <span style='font-size:.85rem; color:#64748B;'>|</span>"
            f" <span style='font-size:.85rem; color:#64748B;'>Région : Tanger-Tétouan-Al Hoceïma</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='tta-details-hero-note'>"
            f"📍 Située dans la province de {html.escape(str(province))}, région Tanger-Tétouan-Al Hoceïma."
            f"</div>",
            unsafe_allow_html=True,
        )
    with hero_right:
        col_a, col_b, col_c = st.columns(3, gap="small")
        with col_a:
            if st.button(
                "📍 Localiser sur la carte",
                key="details_loc_map",
                width="stretch",
                help="Ouvrir Dashboard 2 centré sur cette commune",
            ):
                st.session_state["pending_navigation_page"] = "Interactive Risk Map"
                st.session_state["map_province_select"] = province
                st.session_state["map_commune_focus"] = code
                st.session_state["selected_page"] = "Interactive Risk Map"
                st.rerun()
        with col_b:
            if st.button(
                "⚖️ Comparer aux communes",
                key="details_compare",
                width="stretch",
                help="Ouvrir Dashboard 3 Classement Communes",
            ):
                st.session_state["pending_navigation_page"] = "Commune Ranking"
                st.session_state["selected_page"] = "Commune Ranking"
                st.rerun()
        with col_c:
            profile_rows = [
                {"Champ": "Code communal", "Valeur": code},
                {"Champ": "Commune", "Valeur": name_fr},
                {"Champ": "Province", "Valeur": province},
                {"Champ": "Milieu", "Valeur": milieu},
                {"Champ": "Population 2024", "Valeur": _fmt_int(population_2024)},
                {"Champ": "Superficie (km²)", "Valeur": _fmt_float(area_km2, 2)},
                {"Champ": "Densité (hab/km²)", "Valeur": _fmt_float(density, 1)},
                {"Champ": "Établissements de santé", "Valeur": _fmt_int(total_facilities)},
            ]
            profile_csv = pd.DataFrame(profile_rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "💾 Exporter le profil",
                data=profile_csv,
                file_name=f"profil_commune_{code}.csv",
                mime="text/csv",
                key="details_export",
                width="stretch",
            )
    pop_change_pct = None
    if population_2014 and population_2024:
        pop_change_pct = ((population_2024 - population_2014) / population_2014) * 100

    kpi_items = [
        {
            "label": "Population 2024",
            "value": _fmt_int(population_2024),
            "sub": "Habitants",
            "icon": "population",
        },
        {
            "label": "Évolution démographique",
            "value": (
                f"{pop_change_pct:+.1f}%" if pop_change_pct is not None else "Non disponible"
            ),
            "sub": "2014 → 2024",
            "icon": "trend",
        },
        {
            "label": "Superficie territoriale",
            "value": _fmt_float(area_km2, 2),
            "sub": "Kilomètres carrés",
            "icon": "area",
        },
        {
            "label": "Densité de population",
            "value": _fmt_float(density, 1),
            "sub": "Habitants par km²",
            "icon": "density",
        },
        {
            "label": "Établissements de santé",
            "value": _fmt_int(total_facilities),
            "sub": "Total associés à la commune",
            "icon": "facilities",
        },
    ]

    st.markdown(
        "<div class='tta-details-section-title'>Indicateurs clés</div>",
        unsafe_allow_html=True,
    )
    kpi_cols = st.columns(5, gap="medium")
    for col, item in zip(kpi_cols, kpi_items, strict=True):
        with col:
            if item["icon"] == "population":
                icon_svg = (
                    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
                    "stroke='#0D5C75' stroke-width='1.75' stroke-linecap='round' "
                    "stroke-linejoin='round' aria-hidden='true'>"
                    "<circle cx='12' cy='12' r='9'/><path d='M12 8v4m0 4h.01'/></svg>"
                )
            elif item["icon"] == "trend":
                icon_svg = (
                    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
                    "stroke='#0D5C75' stroke-width='1.75' stroke-linecap='round' "
                    "stroke-linejoin='round' aria-hidden='true'>"
                    "<path d='M17 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm6-7.8a4 4 0 0 1 0 7.6m2 4h1a4 4 0 0 1 3 2.8V21'/></svg>"
                )
            elif item["icon"] == "area":
                icon_svg = (
                    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
                    "stroke='#0D5C75' stroke-width='1.75' stroke-linecap='round' "
                    "stroke-linejoin='round' aria-hidden='true'>"
                    "<path d='M21 12a9 9 0 1 1-9-9 9 9 0 0 1 9 9Z'/></svg>"
                )
            elif item["icon"] == "density":
                icon_svg = (
                    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
                    "stroke='#0D5C75' stroke-width='1.75' stroke-linecap='round' "
                    "stroke-linejoin='round' aria-hidden='true'>"
                    "<circle cx='12' cy='12' r='9'/><path d='M12 8v4m0 4h.01'/></svg>"
                )
            else:
                icon_svg = (
                    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
                    "stroke='#0D5C75' stroke-width='1.75' stroke-linecap='round' "
                    "stroke-linejoin='round' aria-hidden='true'>"
                    "<path d='M12 5v14M5 12h14'/></svg>"
                )
            st.markdown(
                "<div class='tta-details-kpi'>"
                f"<div class='tta-details-kpi-icon'>{icon_svg}</div>"
                f"<div class='tta-details-kpi-value'>{html.escape(str(item['value']))}</div>"
                f"<p class='tta-details-kpi-label'>{html.escape(item['label'])}</p>"
                f"<p class='tta-details-kpi-sub'>{html.escape(item['sub'])}</p>"
                "</div>",
                unsafe_allow_html=True,
            )
    st.markdown(
        "<div class='tta-details-section-title'>Localisation et infrastructures</div>",
        unsafe_allow_html=True,
    )
    row2_cols = st.columns([1.35, 1, 1], gap="medium")

    with row2_cols[0]:
        st.markdown(
            "<div class='tta-details-card-title'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18-0Z'/><circle cx='12' cy='10' r='3'/></svg>"
            "Localisation Géographique"
            "</div>",
            unsafe_allow_html=True,
        )
        try:
            folium_map = get_initial_map(base_map="hybrid", add_tile_layers=True)
            build_commune_layer(
                [selected_row],
                commune_geojson,
                folium_map,
                facilities=commune_facilities,
                color_mode="environment",
                selected_code=code,
                milieu_colors=milieu_pill_colors,
                show=True,
            )
            if commune_facilities:
                commune_lookup = {str(r["commune_code"]): r for r in communes}
                build_facility_layer(
                    commune_facilities,
                    folium_map,
                    color_by_type=True,
                    symbol_markers=True,
                    commune_lookup=commune_lookup,
                    show=True,
                )
            lat = selected_row.get("centroid_lat")
            lon = selected_row.get("centroid_lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                folium_map.fit_bounds(
                    [[lat - 0.02, lon - 0.02], [lat + 0.02, lon + 0.02]],
                    padding=(10, 10),
                    max_zoom=14,
                )
                folium_map.location = [lat, lon]
                folium_map.zoom_start = 14
            st.markdown("<div class='tta-details-map-wrap'>", unsafe_allow_html=True)
            render_map(folium_map, height=380, key="details-map", returned_objects=[])
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as exc:
            st.error(f"Carte indisponible : {exc}")
    with row2_cols[1]:
        st.markdown(
            "<div class='tta-details-card-title'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M22 16v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm6-7.8a4 4 0 0 1 0 7.6m2 4h1a4 4 0 0 1 3 2.8V21'/></svg>"
            "Analyse Démographique"
            "</div>",
            unsafe_allow_html=True,
        )
        if population_2014 is not None and population_2024 is not None:
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=["Population"],
                    y=[population_2014],
                    name="2014",
                    marker_color="#2BB3A3",
                    text=[_fmt_int(population_2014)],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig.add_trace(
                go.Bar(
                    x=["Population"],
                    y=[population_2024],
                    name="2024",
                    marker_color="#0D5C75",
                    text=[_fmt_int(population_2024)],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig.update_layout(
                height=300,
                margin={"l": 8, "r": 8, "t": 8, "b": 42},
                barmode="group",
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font={"family": "Inter, Segoe UI, sans-serif", "size": 10, "color": "#334155"},
                showlegend=True,
                legend={"orientation": "h", "y": 1.02, "x": 0},
                xaxis={"gridcolor": "#E2E8F0", "zeroline": False, "tickfont": {"size": 9}},
                yaxis={"gridcolor": "#E2E8F0", "zeroline": False, "tickfont": {"size": 9}},
            )
            st.plotly_chart(
                fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}
            )
        else:
            st.markdown(
                "<div class='tta-details-empty'>Données démographiques incomplètes pour cette commune.</div>",
                unsafe_allow_html=True,
            )
    with row2_cols[2]:
        st.markdown(
            "<div class='tta-details-card-title'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 17.5a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11Z'/></svg>"
            "Répartition des Établissements"
            "</div>",
            unsafe_allow_html=True,
        )
        if total_facilities > 0:
            facility_order = [
                "hospital",
                "clinic",
                "pharmacy",
                "doctors",
                "laboratory",
                "healthcare_unspecified",
                "physiotherapist",
            ]
            facility_labels = {
                "hospital": "Hôpitaux",
                "clinic": "Cliniques",
                "pharmacy": "Pharmacies",
                "doctors": "Médecins",
                "laboratory": "Laboratoires",
                "healthcare_unspecified": "Autres",
                "physiotherapist": "Autres",
            }
            facility_colors = {
                "hospital": "#1D4ED8",
                "clinic": "#DC2626",
                "pharmacy": "#16A34A",
                "doctors": "#D97706",
                "laboratory": "#7C3AED",
                "healthcare_unspecified": "#475569",
                "physiotherapist": "#475569",
            }
            donut_labels = []
            donut_values = []
            donut_colors = []
            for kind in facility_order:
                cnt = facility_counts.get(kind, 0)
                if cnt > 0:
                    donut_labels.append(facility_labels[kind])
                    donut_values.append(cnt)
                    donut_colors.append(facility_colors[kind])
            fig = go.Figure(
                go.Pie(
                    labels=donut_labels,
                    values=donut_values,
                    hole=0.6,
                    marker_colors=donut_colors,
                    textposition="none",
                    hoverinfo="label+value+percent",
                    sort=False,
                )
            )
            fig.update_layout(
                height=300,
                margin={"l": 8, "r": 8, "t": 8, "b": 8},
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font={"family": "Inter, Segoe UI, sans-serif", "size": 10, "color": "#334155"},
                showlegend=False,
                annotations=[
                    dict(
                        text=f"<b>{total_facilities}</b><br>Établissements",
                        x=0.5,
                        y=0.5,
                        font_size=16,
                        font_color="#0D5C75",
                        showarrow=False,
                    ),
                    dict(
                        text="dans OSM",
                        x=0.5,
                        y=0.56,
                        font_size=10,
                        font_color="#64748B",
                        showarrow=False,
                    ),
                ],
            )
            st.plotly_chart(
                fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}
            )
            st.markdown(
                "<div class='tta-details-card-title' style='margin-top:.75rem;'>"
                "Répartition par type"
                "</div>",
                unsafe_allow_html=True,
            )
            for kind in facility_order:
                cnt = facility_counts.get(kind, 0)
                if cnt > 0:
                    color = facility_colors[kind]
                    st.markdown(
                        f"<div style='display:flex; align-items:center; gap:.5rem; font-size:.75rem; color:#475569; margin:.25rem 0;'>"
                        f"<span class='tta-details-facility-badge' style='background:{color};'>{facility_icon_svg(kind, size=10)}</span>"
                        f"<span style='flex:1;'>{html.escape(facility_labels[kind])}</span>"
                        f"<span style='font-weight:700; color:#0F172A;'>{cnt}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                "<div class='tta-details-empty'>0 établissement enregistré dans OSM pour cette commune.</div>",
                unsafe_allow_html=True,
            )
    row3_cols = st.columns([1.35, 1], gap="medium")

    with row3_cols[0]:
        st.markdown(
            "<div class='tta-details-card-title'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M4 5h16l-6.5 7.5V19l-3 1v-7.5L4 5Z'/></svg>"
            f"Établissements de santé dans {html.escape(str(name_fr))}"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='tta-details-table-wrap'>", unsafe_allow_html=True)
        if commune_facilities:
            type_badge_colors = {
                "hospital": "#DC2626",
                "clinic": "#1D4ED8",
                "pharmacy": "#16A34A",
                "doctors": "#D97706",
                "laboratory": "#7C3AED",
                "healthcare_unspecified": "#475569",
                "physiotherapist": "#475569",
            }
            type_labels = {
                "hospital": "Hôpital",
                "clinic": "Clinique",
                "pharmacy": "Pharmacie",
                "doctors": "Médecin",
                "laboratory": "Laboratoire",
                "healthcare_unspecified": "Autre",
                "physiotherapist": "Autre",
            }
            table_rows = []
            for index, facility in enumerate(commune_facilities, start=1):
                f_type = str(facility.get("facility_type", "healthcare_unspecified"))
                f_type_label = type_labels.get(f_type, "Autre")
                f_color = type_badge_colors.get(f_type, "#475569")
                table_rows.append(
                    f"<tr>"
                    f"<td>{index}</td>"
                    f"<td>{html.escape(str(facility.get('name') or 'Nom non renseigné'))}</td>"
                    f"<td><span class='tta-details-facility-badge' style='background:{f_color};'>{facility_icon_svg(f_type, size=10)}</span> {html.escape(f_type_label)}</td>"
                    f"<td>{html.escape(str(facility.get('addr_city') or 'Non renseignée'))}</td>"
                    f"<td style='font-family:monospace; font-size:.68rem;'>{html.escape(str(facility.get('osm_id', '')))}</td>"
                    f"</tr>"
                )
            st.markdown(
                "<table class='tta-details-table'>"
                "<thead><tr>"
                "<th>#</th>"
                "<th>Nom de l'établissement</th>"
                "<th>Type</th>"
                "<th>Localisation / Quartier</th>"
                "<th>Identifiant OSM</th>"
                "</tr></thead>"
                f"<tbody>{''.join(table_rows)}</tbody>"
                "</table>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='tta-details-empty'>"
                "Aucun établissement de santé n'est associé à cette commune dans le jeu de données OpenStreetMap."
                "</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    with row3_cols[1]:
        st.markdown(
            "<div class='tta-details-card-title'>"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
            "stroke-linejoin='round' aria-hidden='true'>"
            "<path d='M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 17.5a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11Z'/></svg>"
            "Contexte Régional"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='tta-details-table-wrap'>", unsafe_allow_html=True)
        context_rows = [
            (
                "Densité de population (hab/km²)",
                _fmt_float(density, 1),
                _fmt_float(province_avg_density, 1),
                _fmt_float(region_avg_density, 1),
            ),
            (
                "Établissements de santé (moy. / commune)",
                _fmt_int(round(province_avg_facilities, 1)),
                _fmt_int(round(province_avg_facilities, 1)),
                _fmt_int(round(region_avg_facilities, 1)),
            ),
            (
                "Établissements / 10 000 hab.",
                _fmt_float(ratio_commune, 1),
                _fmt_float(ratio_province, 1),
                _fmt_float(ratio_region, 1),
            ),
            ("Environnement territorial", milieu, province, "Mixte"),
        ]
        table_html = "<table class='tta-details-table'>"
        table_html += (
            "<thead><tr><th>Indicateur</th><th style='width:30%;'>"
            + html.escape(str(name_fr))
            + "</th><th>Moy. Province ("
            + html.escape(str(province))
            + ")</th><th>Moy. Régionale (TTA)</th></tr></thead>"
        )
        table_html += "<tbody>"
        for indicator, commune_val, province_val, region_val in context_rows:
            table_html += (
                f"<tr>"
                f"<td style='font-weight:600; color:#0F172A;'>{html.escape(str(indicator))}</td>"
                f"<td style='font-weight:700; color:#0D5C75;'>{html.escape(str(commune_val))}</td>"
                f"<td>{html.escape(str(province_val))}</td>"
                f"<td>{html.escape(str(region_val))}</td>"
                f"</tr>"
            )
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='tta-details-info-banner'>"
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        "stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
        "stroke-linejoin='round' aria-hidden='true'>"
        "<circle cx='12' cy='12' r='9'/><path d='M12 11v5m0-8h.01'/></svg>"
        "<p>Les indicateurs validés de risque et d'accessibilité aux soins ne sont pas encore disponibles pour cette commune. Ce profil présente uniquement les données démographiques et d'infrastructures vérifiées.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _population_by_province(communes: list[dict]) -> pd.DataFrame:
    data = defaultdict(lambda: {"2014": 0, "2024": 0})
    for row in communes:
        data[row["province"]]["2014"] += row.get("population_2014") or 0
        data[row["province"]]["2024"] += row.get("population_2024") or 0
    return pd.DataFrame([{"Province": p, **values} for p, values in sorted(data.items())])


def render_trends(communes: list[dict], facilities: list[dict]) -> None:
    _title(
        "Trends & Historical Analysis",
        "Explore demographic evolution, healthcare infrastructure trends, environmental variations and historical territorial risk indicators across the TTA region.",
    )
    with st.container(border=True):
        st.markdown("**Historical Analysis Filters**")
        c1, c2 = st.columns([1, 2])
        with c1:
            indicator = st.selectbox(
                "Historical Indicator",
                [
                    "Population Evolution",
                    "Healthcare Infrastructure Evolution",
                    "Healthcare Risk Score Evolution",
                    "Healthcare Accessibility Evolution",
                    "Weather and Environmental Trends",
                ],
                key="trends_indicator",
            )
        with c2:
            st.selectbox("Reference years", ["2014 → 2024"], key="trends_period")
    total_2014 = sum(row.get("population_2014") or 0 for row in communes)
    total_2024 = sum(row.get("population_2024") or 0 for row in communes)
    variation = total_2024 - total_2014
    variation_pct = _safe_ratio(variation * 100, total_2014)
    if indicator == "Population Evolution":
        kpi_row(
            [
                {"label": "Selected Period", "value": "2014 → 2024", "icon": "◷"},
                {
                    "label": "Available Records",
                    "value": 2,
                    "description": "Années de référence valides.",
                    "icon": "▤",
                },
                {"label": "Communes Covered", "value": len(communes), "icon": "◉"},
                {
                    "label": "Observed Variation",
                    "value": f"{variation_pct:+.2f}%"
                    if variation_pct is not None
                    else "Not available",
                    "icon": "↗",
                },
            ]
        )
        st.markdown("### Historical Trends Overview")
        fig = go.Figure(
            go.Bar(
                x=["2014", "2024"],
                y=[total_2014, total_2024],
                marker_color=[COLORS["milieu"]["Rural"], THEME.turquoise],
                text=[_fmt(total_2014), _fmt(total_2024)],
                textposition="outside",
            )
        )
        _chart(fig, 330)
        st.markdown("### Demographic Evolution — 2014 to 2024")
        province_df = _population_by_province(communes)
        fig = go.Figure()
        fig.add_bar(
            x=province_df["Province"],
            y=province_df["2014"],
            name="2014",
            marker_color=COLORS["milieu"]["Rural"],
        )
        fig.add_bar(
            x=province_df["Province"],
            y=province_df["2024"],
            name="2024",
            marker_color=THEME.turquoise,
        )
        fig.update_layout(barmode="group")
        _chart(fig, 340)
        growth = []
        for row in communes:
            if row.get("population_2014") is not None and row.get("population_2024") is not None:
                growth.append((row["name_fr"], row["population_2024"] - row["population_2014"]))
        growth.sort(key=lambda x: x[1], reverse=True)
        c1, c2 = st.columns(2)
        for col, title, values, color in [
            (c1, "Top population growth", growth[:10], THEME.turquoise),
            (
                c2,
                "Lowest population variation",
                list(reversed(growth[-10:])),
                COLORS["milieu"]["Rural"],
            ),
        ]:
            with col:
                with st.container(border=True):
                    st.markdown(f"### {title}")
                    fig = go.Figure(
                        go.Bar(
                            x=[v for _, v in reversed(values)],
                            y=[n for n, _ in reversed(values)],
                            orientation="h",
                            marker_color=color,
                        )
                    )
                    _chart(fig, 320)
    else:
        kpi_row(
            [
                {"label": "Selected Period", "value": "Not available", "icon": "◷"},
                {"label": "Available Records", "value": "Not available", "icon": "▤"},
                {"label": "Communes Covered", "value": "Not available", "icon": "◉"},
                {"label": "Observed Variation", "value": "Not available", "icon": "↗"},
            ]
        )
        _unavailable(
            "Historical Trends Overview",
            "Cette série historique n’est pas encore intégrée. La comparaison démographique 2014 → 2024 reste disponible.",
        )
    _unavailable(
        "Historical Territorial Risk Analysis",
        "Historical risk analysis is awaiting validated daily risk records from the risk-scoring pipeline.",
    )
    _unavailable(
        "Environmental Trends",
        "Historical environmental observations are not yet available for this analysis.",
    )
    _unavailable(
        "Temporal Activity Heatmap",
        "La heatmap reste désactivée jusqu’à l’intégration d’un jeu historique adapté.",
    )
    with st.container(border=True):
        st.markdown("### Historical Data Coverage")
        st.info(
            "Population : observations de référence 2014 et 2024 disponibles. Les séries quotidiennes de risque, météo, accessibilité et évolution des établissements ne sont pas encore intégrées."
        )


def render_alerts(communes: list[dict], facilities: list[dict]) -> None:
    _title(
        "Alerts & Priority Areas",
        "Monitor territorial alerts, identify priority communes, and investigate emerging healthcare vulnerability situations across the TTA region.",
    )
    kpi_row(
        [
            {
                "label": "Active Alerts",
                "value": "Not available",
                "description": "Alert data not yet integrated",
                "icon": "!",
            },
            {"label": "Critical Alerts", "value": "Not available", "icon": "!"},
            {"label": "Priority Communes", "value": "Not available", "icon": "◉"},
            {"label": "Pending Review", "value": "Not available", "icon": "◷"},
        ]
    )
    with st.container(border=True):
        st.markdown("### Alert Filters")
        st.info(
            "Les filtres de sévérité, statut et période seront activés après intégration des enregistrements d’alertes et de leurs règles validées."
        )
    c1, c2 = st.columns([1.5, 1])
    with c1:
        with st.container(border=True):
            st.markdown("### Regional Priority Areas")
            st.caption(
                "Les limites communales sont disponibles, mais aucune zone prioritaire validée ne peut être affichée."
            )
            st.map(
                pd.DataFrame(
                    {
                        "lat": [r["centroid_lat"] for r in communes],
                        "lon": [r["centroid_lon"] for r in communes],
                    }
                ),
                zoom=7,
                use_container_width=True,
            )
    with c2:
        _unavailable(
            "Priority Areas Ranking",
            "Aucun classement de priorité n’est affiché sans alertes validées.",
        )
    _unavailable("Alert Management", "Alert data not yet integrated")
    _unavailable(
        "Alert Details & Lifecycle",
        "Les détails, statuts, historiques et transitions seront disponibles après intégration du workflow d’alertes.",
    )


def render_monitoring(communes: list[dict], facilities: list[dict]) -> None:
    _title(
        "System Monitoring",
        "Operational status of data sources, processing pipelines and dashboard dependencies.",
    )
    root = Path(__file__).resolve().parents[2]
    checks = [
        ("Communes CSV", root / "data/processed/communes_TTA_2024.csv", len(communes), 146),
        (
            "Communes GeoJSON",
            root / "data/processed/communes_TTA.geojson",
            "FeatureCollection",
            "FeatureCollection",
        ),
        (
            "Healthcare facilities CSV",
            root / "data/processed/health_facilities_TTA.csv",
            len(facilities),
            892,
        ),
    ]
    available = sum(path.exists() for _, path, _, _ in checks)
    kpi_row(
        [
            {
                "label": "Sources Available",
                "value": f"{available}/{len(checks)}",
                "description": "Contrôles locaux réussis.",
                "icon": "✓",
            },
            {"label": "Communes Loaded", "value": len(communes), "icon": "◉"},
            {"label": "Facilities Loaded", "value": len(facilities), "icon": "▣"},
            {
                "label": "Unassigned Facilities",
                "value": sum(1 for f in facilities if f.get("commune_code") is None),
                "icon": "○",
            },
        ]
    )
    with st.container(border=True):
        st.markdown("### Data Source Health")
        table = []
        for label, path, observed, expected in checks:
            table.append(
                {
                    "Source": label,
                    "Statut": "Disponible" if path.exists() else "Indisponible",
                    "Chemin": str(path.relative_to(root)) if path.exists() else "—",
                    "Observation": observed,
                    "Référence": expected,
                }
            )
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("### Pipeline Coverage")
            st.info(
                "Le monitoring confirme la disponibilité des fichiers locaux chargés par l’application. Les exécutions Airflow, la base PostgreSQL et les appels externes nécessitent une connexion à leur environnement opérationnel."
            )
    with c2:
        with st.container(border=True):
            st.markdown("### Data Integrity")
            st.success(
                "Les identifiants communaux sont conservés comme chaînes et les établissements non affectés restent séparés des statistiques communales."
            )
    _unavailable(
        "Risk & Accessibility Pipeline",
        "Les métriques opérationnelles détaillées seront affichées après intégration des sorties validées de scoring et d’accessibilité.",
    )
