import json
import sys
from pathlib import Path

import streamlit as st

CONFIG_DIR = Path(__file__).resolve().parent / "config"
COMPONENT_DIR = Path(__file__).resolve().parent / "components"
if str(CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_DIR))
if str(COMPONENT_DIR) not in sys.path:
    sys.path.insert(0, str(COMPONENT_DIR))

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from components.header import page_header  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402
from components.states import unavailable_state  # noqa: E402
from config.settings import APP_TITLE  # noqa: E402
from config.theme import APP_CSS  # noqa: E402
from pages.analytics import (  # noqa: E402
    render_alerts,
    render_commune_details,
    render_commune_ranking,
    render_monitoring,
    render_trends,
)
from pages.overview import render_overview  # noqa: E402
from pages.risk_map import render_interactive_risk_map  # noqa: E402

try:
    from data_loader import get_prepared_data  # noqa: E402
except ImportError:
    import importlib

    import data_loader

    importlib.reload(data_loader)
    from data_loader import get_prepared_data  # noqa: E402

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

selected_page = render_sidebar()
page_root = st.empty()
with page_root.container():
    if selected_page == "Overview Dashboard":
        try:
            communes, commune_geojson, facilities = get_prepared_data()
            provinces = sorted({row["province"] for row in communes})
            render_overview(communes, commune_geojson, facilities, provinces)
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
            st.error(f"Impossible de charger les données Overview: {exc}")
    elif selected_page == "Interactive Risk Map":
        try:
            try:
                from data_loader import get_sanitary_prepared_data

                communes, commune_geojson, facilities = get_sanitary_prepared_data()
            except Exception:
                communes, commune_geojson, facilities = get_prepared_data()
            render_interactive_risk_map(communes, commune_geojson, facilities)
        except (
            FileNotFoundError,
            KeyError,
            RuntimeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            st.error(f"Impossible de charger la carte interactive: {exc}")
    elif selected_page in {
        "Commune Ranking",
        "Commune Details",
        "Trends & Historical Analysis",
        "Alerts & Priority Areas",
        "System Monitoring",
    }:
        try:
            communes, commune_geojson, facilities = get_prepared_data()
            if selected_page == "Commune Ranking":
                render_commune_ranking(communes, facilities)
            elif selected_page == "Commune Details":
                render_commune_details(communes, commune_geojson, facilities)
            elif selected_page == "Trends & Historical Analysis":
                render_trends(communes, facilities)
            elif selected_page == "Alerts & Priority Areas":
                render_alerts(communes, facilities)
            else:
                render_monitoring(communes, facilities)
        except (
            FileNotFoundError,
            KeyError,
            RuntimeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            st.error(f"Impossible de charger le dashboard {selected_page}: {exc}")
    else:
        descriptions = {
            "Commune Ranking": "Classements démographiques et comparaisons communales.",
            "Commune Details": "Profil détaillé d'une commune.",
            "Trends & Historical Analysis": "Historique des indicateurs validés.",
            "Alerts & Priority Areas": "Alertes et zones prioritaires validées.",
            "System Monitoring": "État opérationnel des sources et pipelines.",
        }
        page_header(selected_page, descriptions[selected_page])
        unavailable_state(
            "Page en préparation",
            "Cette phase du Sprint 2 n'est pas encore implémentée.",
        )
