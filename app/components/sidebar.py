"""Primary navigation and current territory status."""

from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

import streamlit as st
from config.settings import APP_VERSION, REGION_NAME
from data_loader import COMMUNES_CSV, COMMUNES_GEOJSON, FACILITIES_CSV

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "geovulnera_tta_logo.png"

DASHBOARDS = [
    ("Overview Dashboard", "Vue d'ensemble"),
    ("Interactive Risk Map", "Carte des Risques"),
    ("Commune Ranking", "Classement Communes"),
    ("Commune Details", "Détails Commune"),
    ("Trends & Historical Analysis", "Tendances Historiques"),
    ("Alerts & Priority Areas", "Alertes & Priorités"),
    ("System Monitoring", "Monitoring Système"),
]

NAVIGATION_ICON_CONTENT = {
    "Overview Dashboard": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7h-4v7H4a1 1 0 0 1-1-1z"/>',
    "Interactive Risk Map": '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15m6-12v15"/>',
    "Commune Ranking": '<path d="M4 19V9m6 10V5m6 14v-7m6 7H2"/>',
    "Commune Details": '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    "Trends & Historical Analysis": '<path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/>',
    "Alerts & Priority Areas": '<path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/>',
    "System Monitoring": '<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.7 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.7-1l-1.7.7-1.4-2.4 1.4-1.1a8 8 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.7-1l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.7 1l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1 0 2Z"/>',
}

NAVIGATION_ICON_SVGS = {
    key: (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        "stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round' "
        f"aria-hidden='true'>{content}</svg>"
    )
    for key, content in NAVIGATION_ICON_CONTENT.items()
}


def _navigation_icon_label(dashboard: str) -> str:
    svg = NAVIGATION_ICON_SVGS[dashboard].replace("currentColor", "#64748B")
    encoded_svg = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    title = next(label for key, label in DASHBOARDS if key == dashboard)
    return f"![{html.escape(title)}](data:image/svg+xml;base64,{encoded_svg})"


NAVIGATION_ICONS = {dashboard: _navigation_icon_label(dashboard) for dashboard, _ in DASHBOARDS}


def render_sidebar() -> str:
    labels = [f"{NAVIGATION_ICONS[key]}  {label}" for key, label in DASHBOARDS]
    requested_page = st.session_state.pop("pending_navigation_page", None)
    if requested_page in {dashboard for dashboard, _ in DASHBOARDS}:
        requested_index = next(
            index for index, (dashboard, _) in enumerate(DASHBOARDS) if dashboard == requested_page
        )
        st.session_state["sidebar_navigation_radio"] = labels[requested_index]
    current_page = st.session_state.get("selected_page", "Overview Dashboard")
    default_index = next(
        (index for index, (dashboard, _) in enumerate(DASHBOARDS) if dashboard == current_page),
        0,
    )
    with st.sidebar.container(key="tta-sidebar-brand"):
        st.image(str(LOGO_PATH), width=185)
    st.sidebar.markdown("<div class='tta-sidebar-divider'></div>", unsafe_allow_html=True)
    selected_label = st.sidebar.radio(
        "Navigation",
        labels,
        index=(None if "sidebar_navigation_radio" in st.session_state else default_index),
        label_visibility="collapsed",
        key="sidebar_navigation_radio",
    )
    if selected_label not in labels:
        selected_label = labels[default_index]
    selected_page = DASHBOARDS[labels.index(selected_label)][0]
    st.session_state["selected_page"] = selected_page

    map_province = st.session_state.get("map_province_select", "All Provinces")
    territory = st.session_state.get("overview_territory", "Région TTA")
    if map_province != "All Provinces":
        territory = map_province
    territory_label = REGION_NAME if territory == "Région TTA" else territory

    source_files = (COMMUNES_CSV, COMMUNES_GEOJSON, FACILITIES_CSV)
    timestamps = [path.stat().st_mtime for path in source_files if path.is_file()]
    last_updated = (
        datetime.fromtimestamp(max(timestamps)).strftime("%d/%m/%Y · %H:%M")
        if timestamps
        else "Non disponible"
    )
    sources_available = all(path.is_file() for path in source_files)
    source_status = (
        "Système opérationnel" if sources_available else "Sources de données incomplètes"
    )
    st.sidebar.markdown(
        f"""
        <div class='tta-sidebar-territory-card'>
            <div class='tta-sidebar-card-label'>Territoire sélectionné</div>
            <div class='tta-sidebar-card-select'>
                <span>{html.escape(str(territory_label))}</span>
            </div>
            <div class='tta-sidebar-card-label' style='margin-top:10px;'>
                Dernière mise à jour des données
            </div>
            <div class='tta-sidebar-card-date'>{html.escape(last_updated)}</div>
            <div class='tta-sidebar-status-pill'>
                <span class='tta-status-dot'></span>
                {html.escape(source_status)}
            </div>
        </div>
        <div class='tta-sidebar-bottom-footer'>
            <span class='tta-settings-icon' aria-hidden='true'>
                {NAVIGATION_ICON_SVGS["System Monitoring"]}
            </span>
            <span class='tta-version-text'>v{html.escape(APP_VERSION)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return selected_page
