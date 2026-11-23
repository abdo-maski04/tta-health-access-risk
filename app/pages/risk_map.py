"""Enterprise GIS map for commune and healthcare-facility exploration."""

from __future__ import annotations

import html
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from html import unescape
from typing import Any

import folium
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from data_loader import COMMUNES_CSV, COMMUNES_GEOJSON
from map_utils import (
    NUMERIC_MAP_MODES,
    RISK_FACILITY_COLORS,
    RISK_MILIEU_COLORS,
    add_enterprise_map_controls,
    build_commune_layer,
    build_facility_layer,
    build_heatmap_layer,
    build_proportional_bubble_layer,
    build_unassigned_facility_layer,
    commune_color_values,
    facility_icon_svg,
    geojson_bounds,
    get_initial_map,
    numeric_color_range,
    render_map,
)
from pyproj import Geod
from pages.health_map import render_health_map
from pages.territorial_risk_map import render_territorial_risk_map
from pages.hospital_routes_map import render_hospital_routes_map

REGION_NAME = "Tanger-Tétouan-Al Hoceïma"
BASE_MAP_CHOICES = {
    "Satellite Haute Résolution": "satellite",
    "Satellite Hybride": "hybrid",
    "Clair Professionnel": "light",
    "Sombre": "dark",
    "Relief / Topographique": "terrain",
}
THEMATIC_CHOICES = {
    "Milieu territorial": "environment",
    "Population 2024": "population",
    "Densité de population 2024": "density",
    "Nombre d'établissements": "facilities",
}
FACILITY_GROUPS = {
    "hospital": ("Hôpitaux", "fac_hospital"),
    "clinic": ("Cliniques", "fac_clinic"),
    "pharmacy": ("Pharmacies", "fac_pharmacy"),
    "doctors": ("Médecins / Cabinets", "fac_doctors"),
    "laboratory": ("Laboratoires", "fac_laboratory"),
    "other": ("Autres établissements", "fac_other"),
}
FACILITY_TYPES = {
    "hospital": {"hospital"},
    "clinic": {"clinic"},
    "pharmacy": {"pharmacy"},
    "doctors": {"doctors"},
    "laboratory": {"laboratory"},
    "other": {"physiotherapist", "healthcare_unspecified"},
}
FACILITY_LABELS = {
    kind: FACILITY_GROUPS[group][0]
    for group, types in FACILITY_TYPES.items()
    for kind in types
}
GEOD = Geod(ellps="WGS84")

MAP_SCREEN_CSS = """
<style>
body:has(.tta-map-screen) [data-testid="stMainBlockContainer"] {
    max-width: none !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}
body:has(.tta-map-screen) .st-key-tta-global-header {
    position: relative;
    z-index: 20;
    box-sizing: border-box;
    min-height: var(--tta-header-height);
    height: auto;
    margin: 0;
    padding: 0.65rem 1.5rem;
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
body:has(.tta-map-screen) .st-key-risk-map-canvas {
    position: fixed !important;
    top: var(--tta-header-height);
    right: 0;
    bottom: 0;
    left: var(--tta-map-left, 230px);
    z-index: 1;
    width: auto !important;
    height: calc(100vh - var(--tta-header-height)) !important;
    min-height: 350px !important;
    margin: 0 !important;
    padding: 0 !important;
    background: #EAF1F3;
    z-index: 1;
}
body:has(.tta-map-screen) .st-key-risk-map-canvas [data-testid="stCustomComponentV1"],
body:has(.tta-map-screen) .st-key-risk-map-canvas iframe {
    display: block !important;
    width: 100% !important;
    height: calc(100vh - var(--tta-header-height)) !important;
    min-height: 350px !important;
    border: 0 !important;
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
body:has(.tta-map-screen) .st-key-risk-map-search,
body:has(.tta-map-screen) .st-key-risk-map-inspector,
body:has(.tta-map-screen) .st-key-risk-map-open {
    position: fixed !important;
    z-index: 1100;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(15,23,42,.18);
}
body:has(.tta-map-screen) .st-key-risk-map-search {
    top: 78px;
    left: calc(var(--tta-map-left, 250px) + 72px);
    width: min(390px, calc(100vw - var(--tta-map-left, 250px) - 460px));
    min-width: 260px;
    padding: 9px 10px 5px;
}
body:has(.tta-map-screen) .st-key-risk-map-inspector {
    top: 80px;
    right: 18px;
    width: 350px;
    max-height: 82vh;
    overflow-y: auto;
    padding: 12px;
}
body:has(.tta-map-screen) .st-key-risk-map-open {
    top: 80px;
    right: 18px;
    width: 210px;
    padding: 8px;
}
body:has(.tta-map-screen) .st-key-risk-map-inspector [data-testid="stTabs"] [role="tablist"] {
    gap: 0;
    border-radius: 7px;
    background: #0D5C75;
    padding: 3px;
}
body:has(.tta-map-screen) .st-key-risk-map-inspector [data-testid="stTabs"] [role="tab"] {
    flex: 1;
    min-height: 32px;
    color: rgba(255,255,255,.75) !important;
    font-size: 11px;
    background: transparent !important;
    border: 0 !important;
}
body:has(.tta-map-screen) .st-key-risk-map-inspector [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #FFFFFF !important;
    background: transparent !important;
    border-bottom: 2px solid #14B8A6 !important;
    border-radius: 0;
    font-weight: 750;
}
body:has(.tta-map-screen) .st-key-risk-map-inspector [data-testid="stTabs"] [role="tab"] * {
    color: inherit !important;
}
body:has(.tta-map-screen) .st-key-risk-map-inspector [data-testid="stMarkdownContainer"] p,
body:has(.tta-map-screen) .st-key-risk-map-search [data-testid="stMarkdownContainer"] p {
    font-size: 11px;
}
body:has(.tta-map-screen) .tta-inspector-heading {
    color: #0F172A;
    font-size: 14px;
    font-weight: 750;
    line-height: 1.3;
    padding: 2px 0 7px;
    cursor: move;
}
body:has(.tta-map-screen) .tta-inspector-subtitle {
    color: #64748B;
    font-size: 10px;
    font-weight: 500;
    margin-top: 2px;
}
body:has(.tta-map-screen) .tta-map-kpi {
    padding: 7px 5px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 7px;
    text-align: center;
}
body:has(.tta-map-screen) .tta-map-kpi-value {
    color: #0F172A;
    font-size: 17px;
    font-weight: 750;
    line-height: 1.15;
}
body:has(.tta-map-screen) .tta-map-kpi-label {
    color: #64748B;
    font-size: 9px;
    line-height: 1.2;
    margin-top: 3px;
}
body:has(.tta-map-screen) .tta-map-section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 9px 0 4px;
    color: #334155;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .04em;
}
body:has(.tta-map-screen) .tta-map-section-label svg {
    width: 15px;
    height: 15px;
    flex: 0 0 15px;
    stroke: #0D5C75;
}
body:has(.tta-map-screen) .tta-facility-filter-icon {
    display: inline-flex;
    width: 24px;
    height: 24px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
}
body:has(.tta-map-screen) .tta-facility-filter-icon svg {
    display: block;
}
body:has(.tta-map-screen) .tta-future-indicator {
    margin: 8px 0 2px;
    padding: 8px;
    border-left: 3px solid #94A3B8;
    border-radius: 4px;
    background: #F1F5F9;
    color: #64748B;
    font-size: 10px;
    line-height: 1.4;
}
body:has(.tta-map-screen) .tta-map-legend-line {
    display: flex;
    flex-wrap: wrap;
    gap: 5px 9px;
    margin: 5px 0 8px;
}
body:has(.tta-map-screen) .tta-map-legend-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: #475569;
    font-size: 10px;
}
body:has(.tta-map-screen) .tta-map-legend-swatch {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
}
body:has(.tta-map-screen) .st-key-risk-map-drag-bridge {
    display: none !important;
}
body:has(.tta-map-screen) [data-testid="stHeader"] {
    height: auto !important;
    background: transparent !important;
    pointer-events: none !important;
    z-index: 999990 !important;
}
body:has(.tta-map-screen) [data-testid="stHeader"] [data-testid="stToolbar"],
body:has(.tta-map-screen) [data-testid="stHeader"] button {
    pointer-events: auto !important;
}
body:has(.tta-map-screen):has([data-testid="stSidebar"][data-collapsed="false"]),
body:has(.tta-map-screen):has([data-testid="stSidebar"][aria-expanded="true"]) {
    --tta-map-left: 250px;
}
body:has(.tta-map-screen):has([data-testid="stSidebar"][data-collapsed="true"]),
body:has(.tta-map-screen):has([data-testid="stSidebar"][aria-expanded="false"]) {
    --tta-map-left: 0px;
}
@media(max-width:1050px) {
    body:has(.tta-map-screen) .st-key-risk-map-inspector {
        right: 8px;
        width: min(340px, calc(100vw - var(--tta-map-left, 230px) - 18px));
    }
    body:has(.tta-map-screen) .st-key-risk-map-search {
    left: calc(var(--tta-map-left, 250px) + 72px);
    width: min(340px, calc(100vw - var(--tta-map-left, 250px) - 425px));
    }
}
@media(max-width:720px) {
    body:has(.tta-map-screen) .st-key-risk-map-inspector {
        top: 360px;
        right: 8px;
        width: min(340px, calc(100vw - var(--tta-map-left, 0px) - 16px));
        max-height: calc(100vh - 370px);
    }
    body:has(.tta-map-screen) .st-key-risk-map-search {
        top: 78px;
        left: calc(var(--tta-map-left, 0px) + 72px);
        width: calc(100vw - var(--tta-map-left, 0px) - 112px);
        min-width: 0;
    }
}
</style>
"""


def _geojson_fingerprint(geojson: dict[str, Any]) -> str:
    payload = json.dumps(geojson, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _commune_geojson_cache_key() -> str:
    return "|".join(
        f"{path.resolve()}:{path.stat().st_mtime_ns}:{path.stat().st_size}"
        for path in (COMMUNES_CSV, COMMUNES_GEOJSON)
    )


def _calculate_commune_areas_km2(geojson: dict) -> dict[str, float]:
    """Compute geodesic polygon areas on WGS84, excluding interior rings."""
    areas = {}
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            raise ValueError(
                f"Géométrie communale non prise en charge: {geometry['type']}"
            )

        area_m2 = 0.0
        for polygon in polygons:
            ring_areas = []
            for ring in polygon:
                longitudes = [point[0] for point in ring]
                latitudes = [point[1] for point in ring]
                ring_area, _ = GEOD.polygon_area_perimeter(longitudes, latitudes)
                ring_areas.append(abs(ring_area))
            if ring_areas:
                area_m2 += max(0.0, ring_areas[0] - sum(ring_areas[1:]))
        if area_m2 > 0:
            code = str(feature["properties"]["commune_code"]).strip()
            areas[code] = area_m2 / 1_000_000
    return areas


@st.cache_data(show_spinner=False, max_entries=2)
def _cached_commune_areas_km2(
    _geojson: dict[str, Any],
    cache_key: str,
) -> dict[str, float]:
    return _calculate_commune_areas_km2(_geojson)


def commune_areas_km2(
    geojson: dict[str, Any],
    *,
    cache_key: str | None = None,
) -> dict[str, float]:
    return _cached_commune_areas_km2(
        geojson,
        cache_key or _geojson_fingerprint(geojson),
    )


def _simplify_geojson(
    geojson: dict[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    from shapely.geometry import mapping, shape

    simplified = dict(geojson)
    simplified["features"] = []
    for feature in geojson.get("features", []):
        simplified_feature = dict(feature)
        geometry = shape(feature["geometry"]).simplify(
            tolerance,
            preserve_topology=True,
        )
        simplified_feature["geometry"] = mapping(geometry)
        simplified["features"].append(simplified_feature)
    return simplified


@st.cache_data(show_spinner=False, max_entries=2)
def _cached_simplify_geojson(
    _geojson: dict[str, Any],
    cache_key: str,
    tolerance: float,
) -> dict[str, Any]:
    return _simplify_geojson(_geojson, tolerance)


def simplify_commune_geojson(
    geojson: dict[str, Any],
    tolerance: float = 0.001,
    *,
    cache_key: str | None = None,
) -> dict[str, Any]:
    """Cache a topology-preserving GeoJSON copy at web-map resolution."""
    return _cached_simplify_geojson(
        geojson,
        cache_key or _geojson_fingerprint(geojson),
        tolerance,
    )


@st.cache_data(show_spinner=False)
def _filter_facilities_by_scope(
    facilities: list[dict],
    commune_codes: tuple[str, ...] | None = None,
    facility_types: tuple[str, ...] | None = None,
    assigned: bool | None = None,
) -> list[dict]:
    code_set = set(commune_codes) if commune_codes is not None else None
    type_set = set(facility_types) if facility_types is not None else None
    return [
        row
        for row in facilities
        if (assigned is None or (row.get("commune_code") is not None) is assigned)
        and (
            code_set is None
            or str(row.get("commune_code") or "").strip() in code_set
        )
        and (type_set is None or row.get("facility_type") in type_set)
    ]


def _normalize_search(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


@st.cache_data(show_spinner=False)
def filter_facility_search(
    facilities: list[dict],
    search: str,
) -> list[dict]:
    needle = _normalize_search(search)
    if not needle:
        return facilities
    searchable_fields = (
        "name",
        "facility_type",
        "healthcare",
        "addr_city",
        "addr_street",
    )
    return [
        row
        for row in facilities
        if any(
            needle in _normalize_search(str(row.get(field) or ""))
            for field in searchable_fields
        )
        or needle
        in _normalize_search(
            FACILITY_LABELS.get(
                str(row.get("facility_type", "healthcare_unspecified")),
                "Autres",
            )
        )
    ]


def filter_map_communes(
    communes: list[dict],
    provinces: list[str],
    milieux: list[str],
    search: str,
) -> list[dict]:
    needle = _normalize_search(search)
    province_set = set(provinces)
    milieu_set = set(milieux)
    return [
        row
        for row in communes
        if (not province_set or row["province"] in province_set)
        and (not milieu_set or row["milieu"] in milieu_set)
        and (
            not needle
            or needle
            in _normalize_search(
                " ".join(
                    (
                        str(row.get("name_fr", "")),
                        str(row.get("name_ar", "")),
                        str(row.get("commune_code", "")),
                        str(row.get("province", "")),
                    )
                )
            )
        )
    ]


def commune_code_from_map_event(
    event: dict[str, Any] | None,
    geojson: dict[str, Any] | None = None,
) -> str | None:
    if not isinstance(event, dict):
        return None
    drawing = event.get("last_active_drawing")
    if isinstance(drawing, dict):
        properties = drawing.get("properties") or {}
        code = properties.get("commune_code")
        if code is not None:
            return str(code).strip()
    popup = event.get("last_object_clicked_popup")
    if isinstance(popup, str):
        match = re.search(
            r"(?:<b>)?\s*Code:\s*(?:</b>)?\s*([^<\r\n]+)",
            popup,
            flags=re.IGNORECASE,
        )
        if match:
            return unescape(match.group(1)).strip()
        for line in popup.splitlines():
            if line.startswith("Code:"):
                return unescape(line.partition(":")[2]).strip()
        return None

    clicked_point = event.get("last_object_clicked")
    if isinstance(clicked_point, dict) and geojson is not None:
        latitude = clicked_point.get("lat")
        longitude = clicked_point.get("lng")
        if latitude is None or longitude is None:
            return None
        try:
            from shapely.geometry import Point, shape
        except ImportError:
            return None
        point = Point(longitude, latitude)
        for feature in geojson.get("features", []):
            if shape(feature["geometry"]).contains(point):
                code = feature.get("properties", {}).get("commune_code")
                if code is not None:
                    return str(code).strip()
    return None


def _format_number(value: object, decimals: int = 0) -> str:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        return "Non disponible"
    return f"{value:,.{decimals}f}".replace(",", " ")


def _facility_group(row: dict) -> str:
    kind = str(row.get("facility_type", "healthcare_unspecified"))
    for group, types in FACILITY_TYPES.items():
        if kind in types:
            return group
    return "other"


def _facility_type_counts(facilities: list[dict]) -> Counter[str]:
    return Counter(_facility_group(row) for row in facilities)


def _facility_types_from_state() -> list[str]:
    return sorted(
        kind
        for group, (_, key) in FACILITY_GROUPS.items()
        if st.session_state.get(key, True)
        for kind in FACILITY_TYPES[group]
    )


def _reset_map_filters() -> None:
    defaults = {
        "risk_map_search": "",
        "risk_search_active": "",
        "risk_search_target": "",
        "risk_province_filter": "Toutes les provinces",
        "risk_commune_filter": "Toutes les communes",
        "risk_milieu_filter": "Tous",
        "risk_base_map": "Satellite Haute Résolution",
        "risk_thematic_mode": "Milieu territorial",
        "risk_bubble_metric": "Établissements associés",
        "risk_show_boundaries": True,
        "risk_show_facilities": True,
        "risk_show_unassigned": True,
        "risk_show_bubbles": False,
        "risk_show_heatmap": False,
        "risk_inspector_collapsed": False,
        "risk_inspector_visible": True,
        "risk_future_accessibility": False,
        "risk_future_risk": False,
    }
    defaults.update({key: True for _, key in FACILITY_GROUPS.values()})
    st.session_state.update(defaults)
    st.session_state["risk_selected_commune_code"] = None


def _recenter_map() -> None:
    st.session_state["risk_province_filter"] = "Toutes les provinces"
    st.session_state["risk_commune_filter"] = "Toutes les communes"
    st.session_state["risk_milieu_filter"] = "Tous"
    st.session_state["risk_search_active"] = ""
    st.session_state["risk_search_target"] = ""
    st.session_state["risk_search_status"] = ""
    st.session_state["risk_selected_commune_code"] = None
    st.session_state["risk_map_search"] = ""


def _search_target(
    query: str,
    communes: list[dict],
    facilities: list[dict],
) -> tuple[str, str | None]:
    needle = _normalize_search(query)
    if not needle:
        return "", None
    province_names = sorted({str(row["province"]) for row in communes})
    exact_province = next(
        (
            province
            for province in province_names
            if _normalize_search(province) == needle
        ),
        None,
    )
    if exact_province:
        return "province", exact_province
    partial_provinces = [
        province
        for province in province_names
        if needle in _normalize_search(province)
    ]
    if len(partial_provinces) == 1:
        return "province", partial_provinces[0]
    commune_matches = filter_map_communes(communes, [], [], query)
    if commune_matches:
        return "commune", str(commune_matches[0]["commune_code"])
    if filter_facility_search(facilities, query):
        return "facility", None
    return "none", None


def _drag_panel_script() -> None:
    components.html(
        """
        <script>
        const doc = window.parent.document;
        const panel = doc.querySelector('.st-key-risk-map-inspector');
        if (panel && !panel.dataset.dragBound) {
          panel.dataset.dragBound = 'true';
          const handle = panel.querySelector('.tta-inspector-heading');
          if (handle) {
            handle.addEventListener('pointerdown', (event) => {
              if (event.target.closest('button')) return;
              const rect = panel.getBoundingClientRect();
              const startX = event.clientX;
              const startY = event.clientY;
              panel.style.left = rect.left + 'px';
              panel.style.top = rect.top + 'px';
              panel.style.right = 'auto';
              const move = (moveEvent) => {
                panel.style.left = Math.max(4, rect.left + moveEvent.clientX - startX) + 'px';
                panel.style.top = Math.max(64, rect.top + moveEvent.clientY - startY) + 'px';
              };
              const stop = () => {
                doc.removeEventListener('pointermove', move);
                doc.removeEventListener('pointerup', stop);
              };
              doc.addEventListener('pointermove', move);
              doc.addEventListener('pointerup', stop);
              event.preventDefault();
            });
          }
        }
        </script>
        """,
        height=0,
        scrolling=False,
    )


def _map_search_overlay(
    communes: list[dict],
    facilities: list[dict],
) -> str:
    with st.container(key="risk-map-search"):
        st.markdown(
            _section_label("Explorer le territoire", "search"),
            unsafe_allow_html=True,
        )
        with st.form("risk_map_search_form", border=False):
            query_col, search_col = st.columns([4, 1], gap="small")
            query = query_col.text_input(
                "Rechercher",
                placeholder="Rechercher une commune, province ou établissement…",
                label_visibility="collapsed",
                key="risk_map_search",
            )
            submitted = search_col.form_submit_button(
                "⌕",
                help="Rechercher dans les données réelles",
                width="stretch",
            )
        recenter_col, status_col = st.columns([1, 2.6], gap="small")
        recenter_col.button(
            "⌖ Région TTA",
            key="risk_map_recenter",
            on_click=_recenter_map,
            width="stretch",
        )
        status = st.session_state.get("risk_search_status", "")
        status_col.caption(status or "146 communes · données OSM")

    if submitted:
        target, match = _search_target(query, communes, facilities)
        st.session_state["risk_search_active"] = query.strip()
        st.session_state["risk_search_target"] = target
        st.session_state["risk_search_match"] = match
        if target == "province" and match is not None:
            st.session_state["risk_province_filter"] = match
            st.session_state["risk_commune_filter"] = "Toutes les communes"
            st.session_state["risk_selected_commune_code"] = None
            st.session_state["risk_search_status"] = f"Province trouvée : {match}"
        elif target == "commune" and match is not None:
            commune = next(
                row
                for row in communes
                if str(row["commune_code"]) == str(match)
            )
            st.session_state["risk_province_filter"] = commune["province"]
            st.session_state["risk_commune_filter"] = (
                f"{commune['name_fr']} · {commune['commune_code']}"
            )
            st.session_state["risk_selected_commune_code"] = str(match)
            st.session_state["risk_search_status"] = "Commune trouvée"
        elif target == "facility":
            st.session_state["risk_province_filter"] = "Toutes les provinces"
            st.session_state["risk_commune_filter"] = "Toutes les communes"
            st.session_state["risk_selected_commune_code"] = None
            st.session_state["risk_search_status"] = "Établissements correspondants affichés"
        else:
            st.session_state["risk_province_filter"] = "Toutes les provinces"
            st.session_state["risk_commune_filter"] = "Toutes les communes"
            st.session_state["risk_selected_commune_code"] = None
            st.session_state["risk_search_status"] = "Aucun résultat dans les données disponibles"
    return st.session_state.get("risk_search_active", "")


def _render_facility_filters(facilities: list[dict]) -> None:
    counts = _facility_type_counts(facilities)
    st.markdown(
        _section_label("Établissements de santé", "healthcare"),
        unsafe_allow_html=True,
    )
    columns = st.columns(2, gap="small")
    for index, (group, (label, key)) in enumerate(FACILITY_GROUPS.items()):
        count = counts.get(group, 0)
        with columns[index % 2]:
            icon_col, checkbox_col = st.columns(
                [0.2, 0.8],
                gap="small",
                vertical_alignment="center",
            )
            icon_col.markdown(
                "<span class='tta-facility-filter-icon' "
                f"style='background:{RISK_FACILITY_COLORS[group]}'>"
                f"{facility_icon_svg(group, size=14)}</span>",
                unsafe_allow_html=True,
            )
            checkbox_col.checkbox(
                f"{label} · {count}",
                key=key,
                help=f"{count} enregistrement(s) selon les filtres géographiques.",
            )


SECTION_ICON_CONTENT = {
    "search": "<circle cx='11' cy='11' r='7'/><path d='m20 20-4-4'/>",
    "layers": "<path d='m12 3 9 5-9 5-9-5 9-5Z'/><path d='m3 12 9 5 9-5m-18 5 9 5 9-5'/>",
    "healthcare": "<path d='M12 5v14M5 12h14' stroke-width='2.2'/>",
    "map": "<path d='m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z'/><path d='M9 3v15m6-12v15'/>",
    "palette": "<path d='M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1.7-3.1 1.8 1.8 0 0 1 1.5-2.9H18a3 3 0 0 0 3-3c0-5-4-9-9-9Z'/><path d='M7.5 10h.01M10 7.5h.01M14 7.5h.01M16.5 10h.01'/>",
    "chart": "<path d='M4 19V9m5 10V5m5 14v-7m5 7H2'/>",
}


def _section_label(label: str, icon: str) -> str:
    icon_svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='15' height='15' "
        "viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        "stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round' "
        "aria-hidden='true'>"
        f"{SECTION_ICON_CONTENT[icon]}</svg>"
    )
    return (
        "<div class='tta-map-section-label'>"
        f"{icon_svg}{html.escape(label)}</div>"
    )


def _render_summary(
    communes: list[dict],
    associated: list[dict],
    unassigned: list[dict],
) -> None:
    st.markdown(
        _section_label("Synthèse régionale", "chart"),
        unsafe_allow_html=True,
    )
    metrics = [
        ("Communes", len(communes)),
        ("Total établissements", len(associated) + len(unassigned)),
        ("Associés", len(associated)),
        ("Non associés", len(unassigned)),
    ]
    columns = st.columns(2, gap="small")
    for index, (label, value) in enumerate(metrics):
        with columns[index % 2]:
            st.markdown(
                f"<div class='tta-map-kpi'><div class='tta-map-kpi-value'>"
                f"{value:,}</div><div class='tta-map-kpi-label'>"
                f"{html.escape(label)}</div></div>",
                unsafe_allow_html=True,
            )

    counts = _facility_type_counts(associated + unassigned)
    labels = [FACILITY_GROUPS[group][0] for group in FACILITY_GROUPS]
    values = [counts.get(group, 0) for group in FACILITY_GROUPS]
    colors = [RISK_FACILITY_COLORS[group] for group in FACILITY_GROUPS]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=values,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y} : %{x} établissements<extra></extra>",
        )
    )
    figure.update_layout(
        height=220,
        margin={"l": 8, "r": 30, "t": 8, "b": 10},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Inter, Segoe UI, sans-serif", "size": 9, "color": "#334155"},
        showlegend=False,
        xaxis={"visible": False, "fixedrange": True},
        yaxis={"autorange": "reversed", "fixedrange": True},
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False, "staticPlot": True},
    )

    st.markdown(
        _section_label("Établissements par catégorie", "healthcare"),
        unsafe_allow_html=True,
    )
    facility_legend = "".join(
        "<span class='tta-map-legend-chip'>"
        f"<span class='tta-facility-filter-icon' "
        f"style='background:{RISK_FACILITY_COLORS[group]}'>"
        f"{facility_icon_svg(group, size=12)}</span>{html.escape(label)}</span>"
        for group, (label, _) in FACILITY_GROUPS.items()
    )
    st.markdown(
        f"<div class='tta-map-legend-line'>{facility_legend}</div>",
        unsafe_allow_html=True,
    )

    swatches = "".join(
        "<span class='tta-map-legend-chip'>"
        f"<i class='tta-map-legend-swatch' style='background:{color}'></i>"
        f"{html.escape(label)}</span>"
        for label, color in RISK_MILIEU_COLORS.items()
    )
    st.markdown(
        _section_label("Milieu territorial", "map")
        + f"<div class='tta-map-legend-line'>{swatches}</div>"
        "<div class='tta-future-indicator'>Les indicateurs validés de risque "
        "et d’accessibilité ne sont pas encore intégrés.</div>",
        unsafe_allow_html=True,
    )


def render_interactive_risk_map(
    communes: list[dict],
    commune_geojson: dict,
    facilities: list[dict],
) -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] label p {
            font-size: 0.92rem !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    map_tabs = st.radio(
        "Sélectionnez la carte interactive :",
        [
            "🏥 Carte 1 : Sanitaire & Démographique (RSC-TTA)",
            "⚠️ Carte 2 : Risque & Vulnérabilité Territoriale",
            "🛣️ Carte 3 : Itinéraires vers les Hôpitaux",
            "🌐 Vue SIG Plein Écran (Historique)",
        ],
        horizontal=True,
        key="geovulnera_active_map_selector",
    )

    if map_tabs == "🏥 Carte 1 : Sanitaire & Démographique (RSC-TTA)":
        render_health_map(communes, commune_geojson, facilities)
        return
    elif map_tabs == "⚠️ Carte 2 : Risque & Vulnérabilité Territoriale":
        render_territorial_risk_map(communes, commune_geojson, facilities)
        return
    elif map_tabs == "🛣️ Carte 3 : Itinéraires vers les Hôpitaux":
        render_hospital_routes_map(communes, commune_geojson, facilities)
        return

    st.markdown(MAP_SCREEN_CSS, unsafe_allow_html=True)
    st.markdown("<div class='tta-map-screen'></div>", unsafe_allow_html=True)
    from components.header import page_header

    page_header(
        "Interactive Risk Map",
        f"Exploration des communes et établissements de santé — {REGION_NAME}.",
        compact=True,
    )


    defaults = {
        "risk_map_search": "",
        "risk_search_active": "",
        "risk_search_target": "",
        "risk_search_match": None,
        "risk_province_filter": "Toutes les provinces",
        "risk_commune_filter": "Toutes les communes",
        "risk_milieu_filter": "Tous",
        "risk_base_map": "Satellite Haute Résolution",
        "risk_thematic_mode": "Milieu territorial",
        "risk_bubble_metric": "Établissements associés",
        "risk_show_boundaries": True,
        "risk_show_facilities": True,
        "risk_show_unassigned": True,
        "risk_show_bubbles": False,
        "risk_show_heatmap": False,
        "risk_inspector_collapsed": False,
        "risk_inspector_visible": True,
        "risk_selected_commune_code": None,
        "risk_search_status": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    for _, key in FACILITY_GROUPS.values():
        st.session_state.setdefault(key, True)

    geojson_cache_key = _commune_geojson_cache_key()
    display_geojson = simplify_commune_geojson(
        commune_geojson,
        cache_key=geojson_cache_key,
    )
    areas_km2 = commune_areas_km2(
        commune_geojson,
        cache_key=geojson_cache_key,
    )
    active_search = _map_search_overlay(communes, facilities)
    provinces = sorted({str(row["province"]) for row in communes})
    if (
        st.session_state.get("risk_province_filter")
        not in ["Toutes les provinces", *provinces]
    ):
        st.session_state["risk_province_filter"] = "Toutes les provinces"

    commune_by_code = {
        str(row["commune_code"]).strip(): row for row in communes
    }
    selected_province = st.session_state["risk_province_filter"]
    province_rows = [
        row
        for row in communes
        if selected_province == "Toutes les provinces"
        or row["province"] == selected_province
    ]
    commune_options = {
        "Toutes les communes": None,
        **{
            f"{row['name_fr']} · {row['commune_code']}": str(row["commune_code"])
            for row in sorted(province_rows, key=lambda row: row["name_fr"])
        },
    }
    if st.session_state["risk_commune_filter"] not in commune_options:
        st.session_state["risk_commune_filter"] = "Toutes les communes"

    selected_code = (
        commune_options.get(st.session_state["risk_commune_filter"])
        or st.session_state.get("risk_selected_commune_code")
    )
    selected_commune = commune_by_code.get(str(selected_code)) if selected_code else None
    panel_title = (
        str(selected_commune.get("name_fr", "Commune"))
        if selected_commune
        else f"Région {REGION_NAME}"
    )

    if not st.session_state["risk_inspector_visible"]:
        with st.container(key="risk-map-open"):
            if st.button(
                "☰ Contrôles & Filtres",
                key="risk_map_open_inspector",
                width="stretch",
            ):
                st.session_state["risk_inspector_visible"] = True
                st.rerun()
    else:
        with st.container(key="risk-map-inspector"):
            title_col, minimize_col, close_col = st.columns(
                [5, 0.7, 0.7],
                gap="small",
                vertical_alignment="center",
            )
            title_col.markdown(
                f"<div class='tta-inspector-heading'>"
                f"{html.escape(panel_title)}"
                f"<div class='tta-inspector-subtitle'>Contrôles cartographiques"
                f"{' · ' + html.escape(str(selected_commune['province'])) if selected_commune else ''}"
                "</div></div>",
                unsafe_allow_html=True,
            )
            if minimize_col.button("—", key="risk_map_minimize", help="Réduire le panneau"):
                st.session_state["risk_inspector_collapsed"] = (
                    not st.session_state["risk_inspector_collapsed"]
                )
                st.rerun()
            if close_col.button("×", key="risk_map_close", help="Masquer le panneau"):
                st.session_state["risk_inspector_visible"] = False
                st.rerun()

            if st.session_state["risk_inspector_collapsed"]:
                if st.button(
                    "Ouvrir les filtres",
                    key="risk_map_expand_inspector",
                    width="stretch",
                ):
                    st.session_state["risk_inspector_collapsed"] = False
                    st.rerun()
            else:
                filter_tab, summary_tab = st.tabs(
                    ["Filtres & Couches", "Synthèse & Légende"]
                )
                with filter_tab:
                    st.markdown(
                        _section_label("Filtres géographiques", "layers"),
                        unsafe_allow_html=True,
                    )
                    province_col, milieu_col = st.columns(2, gap="small")
                    selected_province = province_col.selectbox(
                        "Province",
                        ["Toutes les provinces", *provinces],
                        key="risk_province_filter",
                    )
                    selected_milieu = milieu_col.selectbox(
                        "Milieu",
                        ["Tous", "Urbain", "Mixte", "Rural"],
                        key="risk_milieu_filter",
                    )
                    province_rows = [
                        row
                        for row in communes
                        if selected_province == "Toutes les provinces"
                        or row["province"] == selected_province
                    ]
                    commune_options = {
                        "Toutes les communes": None,
                        **{
                            f"{row['name_fr']} · {row['commune_code']}": str(
                                row["commune_code"]
                            )
                            for row in sorted(
                                province_rows,
                                key=lambda row: row["name_fr"],
                            )
                        },
                    }
                    if (
                        st.session_state["risk_commune_filter"]
                        not in commune_options
                    ):
                        st.session_state["risk_commune_filter"] = (
                            "Toutes les communes"
                        )
                    selected_option = st.selectbox(
                        "Commune",
                        list(commune_options),
                        key="risk_commune_filter",
                    )
                    selected_code = commune_options[selected_option]
                    selected_commune = (
                        commune_by_code.get(str(selected_code))
                        if selected_code
                        else None
                    )

                    geographic_communes = filter_map_communes(
                        communes,
                        provinces=(
                            []
                            if selected_province == "Toutes les provinces"
                            else [selected_province]
                        ),
                        milieux=[] if selected_milieu == "Tous" else [selected_milieu],
                        search="",
                    )
                    if selected_code:
                        geographic_communes = [
                            row
                            for row in geographic_communes
                            if str(row["commune_code"]) == str(selected_code)
                        ]
                    geographic_codes = {
                        str(row["commune_code"]).strip()
                        for row in geographic_communes
                    }
                    geographic_code_key = tuple(sorted(geographic_codes))
                    all_associated = _filter_facilities_by_scope(
                        facilities,
                        commune_codes=geographic_code_key,
                        assigned=True,
                    )
                    _render_facility_filters(all_associated)
                    selected_types = tuple(sorted(_facility_types_from_state()))
                    associated_filtered = _filter_facilities_by_scope(
                        facilities,
                        commune_codes=geographic_code_key,
                        facility_types=selected_types,
                        assigned=True,
                    )
                    unassigned_filtered = _filter_facilities_by_scope(
                        facilities,
                        facility_types=selected_types,
                        assigned=False,
                    )
                    if (
                        active_search
                        and st.session_state.get("risk_search_target") == "facility"
                    ):
                        matched_ids = {
                            (row.get("osm_type"), str(row.get("osm_id")))
                            for row in filter_facility_search(facilities, active_search)
                        }
                        associated_filtered = [
                            row
                            for row in associated_filtered
                            if (row.get("osm_type"), str(row.get("osm_id"))) in matched_ids
                        ]
                        unassigned_filtered = [
                            row
                            for row in unassigned_filtered
                            if (row.get("osm_type"), str(row.get("osm_id"))) in matched_ids
                        ]

                    st.markdown(
                        _section_label("Couches cartographiques", "map"),
                        unsafe_allow_html=True,
                    )
                    layer_col_a, layer_col_b = st.columns(2, gap="small")
                    with layer_col_a:
                        st.checkbox(
                            "Frontières communes",
                            key="risk_show_boundaries",
                        )
                        st.checkbox(
                            "Marqueurs établissements",
                            key="risk_show_facilities",
                        )
                        st.checkbox(
                            f"Établissements non associés · {len(unassigned_filtered)}",
                            key="risk_show_unassigned",
                        )
                    with layer_col_b:
                        st.checkbox(
                            "Bulles proportionnelles",
                            key="risk_show_bubbles",
                        )
                        st.checkbox(
                            "Carte de chaleur",
                            key="risk_show_heatmap",
                        )
                    st.markdown(
                        _section_label("Apparence de la carte", "palette"),
                        unsafe_allow_html=True,
                    )
                    st.selectbox(
                        "Taille des bulles",
                        ["Établissements associés", "Population 2024"],
                        key="risk_bubble_metric",
                        disabled=not st.session_state["risk_show_bubbles"],
                    )
                    st.selectbox(
                        "Fond de carte",
                        list(BASE_MAP_CHOICES),
                        key="risk_base_map",
                    )
                    st.selectbox(
                        "Coloration des communes",
                        list(THEMATIC_CHOICES),
                        key="risk_thematic_mode",
                    )
                    st.checkbox(
                        "Accessibilité aux soins · données futures",
                        disabled=True,
                        key="risk_future_accessibility",
                    )
                    st.checkbox(
                        "Niveau de risque · données validées futures",
                        disabled=True,
                        key="risk_future_risk",
                    )
                    st.markdown(
                        "<div class='tta-future-indicator'>Les couches "
                        "d’accessibilité et de risque restent désactivées tant que "
                        "les indicateurs validés ne sont pas intégrés.</div>",
                        unsafe_allow_html=True,
                    )
                    st.button(
                        "Réinitialiser les filtres",
                        key="risk_map_reset",
                        on_click=_reset_map_filters,
                        width="stretch",
                    )

                with summary_tab:
                    # The summary uses the same geographic and type filters as the map.
                    current_province = st.session_state["risk_province_filter"]
                    current_milieu = st.session_state["risk_milieu_filter"]
                    current_commune_label = st.session_state["risk_commune_filter"]
                    current_commune_code = commune_options.get(current_commune_label)
                    summary_communes = filter_map_communes(
                        communes,
                        provinces=(
                            []
                            if current_province == "Toutes les provinces"
                            else [current_province]
                        ),
                        milieux=[] if current_milieu == "Tous" else [current_milieu],
                        search="",
                    )
                    if current_commune_code:
                        summary_communes = [
                            row
                            for row in summary_communes
                            if str(row["commune_code"]) == str(current_commune_code)
                        ]
                    summary_codes = {
                        str(row["commune_code"]).strip()
                        for row in summary_communes
                    }
                    summary_types = tuple(sorted(_facility_types_from_state()))
                    summary_code_key = tuple(sorted(summary_codes))
                    summary_associated = _filter_facilities_by_scope(
                        facilities,
                        commune_codes=summary_code_key,
                        facility_types=summary_types,
                        assigned=True,
                    )
                    summary_unassigned = _filter_facilities_by_scope(
                        facilities,
                        facility_types=summary_types,
                        assigned=False,
                    )
                    if (
                        active_search
                        and st.session_state.get("risk_search_target") == "facility"
                    ):
                        matched_ids = {
                            (row.get("osm_type"), str(row.get("osm_id")))
                            for row in filter_facility_search(facilities, active_search)
                        }
                        summary_associated = [
                            row for row in summary_associated
                            if (row.get("osm_type"), str(row.get("osm_id"))) in matched_ids
                        ]
                        summary_unassigned = [
                            row for row in summary_unassigned
                            if (row.get("osm_type"), str(row.get("osm_id"))) in matched_ids
                        ]
                    _render_summary(
                        summary_communes,
                        summary_associated,
                        summary_unassigned,
                    )

    selected_province = st.session_state.get(
        "risk_province_filter",
        "Toutes les provinces",
    )
    selected_milieu = st.session_state.get("risk_milieu_filter", "Tous")
    selected_commune_label = st.session_state.get(
        "risk_commune_filter",
        "Toutes les communes",
    )
    province_rows = [
        row
        for row in communes
        if selected_province == "Toutes les provinces"
        or row["province"] == selected_province
    ]
    commune_code_by_label = {
        f"{row['name_fr']} · {row['commune_code']}": str(row["commune_code"])
        for row in province_rows
    }
    selected_filter_code = commune_code_by_label.get(selected_commune_label)
    selected_code = selected_filter_code or st.session_state.get(
        "risk_selected_commune_code"
    )
    selected_commune = commune_by_code.get(str(selected_code)) if selected_code else None

    filtered_communes = filter_map_communes(
        communes,
        provinces=(
            []
            if selected_province == "Toutes les provinces"
            else [selected_province]
        ),
        milieux=[] if selected_milieu == "Tous" else [selected_milieu],
        search="",
    )
    if active_search and st.session_state.get("risk_search_target") == "none":
        filtered_communes = []
    if selected_filter_code:
        filtered_communes = [
            row
            for row in filtered_communes
            if str(row["commune_code"]) == selected_filter_code
        ]
    filtered_codes = {
        str(row["commune_code"]).strip() for row in filtered_communes
    }
    if selected_code and str(selected_code) not in filtered_codes:
        selected_code = None
        st.session_state["risk_selected_commune_code"] = None
    filtered_geojson = {
        "type": "FeatureCollection",
        "features": [
            feature
            for feature in display_geojson["features"]
            if str(feature["properties"]["commune_code"]).strip() in filtered_codes
        ],
    }

    selected_types = set(_facility_types_from_state())
    filtered_code_key = tuple(sorted(filtered_codes))
    selected_type_key = tuple(sorted(selected_types))
    associated_all = _filter_facilities_by_scope(
        facilities,
        commune_codes=filtered_code_key,
        assigned=True,
    )
    visible_associated = _filter_facilities_by_scope(
        facilities,
        commune_codes=filtered_code_key,
        facility_types=selected_type_key,
        assigned=True,
    )
    unassigned_all = _filter_facilities_by_scope(facilities, assigned=False)
    visible_unassigned = _filter_facilities_by_scope(
        facilities,
        facility_types=selected_type_key,
        assigned=False,
    )
    if (
        active_search
        and st.session_state.get("risk_search_target") == "facility"
    ):
        matched_ids = {
            (row.get("osm_type"), str(row.get("osm_id")))
            for row in filter_facility_search(facilities, active_search)
        }
        visible_associated = [
            row for row in visible_associated
            if (row.get("osm_type"), str(row.get("osm_id"))) in matched_ids
        ]
        visible_unassigned = [
            row for row in visible_unassigned
            if (row.get("osm_type"), str(row.get("osm_id"))) in matched_ids
        ]

    selected_mode = THEMATIC_CHOICES.get(
        st.session_state.get("risk_thematic_mode", "Milieu territorial"),
        "environment",
    )
    color_values = commune_color_values(
        filtered_communes,
        selected_mode,
        facilities=visible_associated,
        areas_km2=areas_km2,
    )
    mode_values = (
        numeric_color_range(color_values)
        if selected_mode in NUMERIC_MAP_MODES
        else None
    )
    initial_map_key = BASE_MAP_CHOICES.get(
        st.session_state.get("risk_base_map", "Satellite Haute Résolution"),
        "satellite",
    )
    folium_map = get_initial_map(base_map=initial_map_key, add_tile_layers=True)
    from branca.element import Element

    folium_map.get_root().header.add_child(
        Element(
            "<style>"
            "html,body{width:100%!important;height:100%!important;margin:0!important;"
            "padding:0!important;overflow:hidden!important;}"
            "#map_div,.folium-map,.leaflet-container{width:100%!important;"
            "height:100vh!important;min-height:350px!important;background:#EAF1F3!important;}"
            ".leaflet-tile{opacity:1!important;}"
            "</style>"
        ),
        name="risk-map-fullscreen-style",
    )
    commune_layer = build_commune_layer(
        filtered_communes,
        filtered_geojson,
        folium_map,
        facilities=associated_all,
        color_mode=selected_mode,
        color_values=color_values,
        selected_code=str(selected_code) if selected_code else None,
        milieu_colors=RISK_MILIEU_COLORS,
        show=st.session_state["risk_show_boundaries"],
    )
    commune_layer.layer_name = "Frontières communales"
    facility_layer = build_facility_layer(
        visible_associated,
        folium_map,
        color_by_type=True,
        cluster=True,
        symbol_markers=True,
        commune_lookup=commune_by_code,
        show=st.session_state["risk_show_facilities"],
    )
    unassigned_layer = build_unassigned_facility_layer(
        visible_unassigned,
        folium_map,
        symbol_markers=True,
        show=st.session_state["risk_show_unassigned"],
    )
    bubble_metric = (
        "population"
        if st.session_state["risk_bubble_metric"] == "Population 2024"
        else "facilities"
    )
    bubble_layer = build_proportional_bubble_layer(
        filtered_communes,
        visible_associated,
        folium_map,
        metric=bubble_metric,
        show=st.session_state["risk_show_bubbles"],
    )
    heatmap_rows = visible_associated + (
        visible_unassigned if st.session_state["risk_show_unassigned"] else []
    )
    heatmap_layer = build_heatmap_layer(
        heatmap_rows,
        folium_map,
        show=st.session_state["risk_show_heatmap"],
    )
    bounds = (
        geojson_bounds(filtered_geojson)
        if filtered_geojson["features"]
        else geojson_bounds(commune_geojson)
    )

    selected_features = [
        feature
        for feature in filtered_geojson["features"]
        if selected_code
        and str(feature["properties"].get("commune_code")) == str(selected_code)
    ]
    focus_bounds = (
        geojson_bounds(
            {"type": "FeatureCollection", "features": selected_features}
        )
        if selected_features
        else bounds
    )
    folium_map.fit_bounds(
        focus_bounds,
        padding=(24, 24),
        max_zoom=13 if selected_features else 10,
    )

    add_enterprise_map_controls(
        folium_map,
        {
            "communes": commune_layer,
            "facilities": facility_layer,
            "unassigned": unassigned_layer,
            "bubbles": bubble_layer,
            "heatmap": heatmap_layer,
        },
        folium_map._tta_base_layers,
        bounds,
        facility_count=len(visible_associated) + len(visible_unassigned),
        unassigned_count=len(visible_unassigned),
    )
    folium.LayerControl(position="topright", collapsed=True).add_to(folium_map)

    with st.container(key="risk-map-canvas"):
        render_map(
            folium_map,
            height=850,
            key="risk-map-view",
            returned_objects=[],
        )
    _drag_panel_script()
