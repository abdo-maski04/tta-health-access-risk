"""Carte Sanitaire et Démographique — Référentiel Sanitaire Consolidé (RSC-TTA).

Visualisation de niveau SIG professionnel de la répartition territoriale des infrastructures de santé
et de la population dans les 146 communes de la région Tanger-Tétouan-Al Hoceïma.
"""

from __future__ import annotations

import html
import folium
from folium.plugins import Fullscreen, MarkerCluster
import streamlit as st
from config.settings import REGION_NAME
from config.theme import COLORS, THEME
from map_utils import (
    BASE_MAP_CONFIGS,
    get_facility_div_icon,
    render_map,
)

# ---------------------------------------------------------------------------
# Définitions des Thématiques Communales, Bins, Couleurs et Légendes
# ---------------------------------------------------------------------------

THEMATIC_METADATA = {
    "Milieu territorial (Commune)": {
        "unit": "Type d'espace",
        "description": "Classification territoriale officielle du Haut-Commissariat au Plan / Ministère",
        "type": "categorical",
        "items": [
            {"label": "Mixte (Urbain / Rural)", "color": "#16A34A", "meaning": "Commune semi-dense à composantes mixtes"},
            {"label": "Rural", "color": "#EA580C", "meaning": "Commune rurale (habitat dispersé / enclavé)"},
            {"label": "Urbain", "color": "#2563EB", "meaning": "Pôle municipal urbain ou arrondissement"},
        ],
    },
    "Population totale (RGPH 2024)": {
        "unit": "Habitants",
        "description": "Recensement Général de la Population et de l'Habitat 2024 (HCP)",
        "type": "sequential",
        "items": [
            {"label": "< 10 000 hab.", "color": "#EFF3FF", "meaning": "Faible population communale"},
            {"label": "10 000 – 25 000", "color": "#BDD7E7", "meaning": "Population modérée"},
            {"label": "25 000 – 50 000", "color": "#6BAED6", "meaning": "Population intermédiaire"},
            {"label": "50 000 – 150 000", "color": "#2171B5", "meaning": "Forte concentration démographique"},
            {"label": "≥ 150 000 hab.", "color": "#08306B", "meaning": "Grand pôle métropolitain"},
        ],
    },
    "Densité de population (hab/km²)": {
        "unit": "hab/km²",
        "description": "Rapport population 2024 sur superficie polygonale WGS84",
        "type": "sequential",
        "items": [
            {"label": "< 50 hab/km²", "color": "#FEEBE2", "meaning": "Très faible densité (zones montagneuses)"},
            {"label": "50 – 100", "color": "#FBB4B9", "meaning": "Densité rurale dispersée"},
            {"label": "100 – 250", "color": "#F768A1", "meaning": "Densité intermédiaire"},
            {"label": "250 – 1 000", "color": "#AE017E", "meaning": "Forte densité périurbaine"},
            {"label": "≥ 1 000 hab/km²", "color": "#7A0177", "meaning": "Très haute densité urbaine"},
        ],
    },
    "Structures de soins primaires (CSU/CSR/DR)": {
        "unit": "Équipements publics",
        "description": "Offre publique de premier recours déclarée au référentiel RSC-TTA",
        "type": "sequential",
        "items": [
            {"label": "0 (Aucune)", "color": "#FEE2E2", "meaning": "Déficit absolu en équipement primaire public"},
            {"label": "1 structure", "color": "#A1D99B", "meaning": "Équipement primaire unique"},
            {"label": "2 structures", "color": "#41AB5D", "meaning": "Doublement du premier niveau"},
            {"label": "3 – 4 structures", "color": "#238B45", "meaning": "Réseau primaire diversifié"},
            {"label": "≥ 5 structures", "color": "#005A32", "meaning": "Maillage primaire dense"},
        ],
    },
    "Taux de soins primaires / 10 000 hab.": {
        "unit": "ESPC / 10k hab.",
        "description": "Rapport entre structures primaires publiques et population communale",
        "type": "sequential",
        "items": [
            {"label": "< 0.50 (Déficit critique)", "color": "#EF4444", "meaning": "Très fort déficit d'accès aux soins de base"},
            {"label": "0.50 – 1.00 (Faible)", "color": "#F59E0B", "meaning": "En-deçà du seuil recommandable de base"},
            {"label": "1.00 – 2.00 (Standard)", "color": "#6BAED6", "meaning": "Dotation conforme aux moyennes régionales"},
            {"label": "2.00 – 3.00 (Bien doté)", "color": "#3182BD", "meaning": "Bonne couverture par habitant"},
            {"label": "≥ 3.00 (Très bien doté)", "color": "#08519C", "meaning": "Couverture territoriale optimale"},
        ],
    },
    "Hôpitaux publics officiels": {
        "unit": "Hôpitaux",
        "description": "Hôpitaux provinciaux, régionaux et de proximité reconnus par le Ministère",
        "type": "sequential",
        "items": [
            {"label": "0 hôpital", "color": "#F1F5F9", "meaning": "Recours au plateau technique externe"},
            {"label": "1 hôpital", "color": "#FCA5A5", "meaning": "Présence d'un hôpital public"},
            {"label": "2 hôpitaux", "color": "#EF4444", "meaning": "Deux centres hospitaliers publics"},
            {"label": "≥ 3 hôpitaux", "color": "#991B1B", "meaning": "Pôle hospitalier régional majeur"},
        ],
    },
    "Pharmacies d'officine": {
        "unit": "Pharmacies",
        "description": "Officines pharmaceutiques privées actives et géolocalisées",
        "type": "sequential",
        "items": [
            {"label": "0 (Désert pharmaceutique)", "color": "#FEE2E2", "meaning": "Aucune officine sur le territoire communal"},
            {"label": "1 – 2 pharmacies", "color": "#D1FAE5", "meaning": "Desserte minimale"},
            {"label": "3 – 10 pharmacies", "color": "#6EE7B7", "meaning": "Desserte locale active"},
            {"label": "11 – 50 pharmacies", "color": "#10B981", "meaning": "Marché pharmaceutique développé"},
            {"label": "> 50 pharmacies", "color": "#047857", "meaning": "Concentration métropolitaine"},
        ],
    },
    "Densité des pharmacies / 10 000 hab.": {
        "unit": "Pharmacies / 10k hab.",
        "description": "Rapport entre pharmacies déclarées et population 2024",
        "type": "sequential",
        "items": [
            {"label": "0.00 / 10k hab.", "color": "#FEE2E2", "meaning": "Absence totale de pharmacie"},
            {"label": "0.01 – 1.00", "color": "#FEF08A", "meaning": "Sous-densité pharmaceutique"},
            {"label": "1.00 – 2.00", "color": "#A7F3D0", "meaning": "Ratio intermédiaire"},
            {"label": "2.00 – 3.00", "color": "#34D399", "meaning": "Bonne disponibilité de proximité"},
            {"label": "≥ 3.00 / 10k hab.", "color": "#059669", "meaning": "Excellente disponibilité pharmaceutique"},
        ],
    },
}


def _get_commune_choropleth_color(row: dict | None, thematic: str) -> str:
    """Détermine la couleur exacte d'une commune selon la thématique active."""
    if not row:
        return "#CBD5E1"

    if thematic == "Milieu territorial (Commune)":
        milieu = str(row.get("milieu", "Rural")).strip().capitalize()
        if milieu == "Mixte":
            return "#16A34A"  # Vert conventionnel
        elif milieu == "Rural":
            return "#EA580C"  # Orange conventionnel
        elif milieu == "Urbain":
            return "#2563EB"  # Bleu conventionnel
        return "#64748B"

    elif thematic == "Population totale (RGPH 2024)":
        val = row.get("population_2024", 0) or 0
        if val >= 150000:
            return "#08306B"
        elif val >= 50000:
            return "#2171B5"
        elif val >= 25000:
            return "#6BAED6"
        elif val >= 10000:
            return "#BDD7E7"
        return "#EFF3FF"

    elif thematic == "Densité de population (hab/km²)":
        val = row.get("densite_hab_km2", 0.0) or 0.0
        if val >= 1000.0:
            return "#7A0177"
        elif val >= 250.0:
            return "#AE017E"
        elif val >= 100.0:
            return "#F768A1"
        elif val >= 50.0:
            return "#FBB4B9"
        return "#FEEBE2"

    elif thematic == "Structures de soins primaires (CSU/CSR/DR)":
        val = row.get("pub_primary_total", 0) or 0
        if val >= 5:
            return "#005A32"
        elif val >= 3:
            return "#238B45"
        elif val >= 2:
            return "#41AB5D"
        elif val >= 1:
            return "#A1D99B"
        return "#FEE2E2"

    elif thematic == "Taux de soins primaires / 10 000 hab.":
        val = row.get("primary_care_per_10k", 0.0) or 0.0
        if val >= 3.0:
            return "#08519C"
        elif val >= 2.0:
            return "#3182BD"
        elif val >= 1.0:
            return "#6BAED6"
        elif val >= 0.5:
            return "#F59E0B"
        return "#EF4444"

    elif thematic == "Hôpitaux publics officiels":
        val = row.get("pub_hospitals", 0) or 0
        if val >= 3:
            return "#991B1B"
        elif val == 2:
            return "#EF4444"
        elif val == 1:
            return "#FCA5A5"
        return "#F1F5F9"

    elif thematic == "Pharmacies d'officine":
        val = row.get("osm_pharmacies_mapped", 0) or 0
        if val > 50:
            return "#047857"
        elif val >= 11:
            return "#10B981"
        elif val >= 3:
            return "#6EE7B7"
        elif val >= 1:
            return "#D1FAE5"
        return "#FEE2E2"

    elif thematic == "Densité des pharmacies / 10 000 hab.":
        val = row.get("pharmacy_per_10k", 0.0) or 0.0
        if val >= 3.0:
            return "#059669"
        elif val >= 2.0:
            return "#34D399"
        elif val >= 1.0:
            return "#A7F3D0"
        elif val > 0.0:
            return "#FEF08A"
        return "#FEE2E2"

    return "#CBD5E1"


def render_health_map(
    communes: list[dict],
    commune_geojson: dict,
    facilities: list[dict],
) -> None:
    """Rendu de la Carte 1 : Carte Sanitaire et Démographique RSC-TTA avec ergonomie SIG avancée."""

    # 1. En-tête Command Center SIG
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0A3642 0%, #0D5C75 60%, #168C91 100%);
                    color: white; border-radius: 12px; padding: 18px 22px; margin-bottom: 16px;
                    box-shadow: 0 4px 16px rgba(10,54,66,0.18);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="background:rgba(255,255,255,0.2); padding:4px 8px; border-radius:6px; font-size:0.8rem; font-weight:700; letter-spacing:0.5px;">SIG CARTOGRAPHIQUE</span>
                        <span style="font-size:0.8rem; color:#CCFBF1;">• RIGA-TTA &amp; RSC-TTA</span>
                    </div>
                    <h2 style="margin:4px 0 0; font-size:1.45rem; font-weight:750; color:#FFFFFF; letter-spacing:-0.3px;">
                        Carte Sanitaire et Démographique Régionale
                    </h2>
                    <p style="margin:3px 0 0; font-size:0.88rem; color:#E0F2FE;">
                        146 Communes · Référentiel Sanitaire Consolidé · Données officielles Ministère 2025 &amp; OSM vérifié
                    </p>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <span style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25); border-radius:20px; padding:5px 12px; font-size:0.8rem; color:#FFFFFF;">
                        ✓ Mode Plein Écran disponible
                    </span>
                    <span style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25); border-radius:20px; padding:5px 12px; font-size:0.8rem; color:#FFFFFF;">
                        ✓ 10 Fonds Cartographiques
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Métriques Régionales Clés (Bandeau KPI)
    total_pop = sum(c.get("population_2024", 0) for c in communes)
    total_public = sum(c.get("pub_total_official", 0) for c in communes)
    total_primary = sum(c.get("pub_primary_total", 0) for c in communes)
    total_hosp_official = sum(c.get("pub_hospitals", 0) for c in communes)
    total_pharm_osm = sum(c.get("osm_pharmacies_mapped", 0) for c in communes)
    total_clinics = sum(1 for f in facilities if f.get("facility_tier") == "PRIVATE_VALID" and f.get("category_code") in ("CLINIC", "DOCTOR", "LABORATORY", "HOSP_OSM_OTHER") and f.get("has_gps"))

    kpi_cols = st.columns(6)
    with kpi_cols[0]:
        st.metric("Population 2024", f"{total_pop:,.0f}".replace(",", " "), help="Recensement Général 2024 (146 communes)")
    with kpi_cols[1]:
        st.metric("Communes", f"{len(communes)}", help="Région Tanger-Tétouan-Al Hoceïma")
    with kpi_cols[2]:
        st.metric("Équipements Publics", f"{total_public}", help="Total des infrastructures du Ministère de la Santé (RSC-TTA)")
    with kpi_cols[3]:
        st.metric("Soins Primaires (ESPC)", f"{total_primary}", help="Centres de santé urbains/ruraux et dispensaires (CSU, CSR, DR)")
    with kpi_cols[4]:
        st.metric("Hôpitaux Publics", f"{total_hosp_official}", help="24 hôpitaux ministériels officiels (16 géocodés ponctuellement)")
    with kpi_cols[5]:
        st.metric("Pharmacies Actives", f"{total_pharm_osm}", help="731 déclarées, dont 722 officines actives géoréférencées")

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # 3. Barre de Commande & Filtres GIS (4 colonnes épurées)
    st.markdown(
        """
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 16px 8px; margin-bottom:12px; box-shadow:0 1px 4px rgba(0,0,0,0.04);">
            <div style="font-weight:700; color:#0A3642; font-size:0.86rem; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">
                ⚙️ Console de Contrôle SIG &amp; Filtres Territoriaux
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_filter_prov, col_filter_comm, col_thematic, col_basemap = st.columns([1.2, 1.5, 1.8, 1.3])

    provinces = sorted({str(c["province"]) for c in communes if c.get("province")})
    with col_filter_prov:
        selected_province = st.selectbox(
            "1. Province / Préfecture :",
            ["Toutes les provinces", *provinces],
            key="health_map_prov_filter",
        )

    # Communes filtrées
    filtered_communes = [
        c for c in communes
        if selected_province == "Toutes les provinces" or c.get("province") == selected_province
    ]
    commune_names = sorted(filtered_communes, key=lambda x: str(x.get("name_fr", "")))
    commune_options = {"Toutes les communes": None}
    for c in commune_names:
        label = f"{c.get('name_fr', '')} ({c.get('commune_code', '')})"
        commune_options[label] = str(c.get("commune_code"))

    with col_filter_comm:
        selected_commune_label = st.selectbox(
            "2. Cibler une commune :",
            list(commune_options.keys()),
            key="health_map_comm_filter",
            help="Sélectionnez une commune pour centrer la carte et afficher sa fiche territoriale détaillée.",
        )
    selected_commune_code = commune_options[selected_commune_label]

    with col_thematic:
        thematic_mode = st.selectbox(
            "3. Thématique communale (Choroplèthe) :",
            list(THEMATIC_METADATA.keys()),
            key="health_map_thematic_mode",
            help="Sélectionnez la variable pour mettre à jour automatiquement les couleurs des polygones et la légende dynamique.",
        )

    # 10 Styles de Fond de Carte
    basemap_options = {
        "CartoDB Positron (Clair Professionnel)": "light",
        "CartoDB Voyager (Élégant)": "voyager",
        "OpenStreetMap (Standard SIG)": "standard",
        "OpenTopoMap (Relief & Courbes)": "terrain",
        "Esri World Street Map (Routier)": "esri_street",
        "Esri World Topo Map (Topographique)": "esri_topo",
        "Esri World Imagery (Satellite HD)": "satellite",
        "Esri Satellite Hybride (Labels)": "hybrid",
        "CartoDB Dark Matter (Sombre High-Tech)": "dark",
        "Fond Gris Neutre (Analytique)": "neutral_gray",
    }

    with col_basemap:
        selected_basemap_label = st.selectbox(
            "4. Fond de carte (10 styles) :",
            list(basemap_options.keys()),
            key="health_map_basemap_select",
        )
    selected_basemap_key = basemap_options[selected_basemap_label]

    # 4. Filtres de Couches d'Établissements (Layers On/Off)
    st.markdown("<div style='font-size:0.83rem; font-weight:700; color:#334155; margin-bottom:4px; text-transform:uppercase;'>Couches d'Établissements Sanitaires :</div>", unsafe_allow_html=True)
    layer_cols = st.columns(4)
    with layer_cols[0]:
        show_layer_a = st.checkbox("🔴 Hôpitaux Publics (16)", value=True, key="hm_layer_a", help="Plateau hospitalier de référence géolocalisé")
    with layer_cols[1]:
        show_layer_b = st.checkbox("🟢 Pharmacies Validées (722)", value=True, key="hm_layer_b", help="Officines pharmaceutiques privées actives")
    with layer_cols[2]:
        show_layer_c = st.checkbox(f"🟣 Cliniques & Spécialisés ({total_clinics})", value=True, key="hm_layer_c", help="Cliniques privées, cabinets et laboratoires d'analyse")
    with layer_cols[3]:
        show_layer_d = st.checkbox("⚪ Quarantaine / Non homologué (41)", value=False, key="hm_layer_d", help="Structures OSM en attente de validation officielle")

    # 5. Légende Thématique Dynamique (mise à jour instantanée)
    meta = THEMATIC_METADATA.get(thematic_mode, THEMATIC_METADATA["Milieu territorial (Commune)"])
    items = meta["items"]

    legend_items_html = "".join([
        f"""
        <div style="display:flex; align-items:center; gap:6px; margin-right:14px; margin-bottom:4px; font-size:0.8rem;">
            <span style="display:inline-block; width:14px; height:14px; border-radius:3px; background:{item['color']}; border:1px solid rgba(0,0,0,0.15); flex-shrink:0;"></span>
            <span style="color:#0F172A; font-weight:600;">{html.escape(item['label'])}</span>
            <span style="color:#64748B; font-size:0.75rem;">({html.escape(item['meaning'])})</span>
        </div>
        """
        for item in items
    ])

    st.markdown(
        f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid #0D5C75; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
                <div style="font-weight:700; color:#0A3642; font-size:0.88rem;">
                    📊 Légende Thématique : <span style="color:#0D5C75;">{html.escape(thematic_mode)}</span>
                </div>
                <div style="font-size:0.78rem; color:#475569; background:#E2E8F0; padding:2px 8px; border-radius:4px;">
                    Unité : <strong>{html.escape(meta['unit'])}</strong> · {html.escape(meta['description'])}
                </div>
            </div>
            <div style="display:flex; flex-wrap:wrap; align-items:center; gap:4px;">
                {legend_items_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 6. Filtrage rigoureux des infrastructures (aucun faux GPS synthétique)
    valid_master_facilities = [
        f for f in facilities
        if f.get("has_gps") is True
        and f.get("validation_status") not in ("OUTSIDE_REGION_TERRITORY", "RECONCILED_PUBLIC_DUPLICATE")
    ]

    if selected_commune_code:
        valid_master_facilities = [f for f in valid_master_facilities if str(f.get("commune_code")) == selected_commune_code]
    elif selected_province != "Toutes les provinces":
        prov_codes = {str(c["commune_code"]) for c in filtered_communes}
        valid_master_facilities = [f for f in valid_master_facilities if str(f.get("commune_code")) in prov_codes]

    # 7. Création de la Carte Folium avec les fonds configurés
    cfg = BASE_MAP_CONFIGS.get(selected_basemap_key, BASE_MAP_CONFIGS["light"])

    # Centrage dynamique
    if selected_commune_code:
        target_comm = next((c for c in communes if str(c.get("commune_code")) == selected_commune_code), None)
        if target_comm and target_comm.get("centroid_lat") and target_comm.get("centroid_lon"):
            center_loc = [target_comm["centroid_lat"], target_comm["centroid_lon"]]
            zoom_lvl = 11
        else:
            center_loc = [35.25, -5.35]
            zoom_lvl = 8
    else:
        center_loc = [35.25, -5.35]
        zoom_lvl = 8

    fmap = folium.Map(
        location=center_loc,
        zoom_start=zoom_lvl,
        tiles=None,
        control_scale=True,
    )

    # Ajout du fond principal sélectionné
    folium.TileLayer(
        tiles=str(cfg["tiles"]),
        name=str(cfg["name"]),
        attr=str(cfg["attr"]),
        subdomains=str(cfg.get("subdomains", "abc")),
        max_zoom=int(cfg.get("max_zoom", 19)),
        control=False,
    ).add_to(fmap)

    # Si satellite hybride, ajouter les étiquettes et frontières
    if selected_basemap_key == "hybrid":
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            name="Étiquettes & Frontières",
            attr="Labels &copy; Esri",
            overlay=True,
            control=False,
            max_zoom=19,
        ).add_to(fmap)

    # Contrôle Plein Écran Natif Folium
    Fullscreen(
        position="topleft",
        title="Passer en plein écran SIG",
        title_cancel="Quitter le plein écran",
        force_separate_button=True,
    ).add_to(fmap)

    # 8. Couche GeoJSON Communale (Choroplèthe dynamique)
    commune_data_by_code = {str(c["commune_code"]): c for c in communes}

    def style_fn(feature):
        code = str(feature.get("properties", {}).get("commune_code", "")).strip()
        is_highlighted = (code == selected_commune_code)
        row = commune_data_by_code.get(code)
        fill = _get_commune_choropleth_color(row, thematic_mode)
        return {
            "fillColor": fill,
            "fillOpacity": 0.72 if not is_highlighted else 0.90,
            "color": "#0F172A" if is_highlighted else "#334155",
            "weight": 3.5 if is_highlighted else 1.2,
            "opacity": 0.95,
        }

    folium.GeoJson(
        commune_geojson,
        name="Communes (Profil Sanitaire)",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["name_fr", "commune_code", "province", "population_2024"],
            aliases=["Commune :", "Code :", "Province :", "Population 2024 :"],
            localize=True,
            sticky=True,
        ),
    ).add_to(fmap)

    # 9. Couches d'Infrastructures avec Badges SVG et Smart Clusters

    # A. Hôpitaux Publics (Non regroupés pour rester toujours visibles en haute priorité)
    if show_layer_a:
        layer_a_group = folium.FeatureGroup(name="🔴 Hôpitaux Publics Officiels (16)")
        hosp_pts = [
            f for f in valid_master_facilities
            if f.get("facility_tier") == "PUBLIC_CORE"
            and f.get("validation_status") == "OFFICIAL_MINISTRY"
            and f.get("lat") and f.get("lon")
        ]
        for p in hosp_pts:
            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=get_facility_div_icon("pub_hospital", size=30),
                tooltip=f"🏥 <strong>{html.escape(p.get('name', 'Hôpital Public'))}</strong><br/>{html.escape(p.get('commune_name_official', ''))} ({html.escape(p.get('province', ''))})<br/>Statut : Ministère de la Santé",
                popup=folium.Popup(
                    f"""
                    <div style='font-family:Segoe UI, sans-serif; font-size:12px; min-width:220px; line-height:1.4;'>
                        <div style='background:#DC2626; color:white; padding:6px 10px; border-radius:6px; font-weight:700; font-size:13px; margin-bottom:8px;'>
                            🏥 {html.escape(p.get('name', 'Hôpital Public'))}
                        </div>
                        <p style='margin:0 0 3px;'><strong>Type :</strong> Hôpital Public de Référence</p>
                        <p style='margin:0 0 3px;'><strong>Commune :</strong> {html.escape(p.get('commune_name_official', 'N/A'))}</p>
                        <p style='margin:0 0 3px;'><strong>Province :</strong> {html.escape(p.get('province', 'N/A'))}</p>
                        <p style='margin:0 0 3px;'><strong>Source :</strong> Ministère de la Santé (RSC-TTA)</p>
                        <p style='margin:0; font-size:11px; color:#64748B;'><strong>GPS :</strong> {p['lat']:.5f}, {p['lon']:.5f}</p>
                    </div>
                    """,
                    max_width=300,
                ),
            ).add_to(layer_a_group)
        layer_a_group.add_to(fmap)

    # B. Pharmacies Privées Validées (Cluster intelligent avec zoom progressif)
    if show_layer_b:
        cluster_b = MarkerCluster(
            name="🟢 Pharmacies Validées (722)",
            options={
                "maxClusterRadius": 35,
                "spiderfyOnMaxZoom": True,
                "disableClusteringAtZoom": 13,
                "showCoverageOnHover": False,
            },
        )
        pharm_pts = [
            f for f in valid_master_facilities
            if f.get("category_code") == "PHARMACY"
            and f.get("validation_status") == "OSM_MAPPED_ACTIVE"
            and f.get("lat") and f.get("lon")
        ]
        for p in pharm_pts:
            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=get_facility_div_icon("pharmacy", size=24),
                tooltip=f"💊 <strong>{html.escape(p.get('name', 'Pharmacie'))}</strong><br/>{html.escape(p.get('commune_name_official', ''))}",
                popup=folium.Popup(
                    f"""
                    <div style='font-family:Segoe UI, sans-serif; font-size:12px; min-width:200px;'>
                        <strong style='color:#16A34A; font-size:13px;'>💊 {html.escape(p.get('name', 'Pharmacie'))}</strong><br/>
                        <span>Pharmacie d'officine privée</span><br/>
                        <span><strong>Commune :</strong> {html.escape(p.get('commune_name_official', ''))}</span><br/>
                        <span style='font-size:11px; color:#64748B;'>Coordonnées : {p['lat']:.5f}, {p['lon']:.5f}</span>
                    </div>
                    """,
                    max_width=260,
                ),
            ).add_to(cluster_b)
        cluster_b.add_to(fmap)

    # C. Offre Privée Spécialisée & Cliniques (Cluster intelligent avec zoom progressif)
    if show_layer_c:
        cluster_c = MarkerCluster(
            name=f"🟣 Cliniques & Spécialisés ({total_clinics})",
            options={
                "maxClusterRadius": 35,
                "spiderfyOnMaxZoom": True,
                "disableClusteringAtZoom": 13,
                "showCoverageOnHover": False,
            },
        )
        clinic_pts = [
            f for f in valid_master_facilities
            if f.get("facility_tier") == "PRIVATE_VALID"
            and f.get("category_code") in ("CLINIC", "DOCTOR", "LABORATORY", "HOSP_OSM_OTHER")
            and f.get("lat") and f.get("lon")
        ]
        has_rif_node = any(str(p.get("facility_id", "")).endswith("1596542299") for p in clinic_pts)
        for p in clinic_pts:
            if has_rif_node and "150999396" in str(p.get("facility_id", "")):
                continue

            cat = str(p.get("category_code", ""))
            if cat == "DOCTOR":
                icon_key = "doctor"
                cat_desc = "Cabinet Médical"
            elif cat == "LABORATORY":
                icon_key = "laboratory"
                cat_desc = "Laboratoire d'Analyses"
            elif cat == "CLINIC":
                icon_key = "clinic"
                cat_desc = "Clinique Privée"
            else:
                icon_key = "other"
                cat_desc = p.get("facility_category_label", "Établissement Spécialisé")

            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=get_facility_div_icon(icon_key, size=26),
                tooltip=f"<strong>{html.escape(p.get('name', cat_desc))}</strong><br/>{html.escape(cat_desc)} · {html.escape(p.get('commune_name_official', ''))}",
                popup=folium.Popup(
                    f"""
                    <div style='font-family:Segoe UI, sans-serif; font-size:12px; min-width:210px;'>
                        <strong style='color:#7C3AED; font-size:13px;'>{html.escape(p.get('name', 'Structure'))}</strong><br/>
                        <span><strong>Catégorie :</strong> {html.escape(cat_desc)}</span><br/>
                        <span><strong>Commune :</strong> {html.escape(p.get('commune_name_official', ''))}</span><br/>
                        <span><strong>Statut :</strong> Secteur Privé Homologué</span><br/>
                        <span style='font-size:11px; color:#64748B;'>GPS : {p['lat']:.5f}, {p['lon']:.5f}</span>
                    </div>
                    """,
                    max_width=280,
                ),
            ).add_to(cluster_c)
        cluster_c.add_to(fmap)

    # D. Structures Quarantaine (Cluster masqué par défaut)
    if show_layer_d:
        cluster_d = MarkerCluster(
            name="⚪ Structures en Quarantaine (41)",
            options={
                "maxClusterRadius": 35,
                "spiderfyOnMaxZoom": True,
                "disableClusteringAtZoom": 13,
            },
        )
        unverified_pts = [
            f for f in valid_master_facilities
            if f.get("facility_tier") == "UNVERIFIED"
            and f.get("lat") and f.get("lon")
        ]
        for p in unverified_pts:
            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=get_facility_div_icon("unverified", size=22),
                tooltip=f"⚪ {html.escape(p.get('name', 'Structure non homologuée'))} (Quarantaine)",
            ).add_to(cluster_d)
        cluster_d.add_to(fmap)

    folium.LayerControl(position="topright", collapsed=True).add_to(fmap)

    # 10. Rendu Visuel : Carte et Fiche Territoriale
    map_container, inspector_container = st.columns([2.8, 1.2])

    with map_container:
        render_map(fmap, height=640, key="health_map_interactive_canvas", returned_objects=[])

        # Barre des Symboles Cartographiques
        st.markdown(
            """
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:8px 12px; margin-top:8px; display:flex; flex-wrap:wrap; align-items:center; gap:16px; font-size:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                <span style="font-weight:700; color:#0A3642;">Symboles Cartographiques :</span>
                <span style="display:flex; align-items:center; gap:6px;">
                    <span style="display:inline-block; width:14px; height:14px; border-radius:50%; background:#DC2626; border:1.5px solid #FFFFFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
                    <strong>Hôpital Public</strong> (Ministère)
                </span>
                <span style="display:flex; align-items:center; gap:6px;">
                    <span style="display:inline-block; width:14px; height:14px; border-radius:50%; background:#16A34A; border:1.5px solid #FFFFFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
                    <strong>Pharmacie</strong> (Active)
                </span>
                <span style="display:flex; align-items:center; gap:6px;">
                    <span style="display:inline-block; width:14px; height:14px; border-radius:50%; background:#7C3AED; border:1.5px solid #FFFFFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
                    <strong>Clinique Privée</strong>
                </span>
                <span style="display:flex; align-items:center; gap:6px;">
                    <span style="display:inline-block; width:14px; height:14px; border-radius:50%; background:#2563EB; border:1.5px solid #FFFFFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
                    <strong>Cabinet Médical</strong>
                </span>
                <span style="display:flex; align-items:center; gap:6px;">
                    <span style="display:inline-block; width:14px; height:14px; border-radius:50%; background:#DB2777; border:1.5px solid #FFFFFF; box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
                    <strong>Laboratoire</strong>
                </span>
                <span style="color:#64748B; font-size:0.75rem;">
                    * Clusters automatiques avec déploiement progressif au zoom ≥ 13
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 11. Panneau Inspecteur : Fiche Territoriale Sanitaire
    with inspector_container:
        st.markdown(
            """
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px; margin-bottom:12px; box-shadow:0 2px 8px rgba(0,0,0,0.05);">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; border-bottom:1px solid #F1F5F9; padding-bottom:8px;">
                    <h4 style="margin:0; color:#0A3642; font-size:1.02rem; font-weight:750;">📋 Fiche Territoriale Sanitaire</h4>
                    <span style="background:#E0F2FE; color:#0369A1; padding:2px 8px; border-radius:12px; font-size:0.72rem; font-weight:600;">RSC-TTA 2025</span>
                </div>
            """,
            unsafe_allow_html=True,
        )

        target_code = selected_commune_code or (communes[0]["commune_code"] if communes else None)
        selected_row = next((c for c in communes if str(c.get("commune_code")) == str(target_code)), None)

        if selected_row:
            c_name = selected_row.get("name_fr", "Commune")
            c_code = selected_row.get("commune_code", "")
            c_prov = selected_row.get("province", "")
            c_milieu = selected_row.get("milieu", "Rural")
            c_pop = selected_row.get("population_2024", 0)
            c_csu = selected_row.get("pub_csu", 0)
            c_csr = selected_row.get("pub_csr", 0)
            c_csr2 = selected_row.get("pub_csr2_maternite", 0)
            c_dr = selected_row.get("pub_dr", 0)
            c_hosp = selected_row.get("pub_hospitals", 0)
            c_pharm = selected_row.get("osm_pharmacies_mapped", 0)
            c_primary = selected_row.get("pub_primary_total", 0)
            c_ratio_prim = selected_row.get("primary_care_per_10k", 0.0)
            c_ratio_pharm = selected_row.get("pharmacy_per_10k", 0.0)
            c_absent = selected_row.get("is_public_healthcare_absent", False)

            milieu_badge = "#2563EB" if c_milieu == "Urbain" else ("#16A34A" if c_milieu == "Mixte" else "#EA580C")

            st.markdown(
                f"""
                <div style="font-weight:750; font-size:1.18rem; color:#0F172A; line-height:1.2;">{html.escape(c_name)}</div>
                <div style="font-size:0.83rem; color:#64748B; margin-top:2px; margin-bottom:10px;">
                    Code HCP : <strong>{c_code}</strong> · {html.escape(c_prov)} · 
                    <span style="background:{milieu_badge}; color:white; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:600;">{c_milieu}</span>
                </div>

                <div style="background:#F8FAFC; border-radius:8px; padding:10px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.84rem;">
                        <span style="color:#475569;">Population RGPH 2024 :</span>
                        <strong style="color:#0F172A;">{c_pop:,.0f} hab.</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.84rem;">
                        <span style="color:#475569;">Soins Primaires Publics (ESPC) :</span>
                        <strong style="color:#0D5C75;">{c_primary}</strong>
                    </div>
                    <div style="padding-left:8px; font-size:0.79rem; color:#64748B; border-left:2px solid #CBD5E1; margin:4px 0;">
                        • CSU (Urbain) : <strong>{c_csu}</strong><br/>
                        • CSR (Rural) : <strong>{c_csr}</strong> (dont {c_csr2} CSR-2 avec maternité)<br/>
                        • Dispensaires Ruraux (DR) : <strong>{c_dr}</strong>
                    </div>
                </div>

                <div style="background:#F8FAFC; border-radius:8px; padding:10px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.84rem;">
                        <span style="color:#475569;">Hôpitaux Publics :</span>
                        <strong style="color:#DC2626;">{c_hosp}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.84rem;">
                        <span style="color:#475569;">Pharmacies Actives Déclarées :</span>
                        <strong style="color:#16A34A;">{c_pharm}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.84rem;">
                        <span style="color:#475569;">Taux Primaire / 10k hab. :</span>
                        <strong style="color:{'#DC2626' if c_ratio_prim < 1.0 else '#059669'};">{c_ratio_prim:.2f}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.84rem;">
                        <span style="color:#475569;">Densité Pharmacies / 10k hab. :</span>
                        <strong style="color:#0F172A;">{c_ratio_pharm:.2f}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if c_absent:
                st.warning("⚠️ **Alerte Sanitaire :** Commune sans infrastructure de soins de santé primaire publique déclarée.")

            # Structures rurales officielles non géocodées ponctuellement
            rural_no_gps = [
                f for f in facilities
                if str(f.get("commune_code")) == str(c_code)
                and f.get("facility_tier") == "PUBLIC_CORE"
                and f.get("has_gps") is False
            ]
            if rural_no_gps:
                st.markdown(
                    f"""
                    <div style="background:#FEF3C7; border:1px solid #FCD34D; border-left:4px solid #D97706; border-radius:8px; padding:10px; font-size:0.8rem; color:#92400E; margin-top:8px;">
                        <div style="font-weight:700; margin-bottom:4px; display:flex; align-items:center; gap:4px;">
                            <span>📍</span> Structures Publiques Rattachées ({len(rural_no_gps)})
                        </div>
                        <div style="line-height:1.4;">
                            {'<br/>• '.join(html.escape(f.get('name', 'Structure')) for f in rural_no_gps[:5])}
                            {f'<br/>...et {len(rural_no_gps) - 5} autres' if len(rural_no_gps) > 5 else ''}
                        </div>
                        <div style="margin-top:6px; font-size:0.74rem; color:#78350F; font-style:italic;">
                            * Comptabilisées au niveau communal selon le référentiel officiel ministériel, sans injection de faux points GPS synthétiques.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Sélectionnez une commune pour examiner son profil.")

        st.markdown("</div>", unsafe_allow_html=True)
