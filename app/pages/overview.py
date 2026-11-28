"""Overview Dashboard layout and interactive regional map."""

from __future__ import annotations

import csv
import math
from collections import Counter
from io import StringIO

import streamlit as st
from components.chart_card import chart_card
from components.filter_panel import multiselect_filter
from components.header import page_header
from components.kpi_card import kpi_row
from components.sidebar import DASHBOARDS, NAVIGATION_ICONS
from components.source_info import source_info
from components.states import empty_state
from components.table_card import table_card
from config.settings import REGION_NAME
from config.theme import COLORS
from map_utils import (
    build_commune_layer,
    build_facility_layer,
    build_legend,
    build_unassigned_facility_layer,
    get_initial_map,
    render_map,
)
from visualization.overview_charts import (
    associated_facilities_by_province,
    demographic_evolution,
    empty_figure,
    facilities_by_type,
    milieu_donut,
    population_by_province,
    population_top_bottom,
    urban_rural_by_province,
)

REGION_OPTION = "Région TTA"
OVERVIEW_MILIEU_COLORS = COLORS["overview_milieu"]


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _sum_field(rows: list[dict], field: str) -> float | int | None:
    values = [row.get(field) for row in rows]
    if not values or any(not _is_number(value) for value in values):
        return None
    return sum(values)


def _format_number(value: object, decimals: int = 0) -> str:
    if not _is_number(value):
        return "Non disponible"
    return f"{value:,.{decimals}f}".replace(",", " ")


def available_population_years(communes: list[dict]) -> list[int]:
    if not communes:
        return []
    common_fields = set.intersection(*(set(row) for row in communes))
    years = []
    for field in common_fields:
        year_text = field.removeprefix("population_")
        if field.startswith("population_") and year_text.isdigit():
            if all(_is_number(row.get(field)) for row in communes):
                years.append(int(year_text))
    return sorted(years)


def filter_overview_communes(
    communes: list[dict],
    provinces: list[str] | None = None,
    milieux: list[str] | None = None,
    search: str = "",
) -> list[dict]:
    """Apply territorial filters without modifying source data."""
    needle = search.strip().casefold()
    province_set = set(provinces or [])
    milieu_set = set(milieux or [])
    return [
        row
        for row in communes
        if (not province_set or row["province"] in province_set)
        and (not milieu_set or row["milieu"] in milieu_set)
        and (
            not needle
            or needle in str(row["name_fr"]).casefold()
            or needle in str(row["name_ar"]).casefold()
            or needle in str(row["commune_code"]).casefold()
        )
    ]


def build_provincial_summary(
    communes: list[dict],
    facilities: list[dict],
    population_year: int | None = 2024,
) -> list[dict]:
    """Aggregate commune populations and verified facility associations."""
    population_label = (
        f"Population {population_year}" if population_year is not None else "Population"
    )
    rows = []
    for province in sorted({row["province"] for row in communes}):
        province_communes = [row for row in communes if row["province"] == province]
        commune_codes = {str(row["commune_code"]) for row in province_communes}
        total_area = _sum_field(province_communes, "area_km2")
        pop_year = (
            _sum_field(province_communes, f"population_{population_year}")
            if population_year is not None
            else None
        )
        density = (
            round(pop_year / total_area, 1)
            if pop_year is not None and total_area is not None and total_area > 0
            else None
        )
        rows.append(
            {
                "Province": province,
                "Communes": len(province_communes),
                population_label: pop_year,
                "Population urbaine 2024": _sum_field(province_communes, "population_urbaine_2024"),
                "Population rurale 2024": _sum_field(province_communes, "population_rurale_2024"),
                "Établissements associés": sum(
                    row.get("commune_code") is not None
                    and str(row["commune_code"]) in commune_codes
                    for row in facilities
                ),
                "Densité (hab/km²)": density,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row[population_label] is not None,
            row[population_label] if row[population_label] is not None else 0,
        ),
        reverse=True,
    )


def _reset_overview_filters() -> None:
    st.session_state["overview_search"] = ""
    st.session_state["overview_territory"] = REGION_OPTION
    st.session_state["overview_year"] = st.session_state.get("overview_latest_year", 2024)
    st.session_state["overview_milieu"] = []


def _navigate_to_ranking() -> None:
    ranking_label = dict(DASHBOARDS)["Commune Ranking"]
    st.session_state["selected_page"] = "Commune Ranking"
    st.session_state["sidebar_navigation_radio"] = (
        f"{NAVIGATION_ICONS['Commune Ranking']}  {ranking_label}"
    )


def _build_map(
    communes: list[dict],
    geojson: dict,
    facilities: list[dict],
    show_unassigned: bool,
):
    import folium

    folium_map = get_initial_map()
    associated = [row for row in facilities if row.get("commune_code") is not None]
    build_commune_layer(
        communes,
        geojson,
        folium_map,
        facilities=associated,
        milieu_colors=OVERVIEW_MILIEU_COLORS,
    )
    build_facility_layer(associated, folium_map, color_by_type=False)
    if show_unassigned:
        build_unassigned_facility_layer(facilities, folium_map)
    unassigned_count = sum(row.get("commune_code") is None for row in facilities)
    folium_map.add_child(
        build_legend(
            unassigned_count if show_unassigned else 0,
            milieu_colors=OVERVIEW_MILIEU_COLORS,
        )
    )
    folium.LayerControl(position="topright", collapsed=True).add_to(folium_map)
    folium_map.fit_bounds(
        [
            [
                min(row["centroid_lat"] for row in communes),
                min(row["centroid_lon"] for row in communes),
            ],
            [
                max(row["centroid_lat"] for row in communes),
                max(row["centroid_lon"] for row in communes),
            ],
        ],
        padding=(12, 12),
        max_zoom=10,
    )
    return folium_map


@st.dialog("Carte régionale des communes", width="large")
def _show_expanded_map(
    communes: list[dict],
    geojson: dict,
    facilities: list[dict],
    show_unassigned: bool,
) -> None:
    st.caption(
        "Cliquez une commune pour consulter sa population et les établissements "
        "qui lui sont associés."
    )
    render_map(
        _build_map(communes, geojson, facilities, show_unassigned),
        height=760,
        key="overview-expanded-map",
        returned_objects=[],
    )


def _export_communes(communes: list[dict]) -> str:
    fields = [
        ("Code communal", "commune_code"),
        ("Commune", "name_fr"),
        ("Province", "province"),
        ("Milieu", "milieu"),
        ("Population 2014", "population_2014"),
        ("Population 2024", "population_2024"),
    ]
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([label for label, _ in fields])
    for row in communes:
        writer.writerow([row.get(field) for _, field in fields])
    return "\ufeff" + output.getvalue()


def render_overview(
    communes: list[dict],
    commune_geojson: dict,
    facilities: list[dict],
    provinces: list[str],
) -> None:
    st.markdown("<div class='tta-overview'></div>", unsafe_allow_html=True)
    year_options = available_population_years(communes)
    latest_year = year_options[-1] if year_options else None
    st.session_state["overview_latest_year"] = latest_year
    st.session_state.setdefault("overview_search", "")
    st.session_state.setdefault("overview_territory", REGION_OPTION)
    st.session_state.setdefault("overview_year", latest_year)
    st.session_state.setdefault("overview_milieu", [])
    if st.session_state["overview_year"] not in year_options:
        st.session_state["overview_year"] = latest_year

    page_header("Overview Dashboard", "", compact=True)

    with st.container(key="tta-overview-toolbar"):
        search_col, territory_col, year_col, filters_col, export_col, notice_col, user_col = (
            st.columns(
                [1.65, 1.15, 0.88, 0.72, 0.82, 0.22, 0.85],
                gap="small",
                vertical_alignment="center",
            )
        )
        search = search_col.text_input(
            "Rechercher une commune",
            placeholder="Rechercher une commune…",
            label_visibility="collapsed",
            key="overview_search",
        )
        territory = territory_col.selectbox(
            "Territoire",
            [REGION_OPTION, *provinces],
            label_visibility="collapsed",
            key="overview_territory",
        )
        population_year = year_col.selectbox(
            "Période",
            year_options or [None],
            format_func=lambda year: "Non disponible" if year is None else str(year),
            label_visibility="collapsed",
            key="overview_year",
        )
        with filters_col.popover(
            "Filtres",
            icon=":material/tune:",
            use_container_width=True,
        ) as filter_container:
            selected_milieux = multiselect_filter(
                "Milieu",
                ["Urbain", "Mixte", "Rural"],
                key="overview_milieu",
                container=filter_container,
            )
            st.button(
                "Réinitialiser",
                key="overview_reset_filters",
                on_click=_reset_overview_filters,
                use_container_width=True,
            )
        export_slot = export_col.empty()
        notice_col.markdown(
            "<div class='tta-overview-notification' title='Notifications'>🔔</div>",
            unsafe_allow_html=True,
        )
        user_col.markdown(
            "<div class='tta-overview-user'>● &nbsp; Administrateur</div>",
            unsafe_allow_html=True,
        )

    selected_provinces = [] if territory == REGION_OPTION else [territory]
    filtered = filter_overview_communes(
        communes,
        provinces=selected_provinces,
        milieux=selected_milieux,
        search=search,
    )
    filtered_codes = {str(row["commune_code"]) for row in filtered}
    filtered_geojson = {
        "type": "FeatureCollection",
        "features": [
            feature
            for feature in commune_geojson["features"]
            if str(feature["properties"]["commune_code"]) in filtered_codes
        ],
    }

    unassociated_facilities = [row for row in facilities if row.get("commune_code") is None]
    territorial_filter_active = bool(selected_provinces or selected_milieux or search.strip())
    shown_facilities = [
        row
        for row in facilities
        if row.get("commune_code") is not None
        and (not territorial_filter_active or str(row["commune_code"]) in filtered_codes)
    ]
    if not territorial_filter_active:
        shown_facilities.extend(unassociated_facilities)

    export_slot.download_button(
        "Exporter",
        data=_export_communes(filtered),
        file_name=f"tta_communes_rgph_{population_year or 'indisponible'}.csv",
        mime="text/csv",
        disabled=not filtered,
        key="overview_export",
        use_container_width=True,
        icon=":material/download:",
    )

    page_header(
        "Overview Dashboard",
        "Aperçu global de l'accès aux soins et des caractéristiques territoriales "
        f"de la région {REGION_NAME}.",
        include_topbar=False,
    )

    if not filtered:
        empty_state(
            "Aucun résultat",
            "Aucune commune ne correspond aux filtres sélectionnés.",
        )
        source_info(
            "HCP RGPH 2014/2024; OpenStreetMap Geofabrik Maroc",
            "Populations 2014 et 2024",
            "Les établissements hors polygones ne sont pas affectés à une commune.",
        )
        return

    population_total = (
        _sum_field(filtered, f"population_{population_year}")
        if population_year is not None
        else None
    )
    filtered_years = available_population_years(filtered)
    latest_filtered_year = filtered_years[-1] if filtered_years else None
    previous_filtered_year = filtered_years[-2] if len(filtered_years) > 1 else None
    latest_population = (
        _sum_field(filtered, f"population_{latest_filtered_year}")
        if latest_filtered_year is not None
        else None
    )
    previous_population = (
        _sum_field(filtered, f"population_{previous_filtered_year}")
        if previous_filtered_year is not None
        else None
    )
    growth = (
        (latest_population - previous_population) / previous_population * 100
        if latest_population is not None
        and previous_population is not None
        and previous_population > 0
        else None
    )
    milieu_counts = Counter(row["milieu"] for row in filtered)
    facility_description = (
        f"{len(unassociated_facilities)} non associés"
        if not territorial_filter_active
        else "Hors périmètre non inclus"
    )
    population_description = (
        f"+ {growth:.1f}% vs {previous_filtered_year}"
        if growth is not None
        else "Évolution non disponible"
    )
    communes_description = (
        f"{len({row['province'] for row in filtered})} provinces"
        if not territorial_filter_active
        else "Communes filtrées"
    )
    kpi_row(
        [
            {
                "label": "Communes",
                "value": f"{len(filtered):,}".replace(",", " "),
                "description": communes_description,
                "source": "",
                "icon": "👥",
            },
            {
                "label": f"Population totale ({population_year or '—'})",
                "value": _format_number(population_total),
                "description": population_description,
                "source": "",
                "icon": "👥",
            },
            {
                "label": "Établissements OSM",
                "value": f"{len(shown_facilities):,}".replace(",", " "),
                "description": facility_description,
                "source": "",
                "icon": "🏥",
            },
            {
                "label": "Provinces / Préfectures",
                "value": len({row["province"] for row in filtered}),
                "description": "Région TTA",
                "source": "",
                "icon": "📍",
            },
            {
                "label": "Urbaines",
                "value": milieu_counts["Urbain"],
                "description": "Communes",
                "source": "",
                "icon": "🏙️",
            },
            {
                "label": "Mixtes",
                "value": milieu_counts["Mixte"],
                "description": "Communes",
                "source": "",
                "icon": "🏘️",
            },
            {
                "label": "Rurales",
                "value": milieu_counts["Rural"],
                "description": "Communes",
                "source": "",
                "icon": "🏡",
            },
        ],
        columns=7,
    )

    chart_columns = st.columns(3, gap="small")
    year_label = str(population_year) if population_year is not None else "Non disponible"
    population_chart = (
        population_by_province(filtered, population_year)
        if population_year is not None
        else empty_figure(
            "Population par province",
            "Données de population non disponibles",
        )
    )
    urban_rural_chart = (
        urban_rural_by_province(filtered, population_year)
        if population_year is not None
        else empty_figure(
            "Population urbaine vs rurale",
            "Données de population non disponibles",
        )
    )
    chart_specs = [
        ("Répartition des communes par milieu", milieu_donut(filtered)),
        (f"Population {year_label} par province", population_chart),
        (
            "Population urbaine vs rurale (parts par province)",
            urban_rural_chart,
        ),
    ]
    for column, (title, figure) in zip(chart_columns, chart_specs, strict=True):
        with column:
            chart_card(title, figure)

    chart_columns = st.columns([1.1, 1, 1], gap="small")
    with chart_columns[0], st.container(border=True):
        evolution_period = f" ({filtered_years[0]}–{filtered_years[-1]})" if filtered_years else ""
        st.markdown(
            f"<div class='tta-card-title'>Évolution démographique{evolution_period}</div>",
            unsafe_allow_html=True,
        )
        evolution_chart, evolution_summary = st.columns([2.2, 1], gap="small")
        with evolution_chart:
            figure = demographic_evolution(filtered)
            st.plotly_chart(
                figure,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
        with evolution_summary:
            with st.container(border=True):
                st.caption("Population la plus récente")
                st.markdown(f"**{_format_number(latest_population)}**")
                st.caption(
                    str(latest_filtered_year)
                    if latest_filtered_year is not None
                    else "Année non disponible"
                )
                growth_label = f"{growth:+.1f}%" if growth is not None else "Non disponible"
                st.markdown(
                    "<div class='tta-evolution-label'>Évolution</div>"
                    f"<div class='tta-evolution-value'>{growth_label}</div>",
                    unsafe_allow_html=True,
                )
    with chart_columns[1]:
        chart_card(
            f"Top 10 des communes les plus peuplées ({year_label})",
            population_top_bottom(filtered, bottom=False, year=population_year)
            if population_year is not None
            else empty_figure(
                "Communes les plus peuplées",
                "Données de population non disponibles",
            ),
        )
    with chart_columns[2]:
        chart_card(
            f"Top 10 des communes les moins peuplées ({year_label})",
            population_top_bottom(filtered, bottom=True, year=population_year)
            if population_year is not None
            else empty_figure(
                "Communes les moins peuplées",
                "Données de population non disponibles",
            ),
        )

    map_button_clicked = False
    provincial_rows = build_provincial_summary(
        filtered,
        shown_facilities,
        population_year=population_year,
    )
    formatted_rows = []
    for row in provincial_rows:
        f_row = {}
        for key, value in row.items():
            display_key = key
            if key == "Population urbaine 2024":
                display_key = "Population urbaine"
            elif key == "Population rurale 2024":
                display_key = "Population rurale"

            if key == "Densité (hab/km²)":
                f_row[display_key] = _format_number(value, 1)
            elif key != "Communes" and (isinstance(value, (int, float)) or value is None):
                f_row[display_key] = _format_number(value)
            else:
                f_row[display_key] = value
        formatted_rows.append(f_row)

    row_four = st.columns([0.9, 1, 1.1], gap="small")
    with row_four[0]:
        chart_card(
            "Répartition des établissements par type",
            facilities_by_type(shown_facilities),
        )
    with row_four[1]:
        chart_card(
            "Établissements par province",
            associated_facilities_by_province(filtered, shown_facilities),
        )
    with row_four[2], st.container(border=True):
        title_col, button_col = st.columns([1.7, 1], vertical_alignment="center")
        title_col.markdown(
            "<div class='tta-card-title'>Carte régionale des communes</div>",
            unsafe_allow_html=True,
        )
        map_button_clicked = button_col.button(
            "⛶ Agrandir",
            key="overview_expand_map",
            use_container_width=True,
            help="Ouvrir la carte dans une fenêtre de grande taille",
        )
        render_map(
            _build_map(
                filtered,
                filtered_geojson,
                shown_facilities,
                show_unassigned=not territorial_filter_active,
            ),
            height=295,
            key="overview-main-map",
            returned_objects=[],
        )

    bottom_left_col, bottom_right_col = st.columns([1.8, 1.2], gap="small")
    with bottom_left_col:
        table_card(
            "Tableau de synthèse par province",
            formatted_rows,
            height=230,
            action_label="Voir tout le tableau →",
            action_callback=_navigate_to_ranking,
        )

    with bottom_right_col:
        source_info(
            "HCP RGPH pour les données démographiques; OpenStreetMap pour les établissements.",
            ", ".join(map(str, year_options)) if year_options else "Période non disponible",
            "Les établissements OSM ne constituent pas un inventaire officiel exhaustif. "
            "Les établissements hors polygones restent non affectés.",
        )

    if map_button_clicked:
        _show_expanded_map(
            filtered,
            filtered_geojson,
            shown_facilities,
            show_unassigned=not territorial_filter_active,
        )
