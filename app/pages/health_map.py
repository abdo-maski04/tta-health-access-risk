"""Carte Sanitaire et Démographique — Référentiel Sanitaire Consolidé (RSC-TTA).

Architecture SIG Pro en Split-Screen 3 colonnes :
- Colonne 1 (~24%) : Contrôles & Couches SIG
- Colonne 2 (~51%) : Carte Interactive Pleine Hauteur (680px)
- Colonne 3 (~25%) : Fiche Territoriale Sanitaire
"""

from __future__ import annotations

import html
from typing import Any

import folium
import streamlit as st
from folium.plugins import Fullscreen, MarkerCluster

try:
    from map_utils import get_facility_div_icon, render_map
except ImportError:
    from app.map_utils import get_facility_div_icon, render_map

# ---------------------------------------------------------------------------
# Index spatial préparé pour identification ultra-rapide par coordonnées (< 0.5 ms)
# ---------------------------------------------------------------------------

_COMMUNE_SHAPES_CACHE: list[tuple[str, Any]] | None = None


def _get_commune_prepared_shapes(geojson: dict) -> list[tuple[str, Any]]:
    """Index spatial en mémoire des 146 polygones communaux."""
    global _COMMUNE_SHAPES_CACHE
    if _COMMUNE_SHAPES_CACHE is None:
        from shapely.geometry import shape
        from shapely.prepared import prep

        shapes = []
        for f in geojson.get("features", []):
            code = str(f.get("properties", {}).get("commune_code", "")).strip()
            geom = f.get("geometry")
            if code and geom:
                try:
                    s = shape(geom)
                    shapes.append((code, prep(s)))
                except Exception:
                    continue
        _COMMUNE_SHAPES_CACHE = shapes
    return _COMMUNE_SHAPES_CACHE


def find_commune_at_lat_lon(lat: float, lon: float, geojson: dict) -> str | None:
    """Localise le commune_code contenant les coordonnées (lat, lon), ou None si hors polygone."""
    from shapely.geometry import Point

    pt = Point(lon, lat)
    shapes = _get_commune_prepared_shapes(geojson)
    for code, prep_shape in shapes:
        if prep_shape.contains(pt):
            return code
    return None


# ---------------------------------------------------------------------------
# Configuration des Fonds de Carte Publics 100% Gratuits (Zéro Watermark)
# ---------------------------------------------------------------------------

BASEMAP_TILES = {
    "Clair Professionnel": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    "Satellite": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles &copy; Esri",
        "subdomains": "abc",
        "max_zoom": 19,
    },
    "Sombre": {
        "tiles": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    "Relief": {
        "tiles": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attr": "&copy; OpenTopoMap",
        "subdomains": "abc",
        "max_zoom": 19,
    },
}

# ---------------------------------------------------------------------------
# Définitions des Thématiques Communales, Bins et Couleurs
# ---------------------------------------------------------------------------

THEMATIC_CHOICES = [
    "Milieu territorial",
    "Population",
    "Densité",
    "Équipements publics",
]


def _get_commune_choropleth_color(row: dict | None, thematic: str) -> str:
    """Détermine la couleur exacte d'une commune selon la thématique active."""
    if not row:
        return "#CBD5E1"

    if thematic == "Milieu territorial":
        milieu = str(row.get("milieu", "Rural")).strip().capitalize()
        if milieu == "Urbain":
            return "#0D5C75"  # Deep Petrol Teal
        elif milieu == "Mixte":
            return "#2A9D8F"  # Emerald / Seafoam Green
        return "#E9C46A"  # Warm Sand / Ochre Amber

    elif thematic == "Population":
        val = row.get("population_2024", 0) or 0
        if val >= 150000:
            return "#0C4A6E"
        elif val >= 50000:
            return "#0284C7"
        elif val >= 25000:
            return "#38BDF8"
        elif val >= 10000:
            return "#BAE6FD"
        return "#F0F9FF"

    elif thematic == "Densité":
        val = row.get("densite_hab_km2", 0.0) or 0.0
        if val >= 1000.0:
            return "#831843"
        elif val >= 250.0:
            return "#BE185D"
        elif val >= 100.0:
            return "#F472B6"
        elif val >= 50.0:
            return "#FBCFE8"
        return "#FDF2F8"

    elif thematic == "Équipements publics":
        val = (row.get("pub_primary_total", 0) or 0) + (row.get("pub_hospitals", 0) or 0)
        if val >= 5:
            return "#064E3B"
        elif val >= 3:
            return "#059669"
        elif val >= 2:
            return "#34D399"
        elif val >= 1:
            return "#A7F3D0"
        return "#FEE2E2"

    return "#CBD5E1"


def render_health_map(
    communes: list[dict],
    commune_geojson: dict,
    facilities: list[dict],
) -> None:
    """Rendu de la Carte 1 : Espace de Travail SIG 3-Colonnes Split-Screen."""

    # -----------------------------------------------------------------------
    # 0. Initialisation des États de Session
    # -----------------------------------------------------------------------
    st.session_state.setdefault("health_map_selected_commune_code", None)
    st.session_state.setdefault("hm_province_select", "Toutes les provinces")
    st.session_state.setdefault("hm_commune_select", "Aucune commune sélectionnée")
    st.session_state.setdefault("hm_thematic_select", "Milieu territorial")
    st.session_state.setdefault("hm_basemap_select", "Clair Professionnel")
    st.session_state.setdefault("hm_show_hosp", True)
    st.session_state.setdefault("hm_show_essp", False)
    st.session_state.setdefault("hm_show_pharm", True)
    st.session_state.setdefault("hm_show_clinics", True)

    # Injecter les styles CSS pour les conteneurs de cartes et boutons
    st.markdown(
        """
        <style>
        .sig-card-container {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
            height: 680px;
            overflow-y: auto;
            box-sizing: border-box;
        }
        .sig-card-title {
            font-size: 16px;
            font-weight: 750;
            color: #0F172A;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .st-key-hm_btn_reset button {
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            color: #334155 !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            width: 100% !important;
            padding: 8px 12px !important;
            margin-top: 8px !important;
            transition: all 0.15s ease-in-out !important;
        }
        .st-key-hm_btn_reset button:hover {
            background: #F8FAFC !important;
            border-color: #94A3B8 !important;
            color: #0F172A !important;
        }
        .st-key-hm_cta_details button {
            background: #0D5C75 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            width: 100% !important;
            padding: 10px 14px !important;
            margin-top: 14px !important;
            box-shadow: 0 2px 6px rgba(13, 92, 117, 0.25) !important;
            transition: all 0.15s ease-in-out !important;
        }
        .st-key-hm_cta_details button:hover {
            background: #0A475A !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 10px rgba(13, 92, 117, 0.35) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Récupérer la sélection active
    active_code: str | None = st.session_state["health_map_selected_commune_code"]

    # Liste des provinces réelles
    provinces_list = sorted({str(c.get("province")) for c in communes if c.get("province")})
    province_options = ["Toutes les provinces"] + provinces_list

    # -----------------------------------------------------------------------
    # Espace de Travail SIG 3-Colonnes Split-Screen (680px)
    # -----------------------------------------------------------------------
    col_controls, col_map, col_fiche = st.columns([1.05, 2.25, 1.15])

    # =======================================================================
    # COLONNE 1 (~24%) — Contrôles & Couches SIG
    # =======================================================================
    with col_controls:
        st.markdown('<div class="sig-card-container">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="sig-card-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0D5C75" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                    <circle cx="12" cy="12" r="3"/>
                </svg>
                Contrôles & Couches SIG
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 1. Dropdown Province
        selected_province = st.selectbox(
            "Province :",
            province_options,
            index=province_options.index(st.session_state["hm_province_select"])
            if st.session_state["hm_province_select"] in province_options
            else 0,
            key="hm_province_select",
        )

        # Communes filtrées selon la province choisie
        if selected_province != "Toutes les provinces":
            filtered_communes_prov = [c for c in communes if str(c.get("province")) == selected_province]
        else:
            filtered_communes_prov = communes

        # 2. Dropdown Commune (synchronisé dynamiquement avec la sélection)
        commune_name_to_code = {
            str(c.get("name_fr", "")): str(c.get("commune_code", ""))
            for c in filtered_communes_prov
            if c.get("name_fr")
        }
        commune_names_sorted = ["Aucune commune sélectionnée"] + sorted(commune_name_to_code.keys())

        # Trouver l'index de la commune active
        active_commune_name = "Aucune commune sélectionnée"
        if active_code:
            match_comm = next((c for c in communes if str(c.get("commune_code")) == active_code), None)
            if match_comm and match_comm.get("name_fr") in commune_name_to_code:
                active_commune_name = str(match_comm.get("name_fr"))

        selected_commune_name = st.selectbox(
            "Commune :",
            commune_names_sorted,
            index=commune_names_sorted.index(active_commune_name)
            if active_commune_name in commune_names_sorted
            else 0,
            key="hm_commune_select",
        )

        # Mettre à jour la sélection si le dropdown a changé manuellement
        if selected_commune_name != active_commune_name:
            if selected_commune_name == "Aucune commune sélectionnée":
                st.session_state["health_map_selected_commune_code"] = None
            else:
                st.session_state["health_map_selected_commune_code"] = commune_name_to_code.get(selected_commune_name)
            st.rerun()

        # 3. Dropdown Thématique
        selected_thematic = st.selectbox(
            "Thématique :",
            THEMATIC_CHOICES,
            index=THEMATIC_CHOICES.index(st.session_state["hm_thematic_select"])
            if st.session_state["hm_thematic_select"] in THEMATIC_CHOICES
            else 0,
            key="hm_thematic_select",
        )

        # 4. Dropdown Fond de Carte
        basemap_names = list(BASEMAP_TILES.keys())
        selected_basemap = st.selectbox(
            "Fond de carte :",
            basemap_names,
            index=basemap_names.index(st.session_state["hm_basemap_select"])
            if st.session_state["hm_basemap_select"] in basemap_names
            else 0,
            key="hm_basemap_select",
        )

        st.markdown(
            """
            <div style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin: 12px 0 6px;">
                Couches d'Équipements
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Toggles Verticaux avec badges SVG colorés
        show_hosp = st.checkbox("🔴 Hôpitaux Publics (16)", value=st.session_state["hm_show_hosp"], key="hm_show_hosp")
        show_essp = st.checkbox("🔷 Soins Primaires ESSP", value=st.session_state["hm_show_essp"], key="hm_show_essp")
        show_pharm = st.checkbox("🟢 Pharmacies Validées (722)", value=st.session_state["hm_show_pharm"], key="hm_show_pharm")
        show_clinics = st.checkbox("🟣 Cliniques & Spécialisés", value=st.session_state["hm_show_clinics"], key="hm_show_clinics")

        # Légende Thématique Compacte
        if selected_thematic == "Milieu territorial":
            st.markdown(
                """
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; margin: 12px 0 8px;">
                    <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 6px;">
                        Légende Thématique
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; color: #0F172A;">
                            <span style="width: 12px; height: 12px; border-radius: 3px; background: #0D5C75; display: inline-block;"></span> Urbain
                        </div>
                        <div style="display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; color: #0F172A;">
                            <span style="width: 12px; height: 12px; border-radius: 3px; background: #2A9D8F; display: inline-block;"></span> Mixte
                        </div>
                        <div style="display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; color: #0F172A;">
                            <span style="width: 12px; height: 12px; border-radius: 3px; background: #E9C46A; display: inline-block;"></span> Rural
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif selected_thematic == "Population":
            st.markdown(
                """
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; margin: 12px 0 8px;">
                    <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 6px;">
                        Population (RGPH 2024)
                    </div>
                    <div style="display: flex; gap: 4px; align-items: center; font-size: 10px; color: #475569;">
                        <span style="width: 12px; height: 10px; background: #F0F9FF; border: 1px solid #CBD5E1;"></span> &lt;10k
                        <span style="width: 12px; height: 10px; background: #38BDF8;"></span> 25-50k
                        <span style="width: 12px; height: 10px; background: #0C4A6E;"></span> &ge;150k
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif selected_thematic == "Densité":
            st.markdown(
                """
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; margin: 12px 0 8px;">
                    <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 6px;">
                        Densité (hab/km²)
                    </div>
                    <div style="display: flex; gap: 4px; align-items: center; font-size: 10px; color: #475569;">
                        <span style="width: 12px; height: 10px; background: #FDF2F8; border: 1px solid #CBD5E1;"></span> &lt;50
                        <span style="width: 12px; height: 10px; background: #F472B6;"></span> 100-250
                        <span style="width: 12px; height: 10px; background: #831843;"></span> &ge;1 000
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; margin: 12px 0 8px;">
                    <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 6px;">
                        Équipements Publics
                    </div>
                    <div style="display: flex; gap: 4px; align-items: center; font-size: 10px; color: #475569;">
                        <span style="width: 12px; height: 10px; background: #FEE2E2; border: 1px solid #CBD5E1;"></span> 0
                        <span style="width: 12px; height: 10px; background: #34D399;"></span> 2
                        <span style="width: 12px; height: 10px; background: #064E3B;"></span> &ge;5
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Bouton Pleine Largeur Réinitialiser
        if st.button("Réinitialiser les filtres", key="hm_btn_reset"):
            st.session_state["health_map_selected_commune_code"] = None
            st.session_state["hm_province_select"] = "Toutes les provinces"
            st.session_state["hm_commune_select"] = "Aucune commune sélectionnée"
            st.session_state["hm_thematic_select"] = "Milieu territorial"
            st.session_state["hm_basemap_select"] = "Clair Professionnel"
            st.session_state["hm_show_hosp"] = True
            st.session_state["hm_show_essp"] = False
            st.session_state["hm_show_pharm"] = True
            st.session_state["hm_show_clinics"] = True
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # =======================================================================
    # COLONNE 2 (~51%) — Carte Interactive Pleine Hauteur (680px)
    # =======================================================================
    with col_map:
        # Centrage dynamique
        if active_code:
            target_comm = next((c for c in communes if str(c.get("commune_code")) == active_code), None)
            if target_comm and target_comm.get("centroid_lat") and target_comm.get("centroid_lon"):
                map_center = [target_comm["centroid_lat"], target_comm["centroid_lon"]]
                map_zoom = 11
            else:
                map_center = [35.25, -5.35]
                map_zoom = 8.5
        elif selected_province != "Toutes les provinces":
            prov_communes = [c for c in communes if str(c.get("province")) == selected_province]
            lats = [c["centroid_lat"] for c in prov_communes if c.get("centroid_lat")]
            lons = [c["centroid_lon"] for c in prov_communes if c.get("centroid_lon")]
            if lats and lons:
                map_center = [sum(lats) / len(lats), sum(lons) / len(lons)]
                map_zoom = 9.5
            else:
                map_center = [35.25, -5.35]
                map_zoom = 8.5
        else:
            map_center = [35.25, -5.35]
            map_zoom = 8.5

        # Initialisation de Folium SANS shortcut CartoDB (zéro watermark)
        fmap = folium.Map(
            location=map_center,
            zoom_start=map_zoom,
            tiles=None,
            control_scale=True,
        )

        # Ajout explicite du fond sélectionné
        tile_cfg = BASEMAP_TILES.get(selected_basemap, BASEMAP_TILES["Clair Professionnel"])
        folium.TileLayer(
            tiles=tile_cfg["tiles"],
            name=selected_basemap,
            attr=tile_cfg["attr"],
            subdomains=tile_cfg.get("subdomains", "abcd"),
            max_zoom=tile_cfg.get("max_zoom", 19),
            control=False,
        ).add_to(fmap)

        # Contrôle plein écran
        Fullscreen(position="topleft", title="Plein Écran SIG", title_cancel="Quitter").add_to(fmap)

        # Couche GeoJSON des 146 communes
        commune_data_by_code = {str(c["commune_code"]): c for c in communes}

        def style_fn(feature):
            code = str(feature.get("properties", {}).get("commune_code", "")).strip()
            is_active = (active_code is not None and code == active_code)
            row = commune_data_by_code.get(code)
            fill_col = _get_commune_choropleth_color(row, selected_thematic)
            return {
                "fillColor": fill_col,
                "fillOpacity": 0.92 if is_active else 0.78,
                "color": "#0D5C75" if is_active else "#FFFFFF",
                "weight": 3.5 if is_active else 1.2,
                "opacity": 1.0,
            }

        folium.GeoJson(
            commune_geojson,
            name="Communes TTA",
            style_function=style_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=["name_fr", "commune_code", "province", "population_2024"],
                aliases=["Commune :", "Code :", "Province :", "Population 2024 :"],
                localize=True,
                sticky=True,
            ),
        ).add_to(fmap)

        # Établissements filtrés
        valid_facilities = [
            f for f in facilities
            if f.get("has_gps") is True
            and f.get("validation_status") not in ("OUTSIDE_REGION_TERRITORY", "RECONCILED_PUBLIC_DUPLICATE")
        ]
        if selected_province != "Toutes les provinces":
            prov_codes = {str(c["commune_code"]) for c in filtered_communes_prov}
            valid_facilities = [f for f in valid_facilities if str(f.get("commune_code")) in prov_codes]

        # 1. Hôpitaux Publics (16 officiels non regroupés pour haute visibilité)
        if show_hosp:
            hosp_layer = folium.FeatureGroup(name="Hôpitaux Publics (16)")
            hosp_pts = [
                f for f in valid_facilities
                if f.get("facility_tier") == "PUBLIC_CORE"
                and f.get("validation_status") == "OFFICIAL_MINISTRY"
                and f.get("lat") and f.get("lon")
            ]
            for p in hosp_pts:
                folium.Marker(
                    location=[p["lat"], p["lon"]],
                    icon=get_facility_div_icon("pub_hospital", size=28),
                    tooltip=f"🏥 <strong>{html.escape(p.get('name', 'Hôpital Public'))}</strong><br/>{html.escape(p.get('commune_name_official', ''))} ({html.escape(p.get('province', ''))})",
                ).add_to(hosp_layer)
            hosp_layer.add_to(fmap)

        # 2. Soins Primaires ESSP (Cluster intelligent)
        if show_essp:
            essp_cluster = MarkerCluster(
                name="Soins Primaires ESSP",
                options={"maxClusterRadius": 30, "disableClusteringAtZoom": 13},
            )
            essp_pts = [
                f for f in valid_facilities
                if f.get("facility_tier") == "PUBLIC_CORE"
                and f.get("category_code") in ("CSU-1", "CSU-2", "CSR-1", "CSR-2", "DR")
                and f.get("lat") and f.get("lon")
            ]
            for p in essp_pts:
                folium.Marker(
                    location=[p["lat"], p["lon"]],
                    icon=get_facility_div_icon("clinic", size=22),
                    tooltip=f"🔷 <strong>{html.escape(p.get('name', 'Centre de Santé'))}</strong><br/>{html.escape(p.get('commune_name_official', ''))}",
                ).add_to(essp_cluster)
            essp_cluster.add_to(fmap)

        # 3. Pharmacies Validées (Cluster émeraude)
        if show_pharm:
            pharm_cluster = MarkerCluster(
                name="Pharmacies Validées",
                options={"maxClusterRadius": 35, "disableClusteringAtZoom": 13},
            )
            pharm_pts = [
                f for f in valid_facilities
                if f.get("facility_tier") == "PRIVATE_VALID"
                and f.get("category_code") == "PHARMACY"
                and f.get("lat") and f.get("lon")
            ]
            for p in pharm_pts:
                folium.Marker(
                    location=[p["lat"], p["lon"]],
                    icon=get_facility_div_icon("pharmacy", size=22),
                    tooltip=f"🟢 <strong>{html.escape(p.get('name', 'Pharmacie'))}</strong><br/>{html.escape(p.get('commune_name_official', ''))}",
                ).add_to(pharm_cluster)
            pharm_cluster.add_to(fmap)

        # 4. Cliniques & Spécialisés (Cluster violet)
        if show_clinics:
            clinics_cluster = MarkerCluster(
                name="Cliniques & Spécialisés",
                options={"maxClusterRadius": 30, "disableClusteringAtZoom": 13},
            )
            clinics_pts = [
                f for f in valid_facilities
                if f.get("facility_tier") == "PRIVATE_VALID"
                and f.get("category_code") in ("CLINIC", "DOCTOR", "LABORATORY", "HOSP_OSM_OTHER")
                and f.get("lat") and f.get("lon")
            ]
            for p in clinics_pts:
                folium.Marker(
                    location=[p["lat"], p["lon"]],
                    icon=get_facility_div_icon("other", size=24),
                    tooltip=f"🟣 <strong>{html.escape(p.get('name', 'Clinique/Cabinet'))}</strong><br/>{html.escape(p.get('commune_name_official', ''))}",
                ).add_to(clinics_cluster)
            clinics_cluster.add_to(fmap)

        # Rendu de la carte avec écoute des clics
        map_output = render_map(
            fmap,
            height=680,
            key="health_map_interactive_canvas",
            returned_objects=["last_active_drawing", "last_clicked"],
        )

        # Gestion dynamique du clic sur un polygone
        if map_output:
            last_clicked = map_output.get("last_clicked")
            last_drawing = map_output.get("last_active_drawing")

            click_signature = None
            if isinstance(last_clicked, dict) and last_clicked.get("lat") is not None:
                click_signature = f"{last_clicked.get('lat'):.6f}_{last_clicked.get('lng'):.6f}"
            elif isinstance(last_drawing, dict):
                click_signature = str(last_drawing.get("properties", {}).get("commune_code", ""))

            if click_signature and click_signature != st.session_state.get("_health_map_last_click_sig"):
                st.session_state["_health_map_last_click_sig"] = click_signature

                clicked_code = None
                if isinstance(last_drawing, dict):
                    props = last_drawing.get("properties") or {}
                    if props.get("commune_code"):
                        clicked_code = str(props["commune_code"]).strip()

                if not clicked_code and isinstance(last_clicked, dict):
                    c_lat = last_clicked.get("lat")
                    c_lng = last_clicked.get("lng")
                    if c_lat is not None and c_lng is not None:
                        clicked_code = find_commune_at_lat_lon(c_lat, c_lng, commune_geojson)

                if clicked_code and clicked_code != active_code:
                    st.session_state["health_map_selected_commune_code"] = clicked_code
                    st.rerun()

    # =======================================================================
    # COLONNE 3 (~25%) — Fiche Territoriale Sanitaire
    # =======================================================================
    with col_fiche:
        st.markdown('<div class="sig-card-container">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="sig-card-title" style="justify-content: space-between;">
                <span>📋 Fiche Territoriale Sanitaire</span>
                <span style="font-size: 11px; background: #E0F2FE; color: #0369A1; padding: 2px 8px; border-radius: 12px; font-weight: 600;">RSC-TTA</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_row = (
            next((c for c in communes if str(c.get("commune_code")) == active_code), None)
            if active_code
            else None
        )

        if selected_row:
            c_name = selected_row.get("name_fr", "Commune")
            c_code = selected_row.get("commune_code", "")
            c_prov = selected_row.get("province", "")
            c_milieu = str(selected_row.get("milieu", "Rural")).strip().capitalize()
            c_pop = selected_row.get("population_2024", 0) or 0
            c_hosp = selected_row.get("pub_hospitals", 0) or 0
            c_primary = selected_row.get("pub_primary_total", 0) or 0
            c_csu = selected_row.get("pub_csu", 0) or 0
            c_csr = selected_row.get("pub_csr", 0) or 0
            c_dr = selected_row.get("pub_dr", 0) or 0
            c_pharm = selected_row.get("osm_pharmacies_mapped", 0) or 0
            c_clin = selected_row.get("osm_clinics_mapped", 0) or 0
            c_ratio_prim = selected_row.get("primary_care_per_10k", 0.0) or 0.0
            c_ratio_pharm = selected_row.get("pharmacy_per_10k", 0.0) or 0.0

            # Couleur du badge Milieu
            if c_milieu == "Urbain":
                milieu_bg = "#0D5C75"
            elif c_milieu == "Mixte":
                milieu_bg = "#16A34A"
            else:
                milieu_bg = "#D97706"

            # Calcul des largeurs relatives pour les barres de progression
            pct_hosp = min(100, int((c_hosp / 3.0) * 100)) if c_hosp > 0 else 0
            pct_prim = min(100, int((c_primary / 6.0) * 100)) if c_primary > 0 else 0
            pct_pharm = min(100, int((c_pharm / 20.0) * 100)) if c_pharm > 0 else 0
            pct_clin = min(100, int((c_clin / 5.0) * 100)) if c_clin > 0 else 0

            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <div style="font-size: 18px; font-weight: 750; color: #0F172A;">{html.escape(c_name)}</div>
                    <span style="background: {milieu_bg}; color: #FFFFFF; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px;">
                        {html.escape(c_milieu)}
                    </span>
                </div>
                <div style="font-size: 12px; color: #64748B; margin-bottom: 12px;">
                    <strong>Province :</strong> {html.escape(c_prov)} &nbsp;|&nbsp; <strong>Pop. :</strong> {c_pop:,} hab.
                </div>

                <div style="font-size: 11px; font-weight: 700; color: #0D5C75; text-transform: uppercase; letter-spacing: 0.5px; margin: 10px 0 6px;">
                    1. Équipements Publics Officiels
                </div>

                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
                        <span style="color: #475569;">Hôpitaux Publics :</span>
                        <strong style="color: #DC2626;">{c_hosp}</strong>
                    </div>
                    <div style="background: #E2E8F0; border-radius: 6px; height: 7px; overflow: hidden;">
                        <div style="background: #DC2626; width: {pct_hosp}%; height: 100%;"></div>
                    </div>
                </div>

                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
                        <span style="color: #475569;">CSU / CSR / DR :</span>
                        <strong style="color: #0D5C75;">{c_primary}</strong>
                    </div>
                    <div style="background: #E2E8F0; border-radius: 6px; height: 7px; overflow: hidden;">
                        <div style="background: #0D5C75; width: {pct_prim}%; height: 100%;"></div>
                    </div>
                    <div style="font-size: 10px; color: #64748B; margin-top: 2px;">
                        • CSU : {c_csu} | CSR : {c_csr} | DR : {c_dr}
                    </div>
                </div>

                <div style="font-size: 11px; font-weight: 700; color: #16A34A; text-transform: uppercase; letter-spacing: 0.5px; margin: 12px 0 6px;">
                    2. Pharmacies & Cliniques Privées (OSM)
                </div>

                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
                        <span style="color: #475569;">Pharmacies :</span>
                        <strong style="color: #16A34A;">{c_pharm}</strong>
                    </div>
                    <div style="background: #E2E8F0; border-radius: 6px; height: 7px; overflow: hidden;">
                        <div style="background: #16A34A; width: {pct_pharm}%; height: 100%;"></div>
                    </div>
                </div>

                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
                        <span style="color: #475569;">Cliniques & Cabinets :</span>
                        <strong style="color: #7C3AED;">{c_clin}</strong>
                    </div>
                    <div style="background: #E2E8F0; border-radius: 6px; height: 7px; overflow: hidden;">
                        <div style="background: #7C3AED; width: {pct_clin}%; height: 100%;"></div>
                    </div>
                </div>

                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 10px; margin-top: 10px;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
                        <span style="color: #64748B;">Soins Primaires / 10k hab. :</span>
                        <strong style="color: {'#DC2626' if c_ratio_prim < 1.0 else '#0D5C75'};">{c_ratio_prim:.2f}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11px;">
                        <span style="color: #64748B;">Pharmacies / 10k hab. :</span>
                        <strong style="color: #16A34A;">{c_ratio_pharm:.2f}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Bouton d'action pour ouvrir le profil complet (Dashboard 4)
            if st.button("Ouvrir le profil complet →", key="hm_cta_details"):
                st.session_state["details_commune"] = f"{c_name} · {c_prov} · {c_code}"
                st.session_state["pending_navigation_page"] = "Commune Details"
                st.rerun()

        else:
            st.markdown(
                """
                <div style="background: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 10px; padding: 48px 16px; text-align: center; color: #64748B; margin-top: 40px;">
                    <div style="font-size: 2.6rem; margin-bottom: 12px;">🗺️</div>
                    <div style="font-weight: 750; color: #0F172A; font-size: 1.05rem; margin-bottom: 6px;">
                        Sélectionnez une commune
                    </div>
                    <p style="font-size: 0.84rem; line-height: 1.5; margin: 0 0 14px; color: #475569;">
                        Cliquez directement sur un territoire communal sur la carte ou choisissez une commune dans le menu déroulant à gauche pour afficher sa <strong>Fiche Territoriale Sanitaire</strong>.
                    </p>
                    <div style="font-size: 0.76rem; color: #0D5C75; background: #E0F2FE; padding: 5px 12px; border-radius: 20px; display: inline-block; font-weight: 600;">
                        Données officielles RSC-TTA · 146 Communes
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
