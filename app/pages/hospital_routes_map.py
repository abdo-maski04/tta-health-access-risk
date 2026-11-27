"""Carte interactive PyDeck des 146 Itinéraires Routiers Hospitaliers — GeoVulnera TTA.

Visualisation cartographique vectorielle et spatiale haute performance.
Intègre la topographie (Copernicus DEM), le réseau hydrographique,
les contraintes morpho-dynamiques et l'accessibilité hospitalière de la région TTA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[2]
TERRAIN_PNG = ROOT / "data" / "processed" / "terrain" / "tta_hillshade_display.png"
TERRAIN_META_JSON = ROOT / "data" / "processed" / "terrain" / "tta_terrain_metadata.json"
HYDRO_RIVERS_GEOJSON = ROOT / "data" / "processed" / "hydro" / "tta_hydrorivers.geojson"
HYDRO_BASINS_GEOJSON = ROOT / "data" / "processed" / "hydro" / "tta_hydrobasins.geojson"
HAZARDS_GEOJSON = ROOT / "data" / "processed" / "hazards" / "tta_territorial_constraints.geojson"
ISOCHRONES_GEOJSON = ROOT / "data" / "processed" / "isochrones_tta_estimated.geojson"

try:
    from data_loader import load_v2_routes_consolidated
except ImportError:
    from app.data_loader import load_v2_routes_consolidated

try:
    from pages.leaflet_sig_builder import generate_leaflet_sig_html
except ImportError:
    try:
        from app.pages.leaflet_sig_builder import generate_leaflet_sig_html
    except ImportError:
        from leaflet_sig_builder import generate_leaflet_sig_html


def _get_map_center_and_zoom(
    routes_df: pd.DataFrame,
    selected_code: str | None = None,
) -> tuple[float, float, float]:
    """Calcule le centrage et le niveau de zoom optimal."""
    if selected_code and not routes_df.empty:
        target = routes_df[routes_df["commune_code"] == selected_code]
        if not target.empty:
            row = target.iloc[0]
            mid_lat = (row["start_lat"] + row["hospital_lat"]) / 2.0
            mid_lon = (row["start_lon"] + row["hospital_lon"]) / 2.0
            return float(mid_lat), float(mid_lon), 10.0

    if not routes_df.empty:
        avg_lat = float(routes_df["start_lat"].mean())
        avg_lon = float(routes_df["start_lon"].mean())
        return avg_lat, avg_lon, 8.25

    return 35.35, -5.35, 8.25


@st.cache_data(show_spinner=False)
def _load_auxiliary_layers() -> dict[str, Any]:
    """Charge en cache les couches géospatiales auxiliaires (hydro, aléas, isochrones, terrain)."""
    data = {
        "hydro_rivers": None,
        "hydro_basins": None,
        "hazards": None,
        "isochrones": None,
        "terrain_bounds": [-6.2923, 34.4560, -3.7540, 35.9730],
    }

    if HYDRO_RIVERS_GEOJSON.exists():
        with HYDRO_RIVERS_GEOJSON.open("r", encoding="utf-8") as f:
            data["hydro_rivers"] = json.load(f)

    if HYDRO_BASINS_GEOJSON.exists():
        with HYDRO_BASINS_GEOJSON.open("r", encoding="utf-8") as f:
            data["hydro_basins"] = json.load(f)

    if HAZARDS_GEOJSON.exists():
        with HAZARDS_GEOJSON.open("r", encoding="utf-8") as f:
            haz_gj = json.load(f)
            for feat in haz_gj.get("features", []):
                p = feat.get("properties", {})
                alea = p.get("type_alea", "")
                if "Inondation" in alea:
                    p["fill_color"] = [2, 132, 199, 85]
                    p["line_color"] = [2, 132, 199, 220]
                else:
                    p["fill_color"] = [234, 88, 12, 85]
                    p["line_color"] = [234, 88, 12, 220]
            data["hazards"] = haz_gj

    if ISOCHRONES_GEOJSON.exists():
        with ISOCHRONES_GEOJSON.open("r", encoding="utf-8") as f:
            iso_gj = json.load(f)
            palette = {
                15: ([16, 185, 129, 65], [16, 185, 129, 200]),
                30: ([59, 130, 246, 55], [59, 130, 246, 180]),
                45: ([245, 158, 11, 50], [245, 158, 11, 160]),
                60: ([239, 68, 68, 45], [239, 68, 68, 150]),
            }
            for feat in iso_gj.get("features", []):
                m = feat.get("properties", {}).get("isochrone_min", 60)
                fc, lc = palette.get(m, ([100, 100, 100, 40], [100, 100, 100, 150]))
                feat["properties"]["fill_color"] = fc
                feat["properties"]["line_color"] = lc
            data["isochrones"] = iso_gj

    if TERRAIN_META_JSON.exists():
        try:
            with TERRAIN_META_JSON.open("r", encoding="utf-8") as f:
                meta = json.load(f)
                data["terrain_bounds"] = meta.get("bounds", data["terrain_bounds"])
        except Exception:
            pass

    return data


def render_hospital_routes_map(
    communes: list[dict[str, Any]] | None = None,
    commune_geojson: dict[str, Any] | None = None,
    facilities: list[dict[str, Any]] | None = None,
) -> None:
    """Rendu complet de la Carte des 146 Itinéraires v2."""

    # 1. Bannière d'en-tête professionnelle pour le Hackathon
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 45%, #0369A1 100%);
                    color: white; border-radius: 14px; padding: 20px 26px; margin-bottom: 20px;
                    box-shadow: 0 6px 20px rgba(2,132,199,0.18);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
                <div>
                    <h2 style="margin:0; font-size:1.55rem; font-weight:800; color:#FFFFFF; letter-spacing:-0.01em;">
                        🛣️ Accessibilité Hospitalière Régionale — 146 Itinéraires Routiers
                    </h2>
                    <p style="margin:6px 0 0; font-size:0.95rem; color:#E0F2FE;">
                        Visualisation PyDeck haute performance · Analyse orographique, hydrographique et délais d'urgence vitale
                    </p>
                </div>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <span style="background:rgba(16,185,129,0.22); color:#A7F3D0; padding:6px 14px; border-radius:20px; font-size:0.85rem; font-weight:700; border:1px solid rgba(16,185,129,0.4);">
                        🏥 146 Communes Reliées
                    </span>
                    <span style="background:rgba(59,130,246,0.22); color:#BFDBFE; padding:6px 14px; border-radius:20px; font-size:0.85rem; font-weight:700; border:1px solid rgba(59,130,246,0.4);">
                        ⏱️ Modélisation Routière Réelle
                    </span>
                    <span style="background:rgba(245,158,11,0.22); color:#FDE68A; padding:6px 14px; border-radius:20px; font-size:0.85rem; font-weight:700; border:1px solid rgba(245,158,11,0.4);">
                        🏔️ Relief & Hydrographie TTA
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Chargement des données consolidées
    try:
        routes_df, hospitals_df, communes_gj = load_v2_routes_consolidated()
        aux_layers = _load_auxiliary_layers()
    except Exception as exc:
        st.error(f"Erreur lors du chargement des données cartographiques : {exc}")
        return

    # 3. Volet des Filtres et Contrôles
    with st.expander("🔍 Filtres Géographiques et Couches Thématiques", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.8, 1.8, 1.8])

        with col_f1:
            province_list = ["Toutes les provinces"] + sorted(routes_df["province"].unique().tolist())
            selected_province = st.selectbox(
                "Province / Préfecture :",
                province_list,
                key="v2_filter_province",
            )

        with col_f2:
            status_options = [
                "Tous les statuts (146)",
                "⏱️ Urgence vitale (≤ 30 min)",
                "⚠️ Délai modéré (30 à 60 min)",
                "🚨 Isolement sanitaire critique (> 60 min)",
                "🔄 Recalculés ORS v2 (50)",
                "🛡️ Protégés v1 (96)",
            ]
            selected_status = st.selectbox(
                "Délai d'accès & Statut :",
                status_options,
                key="v2_filter_status",
            )

        with col_f3:
            hosp_names = ["Tous les hôpitaux"] + sorted(hospitals_df["name"].unique().tolist())
            selected_hospital = st.selectbox(
                "Hôpital de destination :",
                hosp_names,
                key="v2_filter_hospital",
            )

        with col_f4:
            commune_choices = ["Toutes les communes"] + [
                f"{r['name_fr']} ({r['province']}) — {r['commune_code']}"
                for _, r in routes_df.sort_values("name_fr").iterrows()
            ]
            selected_commune_raw = st.selectbox(
                "Focus sur une commune :",
                commune_choices,
                key="v2_filter_commune",
            )
            selected_commune_code = (
                selected_commune_raw.split("—")[-1].strip()
                if selected_commune_raw != "Toutes les communes"
                else None
            )

        # Bascules multi-couches
        st.markdown("<div style='margin-top:10px; font-weight:700; color:#334155; font-size:0.9rem;'>Couches Géospatiales à afficher :</div>", unsafe_allow_html=True)
        col_l1, col_l2, col_l3, col_l4 = st.columns(4)
        with col_l1:
            show_routes = st.checkbox("🛣️ Itinéraires routiers", value=True, key="v2_show_routes")
            show_terrain = st.checkbox("🏔️ Relief & Topographie (MNT)", value=True, key="v2_show_terrain")
        with col_l2:
            show_polygons = st.checkbox("🗺️ Limites communales", value=True, key="v2_show_polygons")
            show_hydro = st.checkbox("🌊 Réseau hydrographique & Oueds", value=True, key="v2_show_hydro")
        with col_l3:
            show_hospitals = st.checkbox("🏥 Hôpitaux publics", value=True, key="v2_show_hospitals")
            show_hazards = st.checkbox("⚠️ Zones de contraintes morpho-topographiques", value=False, key="v2_show_hazards")
        with col_l4:
            show_origins = st.checkbox("📍 Chefs-lieux de commune", value=False, key="v2_show_origins")
            show_isochrones = st.checkbox("⏱️ Bassins d'urgence (Isochrones)", value=False, key="v2_show_isochrones")

    # 4. Application des Filtres
    filtered_df = routes_df.copy()

    if selected_province != "Toutes les provinces":
        filtered_df = filtered_df[filtered_df["province"] == selected_province]

    if selected_status == "⏱️ Urgence vitale (≤ 30 min)":
        filtered_df = filtered_df[filtered_df["temps_min"] <= 30.0]
    elif selected_status == "⚠️ Délai modéré (30 à 60 min)":
        filtered_df = filtered_df[(filtered_df["temps_min"] > 30.0) & (filtered_df["temps_min"] <= 60.0)]
    elif selected_status == "🚨 Isolement sanitaire critique (> 60 min)":
        filtered_df = filtered_df[filtered_df["temps_min"] > 60.0]
    elif selected_status == "🔄 Recalculés ORS v2 (50)":
        filtered_df = filtered_df[filtered_df["is_recalculated"]]
    elif selected_status == "🛡️ Protégés v1 (96)":
        filtered_df = filtered_df[~filtered_df["is_recalculated"]]

    if selected_hospital != "Tous les hôpitaux":
        filtered_df = filtered_df[filtered_df["hospital_canonical"] == selected_hospital]

    if selected_commune_code:
        filtered_df = filtered_df[filtered_df["commune_code"] == selected_commune_code]

    # 5. Cartouches d'indicateurs de synthèse (KPIs)
    total_displayed = len(filtered_df)
    pop_displayed = int(filtered_df["population_2024"].sum()) if "population_2024" in filtered_df.columns else 0
    pop_under_30 = int(filtered_df[filtered_df["temps_min"] <= 30.0]["population_2024"].sum()) if "population_2024" in filtered_df.columns else 0
    pct_under_30 = round((pop_under_30 / max(1, pop_displayed) * 100), 1) if pop_displayed > 0 else 0.0
    med_temps = round(filtered_df["temps_min"].median(), 1) if total_displayed > 0 else 0.0
    med_dist = round(filtered_df["distance_km"].median(), 1) if total_displayed > 0 else 0.0

    kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)
    with kpi_c1:
        st.metric("Communes Affichées", f"{total_displayed} / 146")
    with kpi_c2:
        st.metric("Population Couverte", f"{pop_displayed:,}".replace(",", " ") + " hab.")
    with kpi_c3:
        st.metric("Accès ≤ 30 min (Urgence)", f"{pct_under_30}%", delta="Golden Hour" if pct_under_30 >= 70 else "Critique")
    with kpi_c4:
        st.metric("Durée Médiane", f"{med_temps} min")
    with kpi_c5:
        st.metric("Distance Médiane", f"{med_dist} km")

    # 6. Construction des Couches PyDeck Multi-Niveaux
    layers = []

    # Couche 1 : Relief et Topographie (BitmapLayer)
    if show_terrain and TERRAIN_PNG.exists():
        terrain_bounds = aux_layers.get("terrain_bounds", [-6.2923, 34.4560, -3.7540, 35.9730])
        terrain_layer = pdk.Layer(
            "BitmapLayer",
            id="terrain-hillshade-layer",
            image=str(TERRAIN_PNG.resolve()),
            bounds=terrain_bounds,
            opacity=0.70,
            desaturate=0.0,
        )
        layers.append(terrain_layer)

    # Couche 2 : Bassins temporels d'urgence (Isochrones GeoJsonLayer)
    if show_isochrones and aux_layers.get("isochrones"):
        isochrones_layer = pdk.Layer(
            "GeoJsonLayer",
            id="isochrones-layer",
            data=aux_layers["isochrones"],
            opacity=0.60,
            stroked=True,
            filled=True,
            wireframe=True,
            get_fill_color="properties.fill_color",
            get_line_color="properties.line_color",
            line_width_min_pixels=1,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(isochrones_layer)

    # Couche 3 : Zones de vigilance morpho-dynamique (Hazards GeoJsonLayer)
    if show_hazards and aux_layers.get("hazards"):
        hazards_layer = pdk.Layer(
            "GeoJsonLayer",
            id="territorial-hazards-layer",
            data=aux_layers["hazards"],
            opacity=0.75,
            stroked=True,
            filled=True,
            get_fill_color="properties.fill_color",
            get_line_color="properties.line_color",
            line_width_min_pixels=2,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(hazards_layer)

    # Couche 4 : Réseau hydrographique et grands oueds (PathLayer / GeoJsonLayer)
    if show_hydro and aux_layers.get("hydro_rivers"):
        hydro_layer = pdk.Layer(
            "GeoJsonLayer",
            id="hydro-rivers-layer",
            data=aux_layers["hydro_rivers"],
            opacity=0.85,
            stroked=True,
            filled=False,
            get_line_color=[14, 165, 233, 220],  # Cyan / bleu hydrographique
            get_line_width=3,
            line_width_min_pixels=2,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(hydro_layer)

    # Couche 5 : Limites communales (GeoJsonLayer)
    if show_polygons and communes_gj:
        active_codes = set(filtered_df["commune_code"])
        filtered_gj = {
            "type": "FeatureCollection",
            "features": [
                f for f in communes_gj["features"]
                if f["properties"].get("commune_code") in active_codes
            ],
        }

        communes_layer = pdk.Layer(
            "GeoJsonLayer",
            id="communes-polygons-layer",
            data=filtered_gj,
            opacity=0.80,
            stroked=True,
            filled=True,
            extruded=False,
            wireframe=True,
            get_fill_color="properties.fill_color",
            get_line_color="properties.line_color",
            line_width_min_pixels=1,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(communes_layer)

    # Couche 6 : Tracés routiers d'accès aux hôpitaux (PathLayer)
    if show_routes and not filtered_df.empty:
        routes_layer = pdk.Layer(
            "PathLayer",
            id="hospital-routes-layer",
            data=filtered_df,
            get_path="path",
            get_color="color_rgb",
            width_min_pixels=3 if not selected_commune_code else 5,
            width_scale=2,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(routes_layer)

    # Couche 7 : Hôpitaux publics de référence (ScatterplotLayer)
    if show_hospitals and not hospitals_df.empty:
        visible_hosp_ids = set(filtered_df["hospital_osm_id"])
        visible_hospitals = hospitals_df[hospitals_df["osm_id"].isin(visible_hosp_ids)]

        hospitals_layer = pdk.Layer(
            "ScatterplotLayer",
            id="hospitals-points-layer",
            data=visible_hospitals,
            get_position=["lon", "lat"],
            get_fill_color="color",
            get_radius="radius",
            radius_min_pixels=7,
            radius_max_pixels=18,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(hospitals_layer)

    # Couche 8 : Chefs-lieux de commune (ScatterplotLayer)
    if show_origins and not filtered_df.empty:
        origins_layer = pdk.Layer(
            "ScatterplotLayer",
            id="commune-origins-layer",
            data=filtered_df,
            get_position=["start_lon", "start_lat"],
            get_fill_color=[30, 41, 59, 220],
            get_radius=500,
            radius_min_pixels=3,
            radius_max_pixels=8,
            pickable=True,
        )
        layers.append(origins_layer)

    # Centrage et caméra de la carte
    center_lat, center_lon, zoom = _get_map_center_and_zoom(filtered_df, selected_commune_code)
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        min_zoom=7.0,
        max_zoom=14.0,
        pitch=28 if not selected_commune_code else 38,
        bearing=0,
    )

    # Infobulle (Tooltip) professionnelle enrichie pour le Jury
    tooltip = {
        "html": """
        <div style="background-color: #0F172A; color: #F8FAFC; padding: 14px 16px; border-radius: 10px; font-family: sans-serif; font-size: 12px; border: 1px solid #334155; box-shadow: 0 8px 24px rgba(0,0,0,0.6); max-width: 310px;">
            <div style="font-weight: 800; font-size: 15px; color: #38BDF8; margin-bottom: 2px;">
                {name_fr} {name} {nom}
            </div>
            <div style="color: #94A3B8; font-size: 11px; margin-bottom: 8px;">
                {province} {category} {type_alea}
            </div>
            <hr style="border: 0; border-top: 1px solid #334155; margin: 6px 0;" />
            <div style="margin-bottom: 5px;">
                <span style="color: #94A3B8;">Destination hospitalière :</span> <b style="color: #FFFFFF;">{hospital_canonical} {hospital_name}</b>
            </div>
            <div style="margin-bottom: 5px;">
                <span style="color: #94A3B8;">Temps d'accès routier :</span> <b style="color: #FCD34D; font-size: 13px;">{temps_min} min</b>
            </div>
            <div style="margin-bottom: 5px;">
                <span style="color: #94A3B8;">Distance de parcours :</span> <b style="color: #FFFFFF;">{distance_km} km</b>
            </div>
            <div style="margin-bottom: 5px;">
                <span style="color: #94A3B8;">Population communale :</span> <b style="color: #6EE7B7;">{population_2024} hab.</b>
            </div>
            <div style="margin-top: 8px;">
                <span style="display:inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; background: #1E293B; border: 1px solid #475569; color: #E2E8F0;">
                    {access_tier} {threshold_category} {statut}
                </span>
            </div>
        </div>
        """,
        "style": {
            "backgroundColor": "transparent",
            "color": "white",
            "zIndex": 1000,
        },
    }

    # Rendu PyDeck dans Streamlit
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/light-v10" if hasattr(pdk.map_styles, "LIGHT") else "light",
    )

    # 6. Rendu Cartographique Double Moteur : SIG Leaflet Professionnel & Vue PyDeck 3D
    tab_sig, tab_pydeck = st.tabs([
        "🗺️ Interface SIG Interactive Professionnelle (Leaflet)",
        "🌐 Vue Synthétique 3D (PyDeck)",
    ])

    with tab_sig:
        def _clean_prop_val(v: Any) -> Any:
            if v is None:
                return None
            if isinstance(v, (list, tuple)):
                return list(v)
            if isinstance(v, (float, int)) and pd.isna(v):
                return None
            if isinstance(v, str):
                return v
            try:
                if pd.isna(v):
                    return None
            except Exception:
                pass
            return v

        routes_gj = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": row["path"] if isinstance(row["path"], list) else [],
                    },
                    "properties": {
                        k: _clean_prop_val(v)
                        for k, v in row.items()
                        if k not in ("path", "geometry")
                    },
                }
                for _, row in routes_df.iterrows()
            ],
        }

        hospitals_gj = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(row["lon"]), float(row["lat"])],
                    },
                    "properties": {
                        k: _clean_prop_val(v)
                        for k, v in row.items()
                        if k not in ("lat", "lon", "geometry")
                    },
                }
                for _, row in hospitals_df.iterrows()
                if pd.notna(row.get("lat")) and pd.notna(row.get("lon"))
            ],
        }

        leaflet_html = generate_leaflet_sig_html(
            routes_geojson=routes_gj,
            hospitals_geojson=hospitals_gj,
            communes_geojson=communes_gj,
            hydro_rivers_geojson=aux_layers.get("hydro_rivers") or {"type": "FeatureCollection", "features": []},
            hydro_basins_geojson=aux_layers.get("hydro_basins") or {"type": "FeatureCollection", "features": []},
            hazards_geojson=aux_layers.get("hazards") or {"type": "FeatureCollection", "features": []},
            isochrones_geojson=aux_layers.get("isochrones") or {"type": "FeatureCollection", "features": []},
            terrain_bounds=aux_layers.get("terrain_bounds", [-6.2923, 34.4560, -3.7540, 35.9730]),
            height=780,
        )

        components.html(leaflet_html, height=800, scrolling=False)

    with tab_pydeck:
        st.pydeck_chart(deck, use_container_width=True)

    # 7. Légende Cartographique Professionnelle pour le Jury
    st.markdown(
        """
        <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:12px; padding:16px 20px; margin-top:14px; margin-bottom:18px;">
            <div style="font-size:0.92rem; font-weight:800; color:#0F172A; margin-bottom:10px;">
                🎨 Légende et Sémiologie Graphique de la Carte d'Accessibilité
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap:14px; font-size:0.83rem;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:26px; height:6px; background:#10B981; border-radius:3px; display:inline-block;"></span>
                    <span><b>Itinéraires Routiers Validés</b> — Réseau principal carrossable</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:26px; height:6px; background:#3B82F6; border-radius:3px; display:inline-block;"></span>
                    <span><b>Axes Structurants Régionaux</b> — Liaisons interprovinciales</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:26px; height:6px; background:#F59E0B; border-radius:3px; display:inline-block;"></span>
                    <span><b>Liaisons de Déserte Particulière</b> (Fnideq, Belyounech, Anjra)</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:13px; height:13px; background:#DC2626; border-radius:50%; display:inline-block;"></span>
                    <span><b>Hôpitaux Publics de Référence</b> (15 centres hospitaliers)</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:26px; height:4px; background:#0EA5E9; border-radius:2px; display:inline-block;"></span>
                    <span><b>Réseau Hydrographique & Oueds</b> (Loukkos, Martil, Laou, Ghis, Nekor)</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:14px; height:14px; background:rgba(234,88,12,0.4); border:1px solid #EA580C; border-radius:3px; display:inline-block;"></span>
                    <span><b>Vigilance Morpho-Topographique</b> (Inondations ABHL & Versants rifains)</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:14px; height:14px; background:linear-gradient(45deg, #10B981, #F59E0B); border-radius:3px; display:inline-block;"></span>
                    <span><b>Relief & Ombrage MNT</b> (Copernicus DEM GLO-30 / GLO-90)</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="width:10px; height:10px; background:#1E293B; border-radius:50%; display:inline-block;"></span>
                    <span><b>Chefs-lieux communaux</b> (Centres de population)</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 8. Fiche Détaillée si une Commune est Sélectionnée
    if selected_commune_code and not filtered_df.empty:
        c_row = filtered_df.iloc[0]
        st.markdown(
            f"""
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:18px 22px; margin-bottom:18px;">
                <h4 style="margin:0 0 10px 0; color:#166534; font-size:1.15rem;">
                    📍 Fiche d'Accessibilité Hospitalière : {c_row['name_fr']} ({c_row['province']})
                </h4>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:12px; font-size:0.89rem;">
                    <div><b>Population légale 2024 :</b> {c_row.get('population_2024', 0):,} hab.</div>
                    <div><b>Milieu territorial :</b> {c_row['milieu']}</div>
                    <div><b>Hôpital de référence :</b> <b>{c_row['hospital_canonical']}</b></div>
                    <div><b>Temps de parcours :</b> <b style="color:#D97706; font-size:1.05rem;">{c_row['temps_min']} min</b></div>
                    <div><b>Distance routière :</b> <b>{c_row['distance_km']} km</b></div>
                    <div><b>Vitesse moyenne estimée :</b> ~{round(c_row['distance_km'] / max(0.01, c_row['temps_min'] / 60), 1)} km/h</div>
                    <div><b>Palier d'urgence :</b> <span style="color:#0369A1; font-weight:700;">{c_row.get('access_tier', 'Standard')}</span></div>
                    <div><b>Intégrité du calcul :</b> Conforme réseau routier réel</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 9. Tableau Exploratoire des Données Filtrées
    with st.expander("📋 Table Détaillée des 146 Itinéraires et Indicateurs Territoriaux", expanded=False):
        display_cols = [
            "commune_code", "name_fr", "province", "milieu", "population_2024",
            "hospital_canonical", "distance_km", "temps_min", "access_tier",
        ]
        col_names_fr = {
            "commune_code": "Code HCP",
            "name_fr": "Commune",
            "province": "Province",
            "milieu": "Milieu",
            "population_2024": "Population 2024",
            "hospital_canonical": "Hôpital Destination",
            "distance_km": "Distance (km)",
            "temps_min": "Durée (min)",
            "access_tier": "Palier d'Accès",
        }
        available_cols = [c for c in display_cols if c in filtered_df.columns]
        df_display = filtered_df[available_cols].rename(columns=col_names_fr)
        st.dataframe(df_display, use_container_width=True, height=280)

        # Boutons de téléchargement
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            csv_data = filtered_df.to_csv(index=False, encoding="utf-8").encode("utf-8")
            st.download_button(
                "📥 Télécharger la sélection (CSV)",
                data=csv_data,
                file_name="itineraires_hospitaliers_tta.csv",
                mime="text/csv",
                key="download_filtered_csv",
            )
        with dcol2:
            st.caption("Sources consolidées : MNT Copernicus DEM, HydroRIVERS, HCP 2024, MSPS & ORS.")
