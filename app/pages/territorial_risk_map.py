"""Carte du Risque et de la Vulnérabilité Territoriale — GeoVulnera TTA.

Visualisation des dimensions de vulnérabilité sanitaire, d'exposition démographique
et de sensibilité climatique par commune, sans score composite artificiel prématuré.
"""

from __future__ import annotations

import html

import folium
import streamlit as st
from folium.plugins import Fullscreen
from map_utils import render_map


def render_territorial_risk_map(
    communes: list[dict],
    commune_geojson: dict,
    facilities: list[dict],
) -> None:
    """Rendu de la Carte 2 : Risque et Vulnérabilité Territoriale."""

    # 1. En-tête et cadre de rigueur méthodologique
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #7C2D12 0%, #B45309 100%);
                    color: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
                    box-shadow: 0 4px 12px rgba(180,83,9,0.15);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <h2 style="margin:0; font-size:1.4rem; font-weight:700; color:#FFFFFF;">
                        ⚠️ Carte de la Vulnérabilité et du Risque Territorial
                    </h2>
                    <p style="margin:4px 0 0; font-size:0.9rem; color:#FEF3C7;">
                        Analyse multi-dimensionnelle de l'exposition démographique et de l'accès aux soins
                    </p>
                </div>
                <div style="background:rgba(255,255,255,0.15); padding:6px 14px; border-radius:20px; font-size:0.82rem; border:1px solid rgba(255,255,255,0.25);">
                    Indépendante de la Carte Sanitaire
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Avertissement scientifique sur le score composite
    st.info(
        "🔬 **Rigueur Méthodologique GeoVulnera :** Le score composite global unifié (croisant aléas climatiques extrêmes, "
        "temps de trajet routiers ORS et vulnérabilités sanitaires) est actuellement en cours de calibration par l'équipe de recherche. "
        "Conformément aux normes d'intégrité scientifique du projet, aucun score prématuré ni poids artificiel n'est simulé. "
        "Cette carte représente les dimensions de vulnérabilité objectives vérifiées."
    )

    # 3. Contrôles et Filtres
    col_dim, col_prov, col_crit = st.columns([1.6, 1.2, 1.2])

    with col_dim:
        risk_dimension = st.selectbox(
            "Dimension territoriale analysée :",
            [
                "1. Vulnérabilité d'accès sanitaire (Déficit primaire / Isolement)",
                "2. Exposition démographique (Population & Part rurale)",
                "3. Typologie de vulnérabilité sanitaire territoriale",
                "4. Sensibilité climatique (Cadre des seuils Open-Meteo)",
            ],
            key="risk_map_dimension_select",
        )

    provinces = sorted({str(c["province"]) for c in communes if c.get("province")})
    with col_prov:
        selected_province = st.selectbox(
            "Filtrer par Province :",
            ["Toutes les provinces", *provinces],
            key="risk_map_province_select",
        )

    with col_crit:
        priority_only = st.checkbox(
            "Communes prioritaires uniquement",
            value=False,
            help="Met en surbrillance les communes sans infrastructure publique ou sous le seuil primaire critique",
            key="risk_map_priority_toggle",
        )

    # 4. Données et calculs de classification
    commune_data_by_code = {str(c["commune_code"]): c for c in communes}

    # Identification des communes à priorité critique
    critical_communes = [
        c
        for c in communes
        if c.get("is_public_healthcare_absent") or c.get("primary_care_per_10k", 0.0) < 1.0
    ]

    # Définition des couleurs selon la dimension
    def get_risk_fill_color(code: str) -> str:
        row = commune_data_by_code.get(code)
        if not row:
            return "#E2E8F0"

        if selected_province != "Toutes les provinces" and row.get("province") != selected_province:
            return "#F1F5F9"

        if "1. Vulnérabilité d'accès sanitaire" in risk_dimension:
            if row.get("is_public_healthcare_absent"):
                return "#B91C1C"  # Rouge sombre : Alerte critique
            ratio = row.get("primary_care_per_10k", 0.0)
            if ratio < 0.5:
                return "#EA580C"  # Orange vif : Très faible
            elif ratio < 1.0:
                return "#F59E0B"  # Ambre : Faible
            elif ratio < 2.0:
                return "#10B981"  # Vert clair : Modéré
            else:
                return "#047857"  # Vert foncé : Bon équipement

        elif "2. Exposition démographique" in risk_dimension:
            rural_pct = row.get("part_rurale_pct", 0.0)
            pop = row.get("population_2024", 0)
            if rural_pct >= 90.0 and pop > 15000:
                return "#9A3412"  # Fortement rural et populeux
            elif rural_pct >= 70.0:
                return "#C2410C"
            elif rural_pct >= 40.0:
                return "#EA580C"
            else:
                return "#38BDF8"  # Urbain / Périurbain

        elif "3. Typologie de vulnérabilité sanitaire" in risk_dimension:
            # Classification objective à 4 niveaux
            is_absent = row.get("is_public_healthcare_absent", False)
            hosp = row.get("pub_hospitals", 0)
            csr2 = row.get("pub_csr2_maternite", 0)
            ratio = row.get("primary_care_per_10k", 0.0)

            if is_absent:
                return "#DC2626"  # Niveau 4 : Isolement sanitaire total
            elif hosp > 0:
                return "#1D4ED8"  # Niveau 1 : Pôle hospitalier central
            elif csr2 > 0 and ratio >= 1.0:
                return "#059669"  # Niveau 2 : Réseau rural consolidé
            else:
                return "#D97706"  # Niveau 3 : Réseau rural fragile (dispensaire seul ou ratio < 1)

        else:  # Sensibilité climatique
            # Présentation de l'exposition selon le milieu et le relief
            milieu = row.get("milieu", "Rural")
            if milieu == "Rural":
                return "#B45309"
            elif milieu == "Mixte":
                return "#D97706"
            else:
                return "#0D9488"

    def risk_style_fn(feature):
        code = str(feature.get("properties", {}).get("commune_code", "")).strip()
        row = commune_data_by_code.get(code, {})
        is_crit = (
            row.get("is_public_healthcare_absent") or row.get("primary_care_per_10k", 0.0) < 1.0
        )

        stroke_color = "#991B1B" if (priority_only and is_crit) else "#334155"
        stroke_weight = 2.5 if (priority_only and is_crit) else 1
        return {
            "fillColor": get_risk_fill_color(code),
            "fillOpacity": 0.72,
            "color": stroke_color,
            "weight": stroke_weight,
            "opacity": 0.9,
        }

    # 5. Création de la carte Folium
    fmap = folium.Map(
        location=[35.25, -5.35],
        zoom_start=8,
        tiles=None,
        control_scale=True,
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="&copy; OpenStreetMap contributors &copy; CARTO",
        subdomains="abcd",
        max_zoom=20,
        control=False,
    ).add_to(fmap)

    Fullscreen(
        position="topleft",
        title="Passer en plein écran SIG",
        title_cancel="Quitter le plein écran",
        force_separate_button=True,
    ).add_to(fmap)

    folium.GeoJson(
        commune_geojson,
        name="Vulnérabilité Territoriale",
        style_function=risk_style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["name_fr", "commune_code", "province", "population_2024"],
            aliases=["Commune :", "Code :", "Province :", "Population :"],
            localize=True,
        ),
    ).add_to(fmap)

    # 6. Rendu interactif
    col_map, col_details = st.columns([2.8, 1.2])

    with col_map:
        render_map(fmap, height=600, key="territorial_risk_map_canvas", returned_objects=[])

    with col_details:
        st.markdown(
            f"""
            <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:12px; margin-bottom:12px;">
                <h4 style="margin:0 0 6px; color:#92400E; font-size:0.95rem;">📊 Synthèse de Vulnérabilité</h4>
                <div style="font-size:0.85rem; color:#78350F;">
                    • <strong>Communes analysées :</strong> {len(communes)}<br/>
                    • <strong>Communes sans structure publique :</strong> {sum(1 for c in communes if c.get("is_public_healthcare_absent"))}<br/>
                    • <strong>Taux primaire critique (&lt;1/10k) :</strong> {sum(1 for c in communes if c.get("primary_care_per_10k", 0.0) < 1.0)}<br/>
                    • <strong>Communes rurales isolées :</strong> {sum(1 for c in communes if c.get("milieu") == "Rural" and c.get("pub_hospitals", 0) == 0)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='font-size:0.9rem; font-weight:700; color:#0F172A; margin-bottom:6px;'>🚨 Communes en Situation de Fragilité :</div>",
            unsafe_allow_html=True,
        )

        display_critical = [
            c
            for c in critical_communes
            if selected_province == "Toutes les provinces" or c.get("province") == selected_province
        ]

        if display_critical:
            for c in display_critical[:8]:
                c_nom = c.get("name_fr", "")
                c_prov = c.get("province", "")
                c_ratio = c.get("primary_care_per_10k", 0.0)
                is_abs = c.get("is_public_healthcare_absent", False)
                stat_tag = "Zéro structure" if is_abs else f"{c_ratio:.2f} / 10k"
                tag_bg = "#EF4444" if is_abs else "#F59E0B"
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 8px; margin-bottom:4px; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; font-size:0.8rem;">
                        <div>
                            <strong>{html.escape(c_nom)}</strong> ({html.escape(c_prov)})
                        </div>
                        <span style="background:{tag_bg}; color:white; padding:1px 6px; border-radius:4px; font-weight:600; font-size:0.75rem;">
                            {stat_tag}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            if len(display_critical) > 8:
                st.caption(
                    f"...et {len(display_critical) - 8} autres communes dans cette province."
                )
        else:
            st.success("Aucune commune sous seuil critique dans la province sélectionnée.")

        st.markdown(
            """
            <div style="margin-top:12px; font-size:0.75rem; color:#64748B; line-height:1.4;">
                <em>Source : Ministère de la Santé (2025), RGPH 2024. Aléas calculés par Open-Meteo.</em>
            </div>
            """,
            unsafe_allow_html=True,
        )
