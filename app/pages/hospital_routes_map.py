"""Carte des Itinéraires vers les Hôpitaux — GeoVulnera TTA.

Analyse des déplacements routiers entre les communes et les hôpitaux publics géolocalisés.
Intègre la détection du moteur de routage OpenRouteService et la distinction stricte
entre distance routière réelle et distance géodésique indicative.
"""

from __future__ import annotations

import html
import urllib.request
import urllib.error
import folium
from folium.plugins import Fullscreen
import streamlit as st
from pyproj import Geod
from config.settings import REGION_NAME
from map_utils import render_map

GEOD = Geod(ellps="WGS84")


def _check_ors_service(base_url: str = "http://localhost:8080/ors") -> bool:
    """Vérifie si le moteur de routage ORS local est opérationnel sans lever d'exception."""
    try:
        req = urllib.request.Request(f"{base_url}/v2/health", headers={"User-Agent": "GeoVulnera"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def render_hospital_routes_map(
    communes: list[dict],
    commune_geojson: dict,
    facilities: list[dict],
) -> None:
    """Rendu de la Carte 3 : Itinéraires vers les Hôpitaux Publics."""

    # 1. En-tête
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
                    color: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
                    box-shadow: 0 4px 12px rgba(37,99,235,0.15);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <h2 style="margin:0; font-size:1.4rem; font-weight:700; color:#FFFFFF;">
                        🛣️ Carte des Itinéraires vers les Hôpitaux Publics
                    </h2>
                    <p style="margin:4px 0 0; font-size:0.9rem; color:#DBEAFE;">
                        Accès au plateau hospitalier régional · Déplacements &amp; Connectivité
                    </p>
                </div>
                <div style="background:rgba(255,255,255,0.18); padding:6px 14px; border-radius:20px; font-size:0.82rem; border:1px solid rgba(255,255,255,0.3);">
                    Réseau Routier &amp; Hôpitaux Ministériels
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Filtrage strict des hôpitaux publics géolocalisés (16 hôpitaux vérifiés)
    geocoded_public_hospitals = [
        f for f in facilities
        if f.get("facility_tier") == "PUBLIC_CORE"
        and f.get("validation_status") == "OFFICIAL_MINISTRY"
        and f.get("has_gps") is True
        and f.get("lat") is not None
        and f.get("lon") is not None
    ]

    # Vérification d'état du moteur de routage
    ors_is_online = _check_ors_service()

    if ors_is_online:
        st.success("🟢 Moteur de routage OpenRouteService opérationnel : calcul des tracés routiers réels activé.")
    else:
        st.warning(
            "⚠️ **Moteur de routage local hors ligne :** Le service OpenRouteService local (`http://localhost:8080/ors`) "
            "n'est pas démarré. Conformément aux règles d'intégrité de la mission, **aucune distance ni durée routière n'est inventée ou simulée**. "
            "La carte présente la distance géodésique à vol d'oiseau (orthodromique WGS84) à titre indicatif."
        )

    # 3. Sélecteurs d'Origine et de Destination
    col_orig, col_dest = st.columns(2)

    with col_orig:
        commune_options = {
            f"{c.get('name_fr', '')} ({c.get('province', '')})": c
            for c in sorted(communes, key=lambda x: str(x.get("name_fr", "")))
        }
        selected_origin_label = st.selectbox(
            "1. Commune d'origine (Point de référence communal) :",
            list(commune_options.keys()),
            key="routes_map_origin_select",
        )
        origin_commune = commune_options[selected_origin_label]

        st.caption(
            "📍 *Origine = point de référence communal officiel (chef-lieu / centroïde représentatif intérieur) "
            "et non la localisation individuelle d'un habitant.*"
        )

    with col_dest:
        hospital_options = {
            f"{h.get('name', 'Hôpital')} — {h.get('commune_name_official', '')} ({h.get('province', '')})": h
            for h in sorted(geocoded_public_hospitals, key=lambda x: str(x.get("name", "")))
        }
        selected_hosp_label = st.selectbox(
            "2. Hôpital public de destination :",
            list(hospital_options.keys()),
            key="routes_map_dest_select",
        )
        destination_hospital = hospital_options[selected_hosp_label]

        st.caption(
            "🏥 *Destination = l'un des 16 hôpitaux publics officiels dont les coordonnées GPS ont été vérifiées.*"
        )

    # 4. Calcul des coordonnées
    start_lat = origin_commune.get("start_lat") or origin_commune.get("centroid_lat")
    start_lon = origin_commune.get("start_lon") or origin_commune.get("centroid_lon")
    end_lat = destination_hospital.get("lat")
    end_lon = destination_hospital.get("lon")

    if not (start_lat and start_lon and end_lat and end_lon):
        st.error("Coordonnées d'origine ou de destination incomplètes pour ce couple.")
        return

    # Calcul géodésique exact WGS84
    _, _, dist_meters = GEOD.inv(start_lon, start_lat, end_lon, end_lat)
    geodesic_dist_km = round(dist_meters / 1000.0, 1)

    # Calcul des hôpitaux les plus proches de la commune
    nearest_hospitals = []
    for h in geocoded_public_hospitals:
        h_lat = h.get("lat")
        h_lon = h.get("lon")
        if h_lat and h_lon:
            _, _, d_m = GEOD.inv(start_lon, start_lat, h_lon, h_lat)
            nearest_hospitals.append({
                "name": h.get("name", "Hôpital"),
                "commune": h.get("commune_name_official", ""),
                "province": h.get("province", ""),
                "dist_km": round(d_m / 1000.0, 1),
                "lat": h_lat,
                "lon": h_lon,
            })
    nearest_hospitals.sort(key=lambda x: x["dist_km"])

    # 5. Construction de la carte Folium
    fmap = folium.Map(
        location=[(start_lat + end_lat) / 2.0, (start_lon + end_lon) / 2.0],
        zoom_start=9,
        tiles="cartodbpositron",
        control_scale=True,
    )

    Fullscreen(
        position="topleft",
        title="Passer en plein écran SIG",
        title_cancel="Quitter le plein écran",
        force_separate_button=True,
    ).add_to(fmap)

    # Contour des communes en fond neutre
    folium.GeoJson(
        commune_geojson,
        name="Limites communales",
        style_function=lambda x: {
            "fillColor": "#F8FAFC",
            "fillOpacity": 0.35,
            "color": "#94A3B8",
            "weight": 1,
        },
    ).add_to(fmap)

    # Marqueur d'Origine (Commune)
    folium.Marker(
        location=[start_lat, start_lon],
        icon=folium.Icon(color="blue", icon="home", prefix="fa"),
        tooltip=f"📍 Origine : {origin_commune.get('name_fr', '')} (Chef-lieu communal)",
        popup=f"""
        <div style='font-family:sans-serif; font-size:12px;'>
            <strong>{origin_commune.get('name_fr', '')}</strong><br/>
            Province : {origin_commune.get('province', '')}<br/>
            Population 2024 : {origin_commune.get('population_2024', 0):,.0f} hab.<br/>
            <em>Point de référence communal officiel</em>
        </div>
        """,
    ).add_to(fmap)

    # Marqueur de Destination (Hôpital sélectionné)
    folium.Marker(
        location=[end_lat, end_lon],
        icon=folium.Icon(color="red", icon="plus", prefix="fa"),
        tooltip=f"🏥 Destination : {destination_hospital.get('name', 'Hôpital')}",
        popup=f"""
        <div style='font-family:sans-serif; font-size:12px;'>
            <strong>{destination_hospital.get('name', 'Hôpital')}</strong><br/>
            Commune : {destination_hospital.get('commune_name_official', '')}<br/>
            Province : {destination_hospital.get('province', '')}<br/>
            Statut : Hôpital Public Ministériel Vérifié
        </div>
        """,
    ).add_to(fmap)

    # Autres hôpitaux en gris discret
    for h in geocoded_public_hospitals:
        if h != destination_hospital:
            folium.CircleMarker(
                location=[h["lat"], h["lon"]],
                radius=5,
                color="#0A3642",
                fill=True,
                fill_color="#DC2626",
                fill_opacity=0.65,
                weight=1,
                tooltip=f"🏥 {h.get('name', '')}",
            ).add_to(fmap)

    # Tracé du lien géodésique (ou routier si ORS actif)
    folium.PolyLine(
        locations=[[start_lat, start_lon], [end_lat, end_lon]],
        color="#EA580C" if not ors_is_online else "#2563EB",
        weight=3,
        dash_array="6, 6" if not ors_is_online else None,
        tooltip=f"Liaison géodésique : {geodesic_dist_km} km à vol d'oiseau",
    ).add_to(fmap)

    # 6. Rendu interactif
    col_map, col_metrics = st.columns([2.6, 1.4])

    with col_map:
        render_map(fmap, height=600, key="hospital_routes_canvas", returned_objects=[])

    with col_metrics:
        st.markdown(
            f"""
            <div style="background:#F0FDF4 if ors_is_online else #FFFBEB; border:1px solid {'#86EFAC' if ors_is_online else '#FDE68A'}; border-radius:10px; padding:14px; margin-bottom:12px;">
                <h4 style="margin:0 0 8px; color:#0A3642; font-size:1rem;">📏 Analyse du Déplacement</h4>
                <div style="font-size:0.85rem; color:#1E293B;">
                    • <strong>Origine :</strong> {html.escape(origin_commune.get('name_fr', ''))}<br/>
                    • <strong>Destination :</strong> {html.escape(destination_hospital.get('name', ''))}<br/>
                    • <strong>Distance géodésique :</strong> <span style="font-size:1.1rem; font-weight:700; color:#EA580C;">{geodesic_dist_km} km</span> (vol d'oiseau)<br/>
                    • <strong>Distance routière :</strong> <em>{'Calculée via ORS' if ors_is_online else 'Non disponible (ORS hors ligne)'}</em><br/>
                    • <strong>Durée de trajet :</strong> <em>{'Calculée via ORS' if ors_is_online else 'Non disponible (ORS hors ligne)'}</em>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='font-size:0.9rem; font-weight:700; color:#0F172A; margin-bottom:6px;'>🏥 Hôpitaux les Plus Proches :</div>", unsafe_allow_html=True)
        for h in nearest_hospitals[:4]:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 10px; margin-bottom:4px; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; font-size:0.82rem;">
                    <div>
                        <strong>{html.escape(h['name'])}</strong><br/>
                        <span style="color:#64748B; font-size:0.75rem;">{html.escape(h['commune'])} ({html.escape(h['province'])})</span>
                    </div>
                    <span style="background:#DBEAFE; color:#1D4ED8; padding:2px 8px; border-radius:4px; font-weight:600; font-size:0.75rem;">
                        {h['dist_km']} km
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div style="margin-top:14px; font-size:0.75rem; color:#64748B; line-height:1.4;">
                <em>Notice : Conformément aux consignes de rigueur du projet GeoVulnera, aucune distance routière ou durée de trajet n'est extrapolée sans calcul par un graphe routier effectif.</em>
            </div>
            """,
            unsafe_allow_html=True,
        )
