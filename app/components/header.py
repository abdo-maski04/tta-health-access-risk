"""Shared application header and page title."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st
from config.settings import REGION_NAME

from components.sidebar import DASHBOARDS, NAVIGATION_ICON_SVGS

HEADER_ICONS = {
    **NAVIGATION_ICON_SVGS,
}

HEADER_TITLES = {
    "Overview Dashboard": "Vue d’ensemble",
    "Interactive Risk Map": "Carte des risques",
    "Commune Ranking": "Classement communal",
    "Commune Details": "Détail communal",
    "Trends & Historical Analysis": "Tendances historiques",
    "Alerts & Priority Areas": "Alertes et priorités",
    "System Monitoring": "Monitoring système",
}

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "geovulnera_tta_logo.png"


def _global_header(title: str) -> None:
    with st.container(key="tta-global-header"):
        menu_col, logo_col, region_col, page_col = st.columns(
            [0.55, 1.3, 1.1, 1.1],
            vertical_alignment="center",
        )
        with menu_col:
            with st.popover("☰ Menu", help="Ouvrir le menu de navigation"):
                st.markdown("### 📋 Navigation")
                current_page = st.session_state.get("selected_page", "Overview Dashboard")
                for key, label in DASHBOARDS:
                    is_current = current_page == key
                    btn_text = f"● {label}" if is_current else label
                    if st.button(
                        btn_text,
                        key=f"hdr_nav_{key}",
                        type="primary" if is_current else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["pending_navigation_page"] = key
                        st.session_state["selected_page"] = key
                        st.rerun()
                st.divider()
                st.markdown(
                    """
                    <button onclick="
                        const doc = window.parent.document;
                        const btn = doc.querySelector('[data-testid=\\'stSidebarCollapseButton\\'] button, [data-testid=\\'stExpandSidebarButton\\'] button, button[aria-label*=\\'sidebar\\' i]');
                        if (btn) btn.click();
                    " style="
                        width: 100%;
                        padding: 7px 10px;
                        background: #0D5C75;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        font-weight: 600;
                        cursor: pointer;
                        font-size: 12px;
                    ">⮂ Volet latéral</button>
                    """,
                    unsafe_allow_html=True,
                )
        logo_col.image(str(LOGO_PATH), width="stretch")
        territory = st.session_state.get("overview_territory", "Région TTA")
        risk_province = st.session_state.get(
            "risk_province_filter",
            "Toutes les provinces",
        )
        if risk_province != "Toutes les provinces":
            territory = risk_province
        if territory == "Région TTA":
            territory = REGION_NAME
        region_col.markdown(
            f"<div class='tta-global-header-region'>{html.escape(str(territory))}</div>",
            unsafe_allow_html=True,
        )
        page_col.markdown(
            f"<div class='tta-global-header-page'>{html.escape(title)}</div>",
            unsafe_allow_html=True,
        )


def page_header(
    title: str,
    description: str,
    update_label: str | None = None,
    *,
    include_topbar: bool = True,
    compact: bool = False,
) -> None:
    icon = HEADER_ICONS.get(title, HEADER_ICONS["Overview Dashboard"])
    display_title = HEADER_TITLES.get(title, title)
    if include_topbar:
        _global_header(display_title)
    if compact:
        return

    update = ""
    if update_label:
        update = (
            "<div class='tta-header-update'>"
            f"Dernière actualisation : {html.escape(update_label)}"
            "</div>"
        )
    st.markdown(
        "<div class='tta-header'>"
        + f"<div class='tta-header-icon' aria-hidden='true'>{icon}</div>"
        + "<div class='tta-header-content'>"
        + f"<h1>{html.escape(display_title)}</h1>"
        + f"<p>{html.escape(description)}</p>"
        + f"{update}</div></div>",
        unsafe_allow_html=True,
    )
