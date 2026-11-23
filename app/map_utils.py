"""Construction des couches Folium de la carte TTA."""

from __future__ import annotations

import html
import json
import math
from collections import Counter
from collections.abc import Iterable

from config.theme import COLORS, THEME

MILIEU_COLORS = COLORS["milieu"]
FACILITY_COLORS = COLORS["facility"]
RISK_MILIEU_COLORS = COLORS["risk_milieu"]
RISK_FACILITY_COLORS = COLORS["risk_facility"]
FACILITY_LABELS = {
    "hospital": "Hôpitaux",
    "clinic": "Cliniques",
    "pharmacy": "Pharmacies",
    "doctors": "Médecins",
    "laboratory": "Laboratoires",
    "physiotherapist": "Autres",
    "healthcare_unspecified": "Autres",
}
FACILITY_ICON_CONTENT = {
    "hospital": (
        "<path d='M4 21V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v16'/>"
        "<path d='M9 21v-4h6v4M9 7h.01M15 7h.01M9 11h.01M15 11h.01'/>"
        "<path d='M11 7h2m-1-1v2'/>"
    ),
    "clinic": "<path d='M12 5v14M5 12h14' stroke-width='2.5'/>",
    "pharmacy": (
        "<path d='M12 5v14M5 12h14' stroke-width='2.5'/>"
        "<path d='M4 4h.01M20 20h.01'/>"
    ),
    "doctors": (
        "<path d='M6 3v5a4 4 0 0 0 8 0V3M4 3h4m4 0h4'/>"
        "<path d='M10 12v2a4 4 0 0 0 8 0v-1'/>"
        "<circle cx='18' cy='11' r='2'/>"
    ),
    "laboratory": (
        "<path d='M9 3h6m-5 0v7l-5.5 8.5A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-2.5L14 10V3'/>"
        "<path d='M8 16h8'/>"
    ),
    "other": (
        "<path d='M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z'/>"
        "<path d='M12 7v6m-3-3h6'/>"
    ),
}

MAP_TOOL_ICONS = {
    "satellite": "<circle cx='12' cy='12' r='8'/><path d='m7 17 10-10M9 9l2 2m4 4 2 2'/>",
    "light": "<circle cx='12' cy='12' r='4'/><path d='M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42'/>",
    "dark": "<path d='M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z'/>",
    "boundaries": "<path d='m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z'/><path d='M9 3v15m6-12v15'/>",
    "facilities": "<path d='M12 5v14M5 12h14' stroke-width='2.5'/>",
    "unassigned": "<circle cx='12' cy='12' r='8'/><path d='M12 8v4m0 4h.01'/>",
    "bubbles": "<circle cx='8' cy='15' r='4'/><circle cx='16' cy='8' r='5'/>",
    "heatmap": "<path d='M4 4h16v16H4z'/><path d='M8 8h.01M12 8v.01M16 8h.01M8 12v.01m4 0h.01m4-.01v.01M8 16h.01m4 0v.01m4-.01v.01' stroke-width='2.5'/>",
    "recenter": "<circle cx='12' cy='12' r='8'/><circle cx='12' cy='12' r='2'/><path d='M12 2v3m0 14v3M2 12h3m14 0h3'/>",
    "fullscreen": "<path d='M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m13-5v3a2 2 0 0 1-2 2h-3'/>",
}


def facility_icon_svg(kind: str, *, size: int = 14) -> str:
    """Return a small outline SVG icon for a healthcare facility category."""
    content = FACILITY_ICON_CONTENT.get(kind, FACILITY_ICON_CONTENT["other"])
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
        "viewBox='0 0 24 24' fill='none' stroke='#FFFFFF' stroke-width='1.75' "
        "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>"
        f"{content}</svg>"
    )


def _map_tool_svg(name: str) -> str:
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='currentColor' "
        "stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round' "
        "aria-hidden='true'>"
        f"{MAP_TOOL_ICONS[name]}</svg>"
    )


def _tooltip_text(value: object) -> str:
    escaped = html.escape(str(value))
    return escaped.replace("`", "&#96;").replace("${", "&#36;{")


def _format_population(value: object) -> str:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        return "Non disponible"
    return f"{int(value):,}".replace(",", " ")


BASE_MAP_CONFIGS: dict[str, dict[str, str | int]] = {
    "light": {
        "name": "Clair Professionnel (CartoDB Positron)",
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    "standard": {
        "name": "Standard (OpenStreetMap)",
        "tiles": "OpenStreetMap",
        "attr": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        "max_zoom": 19,
    },
    "satellite": {
        "name": "Satellite (Esri World Imagery)",
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles &copy; Esri",
        "max_zoom": 19,
    },
    "hybrid": {
        "name": "Satellite Hybride (Esri)",
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles &copy; Esri",
        "max_zoom": 19,
    },
    "terrain": {
        "name": "Relief / Topographique (OpenTopoMap)",
        "tiles": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attr": "Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap",
        "subdomains": "abc",
        "max_zoom": 19,
    },
    "dark": {
        "name": "Sombre (CartoDB Dark Matter)",
        "tiles": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
        "subdomains": "abcd",
        "max_zoom": 20,
    },
}


def get_initial_map(base_map: str = "light", add_tile_layers: bool = True):
    try:
        import folium
    except ImportError as exc:
        raise RuntimeError(
            "Folium n'est pas installé. Installez les dépendances déclarées dans requirements/app.txt."
        ) from exc

    norm = str(base_map).strip().lower()
    selected_key = "light"
    if norm in BASE_MAP_CONFIGS:
        selected_key = norm
    elif "openstreet" in norm or "osm" in norm or "standard" in norm:
        selected_key = "standard"
    elif "hybrid" in norm:
        selected_key = "hybrid"
    elif "satellit" in norm or "imagerie" in norm or "imagery" in norm:
        selected_key = "satellite"
    elif "terrain" in norm or "topo" in norm or "relief" in norm:
        selected_key = "terrain"
    elif "dark" in norm or "sombre" in norm:
        selected_key = "dark"

    folium_map = folium.Map(
        location=[35.20, -5.45],
        zoom_start=8,
        tiles=None,
    )

    base_layers = {}
    if add_tile_layers:
        for key, cfg in BASE_MAP_CONFIGS.items():
            layer = folium.TileLayer(
                tiles=str(cfg["tiles"]),
                name=str(cfg["name"]),
                attr=str(cfg["attr"]),
                subdomains=str(cfg.get("subdomains", "abc")),
                max_zoom=int(cfg.get("max_zoom", 19)),
                control=True,
                show=(key == selected_key),
            )
            layer.add_to(folium_map)
            base_layers[key] = layer
        hybrid_labels = folium.TileLayer(
            tiles=(
                "https://server.arcgisonline.com/ArcGIS/rest/services/"
                "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            ),
            name="Étiquettes et frontières",
            attr="Labels &copy; Esri",
            overlay=True,
            control=False,
            show=(selected_key == "hybrid"),
            max_zoom=19,
        )
        hybrid_labels.add_to(folium_map)
        folium_map._tta_hybrid_labels = hybrid_labels
    else:
        cfg = BASE_MAP_CONFIGS[selected_key]
        layer = folium.TileLayer(
            tiles=str(cfg["tiles"]),
            name=str(cfg["name"]),
            attr=str(cfg["attr"]),
            subdomains=str(cfg.get("subdomains", "abc")),
            max_zoom=int(cfg.get("max_zoom", 19)),
            control=True,
            show=True,
        )
        layer.add_to(folium_map)
        base_layers[selected_key] = layer
    folium_map._tta_base_layers = base_layers

    return folium_map


MAP_COLOR_MODES = {"environment", "province", "population", "density", "facilities"}
NUMERIC_MAP_MODES = {"population", "density", "facilities"}


def commune_color_values(
    communes: Iterable[dict],
    color_mode: str,
    facilities: Iterable[dict] | None = None,
    areas_km2: dict[str, float] | None = None,
) -> dict[str, float | None]:
    """Return real numeric values used by population, density, and facility maps."""
    if color_mode not in MAP_COLOR_MODES:
        raise ValueError(f"Mode cartographique inconnu: {color_mode}")
    rows = list(communes)
    if color_mode not in NUMERIC_MAP_MODES:
        return {}
    if color_mode == "facilities":
        counts = Counter(
            str(row["commune_code"]).strip()
            for row in facilities or []
            if row.get("commune_code") is not None
        )
        return {
            str(row["commune_code"]).strip(): float(
                counts[str(row["commune_code"]).strip()]
            )
            for row in rows
        }
    if color_mode == "population":
        return {
            str(row["commune_code"]).strip(): (
                float(row["population_2024"])
                if isinstance(row.get("population_2024"), (int, float))
                else None
            )
            for row in rows
        }

    areas = areas_km2 or {}
    values = {}
    for row in rows:
        code = str(row["commune_code"]).strip()
        area = areas.get(code)
        population = row.get("population_2024")
        values[code] = (
            float(population) / area
            if isinstance(population, (int, float))
            and area is not None
            and area > 0
            else None
        )
    return values


def numeric_color_range(
    values: dict[str, float | None],
) -> tuple[float, float] | None:
    available = [value for value in values.values() if value is not None]
    return (min(available), max(available)) if available else None


def build_commune_layer(
    communes: Iterable[dict],
    geojson: dict,
    folium_map,
    facilities: Iterable[dict] | None = None,
    color_mode: str = "environment",
    color_values: dict[str, float | None] | None = None,
    province_colors: dict[str, str] | None = None,
    selected_code: str | None = None,
    milieu_colors: dict[str, str] | None = None,
    show: bool = True,
):
    import folium
    from branca.colormap import LinearColormap

    if color_mode not in MAP_COLOR_MODES:
        raise ValueError(f"Mode cartographique inconnu: {color_mode}")
    environment_colors = milieu_colors or MILIEU_COLORS
    selected_codes = {str(row["commune_code"]).strip() for row in communes}
    facility_rows = list(facilities or [])
    facility_counts = Counter(
        str(row["commune_code"]).strip()
        for row in facility_rows
        if row.get("commune_code") is not None
    )
    facility_type_counts: dict[str, Counter[str]] = {}
    for row in facility_rows:
        code = row.get("commune_code")
        if code is not None:
            facility_type_counts.setdefault(str(code).strip(), Counter())[
                str(row.get("facility_type", "healthcare_unspecified"))
            ] += 1
    features = [
        feature for feature in geojson["features"]
        if str(feature["properties"]["commune_code"]).strip() in selected_codes
    ]
    feature_group = folium.FeatureGroup(name="Communes", show=show)

    province_names = sorted({
        str(feature["properties"].get("province", ""))
        for feature in features
    })
    province_palette = COLORS["province"]
    colors_by_province = province_colors or {
        province: province_palette[index % len(province_palette)]
        for index, province in enumerate(province_names)
    }

    mode_values = color_values or {}
    numeric_values = [
        mode_values.get(str(feature["properties"]["commune_code"]).strip())
        for feature in features
    ]
    available_values = [value for value in numeric_values if value is not None]
    color_scale = None
    if color_mode in NUMERIC_MAP_MODES and available_values:
        minimum, maximum = min(available_values), max(available_values)
        if minimum == maximum:
            minimum = max(0.0, minimum - 1.0)
            maximum += 1.0
        color_scale = LinearColormap(
            colors=COLORS["map_scale"],
            vmin=minimum,
            vmax=maximum,
        )

    for feature in features:
        code = str(feature["properties"]["commune_code"]).strip()
        properties = dict(feature["properties"])
        milieu = properties.get("milieu", "")
        if color_mode == "environment":
            fill_color = environment_colors.get(
                milieu,
                environment_colors.get("Non assigné", THEME.grey),
            )
        elif color_mode == "province":
            fill_color = colors_by_province.get(
                str(properties.get("province", "")),
                THEME.grey,
            )
        else:
            value = mode_values.get(code)
            fill_color = color_scale(value) if color_scale and value is not None else THEME.grey
        code = str(properties.get("commune_code", "")).strip()
        is_selected = bool(selected_code is not None and code == str(selected_code).strip())
        population_2014_text = _format_population(
            properties.get("population_2014")
        )
        population_2024_text = _format_population(
            properties.get("population_2024")
        )
        urban_population_text = _format_population(
            properties.get("population_urbaine_2024")
        )
        rural_population_text = _format_population(
            properties.get("population_rurale_2024")
        )
        facility_count_text = (
            str(facility_counts[code])
            if facilities is not None
            else "Non disponible"
        )
        type_distribution = [
            f"{FACILITY_LABELS.get(kind, 'Autres')} : {count}"
            for kind, count in sorted(
                facility_type_counts.get(code, Counter()).items(),
                key=lambda item: (
                    FACILITY_LABELS.get(item[0], "Autres"),
                    item[0],
                ),
            )
        ]
        distribution_html = (
            "<br>".join(html.escape(item) for item in type_distribution)
            if type_distribution
            else "Aucun établissement associé"
        )

        milieu_color = environment_colors.get(milieu, THEME.navy)
        popup_html = (
            "<div style='font-family: Inter, sans-serif; min-width: 175px; font-size: 13px; line-height: 1.5; color: #172B3A;'>"
            f"<div style='font-size: 14px; font-weight: 700; color: #0B2235; margin-bottom: 3px;'>Commune : {html.escape(str(properties.get('name_fr', 'Commune')))}</div>"
            f"<b>Province :</b> {html.escape(str(properties.get('province', '')))}<br>"
            f"<b>Code :</b> {html.escape(str(properties.get('commune_code', '')))}<br>"
            f"<b>Environnement :</b> <span style='color: {milieu_color}; font-weight: 600;'>{html.escape(str(milieu))}</span><br>"
            f"<b>Population 2014 :</b> {html.escape(population_2014_text)}<br>"
            f"<b>Population 2024:</b> {html.escape(population_2024_text)}<br>"
            f"<b>Population urbaine:</b> {html.escape(urban_population_text)}<br>"
            f"<b>Population rurale:</b> {html.escape(rural_population_text)}<br>"
            f"<b>Établissements associés:</b> {html.escape(facility_count_text)}<br>"
            f"<b>Répartition :</b><br>{distribution_html}"
            "</div>"
        )

        folium.GeoJson(
            feature,
            style_function=lambda _feature, color=fill_color, is_sel=is_selected: {
                "fillColor": color,
                "color": "#00E5FF" if is_sel else THEME.surface,
                "weight": 3.8 if is_sel else 1.15,
                "fillOpacity": 0.85 if is_sel else 0.70,
            },
            highlight_function=lambda _feature: {
                "weight": 2.5,
                "color": THEME.navy,
                "fillOpacity": 0.78,
            },
            popup_keep_highlighted=True,
            tooltip=folium.Tooltip(
                f"{_tooltip_text(properties.get('name_fr', 'Commune'))}"
                f" — {_tooltip_text(properties.get('province', ''))}"
            ),
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(feature_group)

    feature_group.add_to(folium_map)
    return feature_group


def build_facility_layer(
    facilities: Iterable[dict],
    folium_map,
    color_by_type: bool = True,
    cluster: bool = False,
    *,
    symbol_markers: bool = False,
    commune_lookup: dict[str, dict] | None = None,
    show: bool = True,
):
    import folium

    feature_group = folium.FeatureGroup(
        name="Établissements de santé",
        show=show,
    )
    if cluster:
        from folium.plugins import MarkerCluster
        target = MarkerCluster(name="Regroupement établissements").add_to(feature_group)
    else:
        target = feature_group

    for facility in facilities:
        lat = facility["lat"]
        lon = facility["lon"]
        facility_type = facility["facility_type"]
        name = facility.get("name") or "Établissement OSM sans nom"
        color = (
            FACILITY_COLORS.get(facility_type, THEME.text_muted)
            if color_by_type
            else THEME.blue
        )
        radius = 4 if facility_type == "pharmacy" else 4.5

        parts = [
            f"<div style='font-weight:700; color:#0B2235; font-size:13px; margin-bottom:2px;'>{html.escape(str(name))}</div>",
            f"<b>Type :</b> {html.escape(str(facility_type))}",
        ]
        if facility.get("addr_city"):
            parts.append(f"<b>Ville :</b> {html.escape(str(facility['addr_city']))}")
        parts.append("<small style='color:#718096;'>Source : OpenStreetMap</small>")
        popup_html = "<br>".join(parts)
        code = facility.get("commune_code")
        commune = (
            commune_lookup.get(str(code).strip())
            if code is not None and commune_lookup
            else None
        )
        if commune is not None:
            popup_html += (
                f"<br><b>Commune :</b> "
                f"{html.escape(str(commune.get('name_fr', '')))}"
                f"<br><b>Province :</b> "
                f"{html.escape(str(commune.get('province', '')))}"
                f"<br><b>Code :</b> {html.escape(str(code))}"
            )
        popup = folium.Popup(popup_html, max_width=280)
        tooltip = _tooltip_text(name)

        if symbol_markers:
            kind = (
                facility_type
                if facility_type in RISK_FACILITY_COLORS
                else "other"
            )
            badge_color = RISK_FACILITY_COLORS.get(
                kind,
                RISK_FACILITY_COLORS["other"],
            )
            icon_html = (
                "<svg xmlns='http://www.w3.org/2000/svg' width='30' height='30' "
                "viewBox='0 0 30 30' role='img' fill='none' stroke='#FFFFFF' "
                "stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round' "
                f"aria-label='{html.escape(FACILITY_LABELS.get(facility_type, 'Autres'))}'>"
                "<circle cx='15' cy='15' r='12' fill='"
                f"{badge_color}' stroke='#FFFFFF' stroke-width='2'/>"
                "<g transform='translate(7.5 7.5) scale(.625)'>"
                f"{FACILITY_ICON_CONTENT.get(kind, FACILITY_ICON_CONTENT['other'])}"
                "</g>"
                "</svg>"
            )
            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(
                    html=icon_html,
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    class_name="tta-health-facility-icon",
                ),
                popup=popup,
                tooltip=tooltip,
            ).add_to(target)
        else:
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                weight=1,
                popup=popup,
                tooltip=tooltip,
            ).add_to(target)

    feature_group.add_to(folium_map)
    return feature_group


def build_unassigned_facility_layer(
    facilities: Iterable[dict],
    folium_map,
    *,
    symbol_markers: bool = False,
    show: bool = True,
):
    """Affiche les établissements hors polygones sans inventer d'association."""
    import folium

    feature_group = folium.FeatureGroup(
        name="Établissements hors polygones communaux",
        show=show,
    )
    for facility in facilities:
        if facility.get("commune_code") is not None:
            continue
        name = facility.get("name") or "Établissement OSM sans nom"
        popup = (
            f"<b>{html.escape(str(name))}</b><br>"
            f"<b>Type:</b> {html.escape(str(facility['facility_type']))}<br>"
            "<b>Association communale:</b> Hors périmètre des 146 polygones"
        )
        popup_object = folium.Popup(popup, max_width=280)
        tooltip = f"{_tooltip_text(name)} — hors commune associée"
        if symbol_markers:
            kind = (
                facility["facility_type"]
                if facility["facility_type"] in RISK_FACILITY_COLORS
                else "other"
            )
            icon_html = (
                "<svg xmlns='http://www.w3.org/2000/svg' width='30' height='30' "
                "viewBox='0 0 30 30' role='img' aria-label='Établissement non associé'>"
                "<circle cx='15' cy='15' r='12' fill='#475569' "
                "stroke='#FFFFFF' stroke-width='2'/>"
                "<g transform='translate(7.5 7.5) scale(.625)' fill='none' "
                "stroke='#FFFFFF' stroke-width='1.75' stroke-linecap='round' "
                "stroke-linejoin='round'>"
                f"{FACILITY_ICON_CONTENT.get(kind, FACILITY_ICON_CONTENT['other'])}"
                "</g>"
                "</svg>"
            )
            folium.Marker(
                location=[facility["lat"], facility["lon"]],
                icon=folium.DivIcon(
                    html=icon_html,
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    class_name="tta-health-facility-icon",
                ),
                popup=popup_object,
                tooltip=tooltip,
            ).add_to(feature_group)
        else:
            folium.CircleMarker(
                location=[facility["lat"], facility["lon"]],
                radius=4,
                color=THEME.text_muted,
                fill=True,
                fill_color=THEME.text_muted,
                fill_opacity=0.85,
                weight=1.2,
                popup=popup_object,
                tooltip=tooltip,
            ).add_to(feature_group)

    feature_group.add_to(folium_map)
    return feature_group


def build_proportional_bubble_layer(
    communes: Iterable[dict],
    facilities: Iterable[dict],
    folium_map,
    metric: str = "facilities",
    *,
    show: bool = True,
):
    """Render commune-centred bubbles sized from observed population/facility data."""
    import folium

    if metric not in {"facilities", "population"}:
        raise ValueError(f"Indicateur de bulles inconnu: {metric}")
    commune_rows = list(communes)
    facility_counts = Counter(
        str(row["commune_code"]).strip()
        for row in facilities
        if row.get("commune_code") is not None
    )
    values = {}
    for row in commune_rows:
        code = str(row["commune_code"]).strip()
        value = (
            facility_counts[code]
            if metric == "facilities"
            else row.get("population_2024")
        )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values[code] = max(0.0, float(value))
    maximum = max(values.values(), default=0.0)
    group = folium.FeatureGroup(name="Bulles proportionnelles", show=show)
    if maximum <= 0:
        group.add_to(folium_map)
        return group

    label = "Établissements associés" if metric == "facilities" else "Population 2024"
    for row in commune_rows:
        code = str(row["commune_code"]).strip()
        value = values.get(code)
        latitude = row.get("centroid_lat")
        longitude = row.get("centroid_lon")
        if (
            value is None
            or value <= 0
            or not isinstance(latitude, (int, float))
            or not isinstance(longitude, (int, float))
        ):
            continue
        radius = 5 + 17 * math.sqrt(value / maximum)
        popup = (
            f"<b>{html.escape(str(row.get('name_fr', 'Commune')))}</b><br>"
            f"{html.escape(label)} : {_format_population(value)}"
        )
        folium.CircleMarker(
            location=[latitude, longitude],
            radius=radius,
            color="#FFFFFF",
            weight=2,
            fill=True,
            fill_color="#F59E0B",
            fill_opacity=0.76,
            popup=folium.Popup(popup, max_width=240),
            tooltip=(
                f"{_tooltip_text(row.get('name_fr', 'Commune'))} — "
                f"{_tooltip_text(label)} : {_format_population(value)}"
            ),
        ).add_to(group)
    group.add_to(folium_map)
    return group


def build_heatmap_layer(
    facilities: Iterable[dict],
    folium_map,
    *,
    show: bool = True,
):
    """Render an OSM facility density layer from real facility coordinates."""
    import folium
    from folium.plugins import HeatMap

    rows = list(facilities)
    group = folium.FeatureGroup(name="Concentration des établissements", show=show)
    points = [
        [row["lat"], row["lon"], 1]
        for row in rows
        if isinstance(row.get("lat"), (int, float))
        and isinstance(row.get("lon"), (int, float))
    ]
    if points:
        HeatMap(
            points,
            name="Concentration des établissements",
            radius=20,
            blur=16,
            min_opacity=0.25,
        ).add_to(group)
    group.add_to(folium_map)
    return group


def geojson_bounds(geojson: dict) -> list[list[float]]:
    """Return [south-west, north-east] bounds from Polygon/MultiPolygon coordinates."""
    points: list[tuple[float, float]] = []

    def collect(value: object) -> None:
        if not isinstance(value, (list, tuple)):
            return
        if (
            len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):
            points.append((float(value[0]), float(value[1])))
            return
        for item in value:
            collect(item)

    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        collect(geometry.get("coordinates", []))
    if not points:
        raise ValueError("Aucune coordonnée Polygon/MultiPolygon à cadrer.")
    longitudes, latitudes = zip(*points, strict=True)
    return [
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)],
    ]


def add_enterprise_map_controls(
    folium_map,
    layers: dict[str, object],
    base_layers: dict[str, object],
    bounds: list[list[float]],
    *,
    facility_count: int,
    unassigned_count: int,
):
    """Add map-local quick controls, a compact legend, and the data caveat."""
    from branca.element import MacroElement
    from jinja2 import Template

    map_name = folium_map.get_name()
    layer_names = {
        key: layer.get_name()
        for key, layer in layers.items()
        if layer is not None
    }
    base_names = {
        key: layer.get_name()
        for key, layer in base_layers.items()
        if layer is not None
    }
    hybrid_labels = getattr(folium_map, "_tta_hybrid_labels", None)
    hybrid_labels_name = (
        hybrid_labels.get_name() if hybrid_labels is not None else None
    )
    milieu_items = "".join(
        "<span class='tta-map-legend-item'>"
        f"<i style='background:{color}'></i>{html.escape(label)}</span>"
        for label, color in RISK_MILIEU_COLORS.items()
    )
    type_items = "".join(
        "<span class='tta-map-legend-item'>"
        f"<i class='tta-map-legend-badge' style='background:{RISK_FACILITY_COLORS[kind]}'>"
        f"{facility_icon_svg(kind, size=10)}</i>"
        f"{html.escape(label)}</span>"
        for kind, label in (
            ("hospital", "Hôpitaux"),
            ("clinic", "Cliniques"),
            ("pharmacy", "Pharmacies"),
            ("doctors", "Médecins"),
            ("laboratory", "Laboratoires"),
            ("other", "Autres"),
        )
    )
    html_content = f"""
    <style>
      .tta-map-toolrail {{
        position:absolute; z-index:1000; left:14px; top:82px;
        display:flex; flex-direction:column; gap:4px; padding:4px;
        background:#fff; border:1px solid #E2E8F0; border-radius:9px;
        box-shadow:0 2px 12px rgba(15,23,42,.16);
      }}
      .tta-map-toolrail button {{
        width:36px; height:36px; border:0; border-radius:6px; background:#fff;
        color:#334155; font:600 16px Inter,Arial,sans-serif; cursor:pointer;
      }}
      .tta-map-toolrail button svg {{
        display:block; margin:auto;
      }}
      .tta-map-toolrail button:hover,
      .tta-map-toolrail button[aria-pressed='true'] {{
        background:#E0F2F1; color:#0D5C75;
      }}
      .tta-map-toolrail button:focus-visible {{
        outline:2px solid #0D5C75; outline-offset:1px;
      }}
      .tta-map-legend {{
        position:absolute; z-index:1000; left:14px; bottom:14px;
        max-width:430px; padding:10px 12px; color:#334155;
        background:rgba(255,255,255,.94); border:1px solid #E2E8F0;
        border-radius:8px; box-shadow:0 2px 12px rgba(15,23,42,.13);
        font:10px/1.45 Inter,Arial,sans-serif;
      }}
      .tta-map-legend-title {{ margin-bottom:5px; color:#0F172A; font-weight:700; }}
      .tta-map-legend-section {{ display:flex; flex-wrap:wrap; gap:4px 10px; }}
      .tta-map-legend-item {{ display:inline-flex; align-items:center; gap:4px; white-space:nowrap; }}
      .tta-map-legend-item i {{
        display:inline-block; width:10px; height:10px; border-radius:2px;
      }}
      .tta-map-legend-item .tta-map-legend-badge {{
        display:inline-flex; align-items:center; justify-content:center;
        width:15px; height:15px; border-radius:50%; color:#fff;
      }}
      .tta-map-legend-item .tta-map-legend-badge svg {{
        display:block;
      }}
      .tta-map-legend-divider {{ margin:7px 0 5px; border-top:1px solid #E2E8F0; }}
      .tta-map-future-note {{
        position:absolute; z-index:1000; left:14px; bottom:132px;
        padding:7px 10px; background:rgba(239,246,255,.96);
        border:1px solid #BFDBFE; border-radius:7px; color:#0D5C75;
        font:10px/1.35 Inter,Arial,sans-serif;
      }}
      @media(max-width:900px) {{
        .tta-map-legend {{ max-width:calc(100vw - 90px); }}
        .tta-map-toolrail {{ left:8px; top:76px; }}
        .tta-map-legend, .tta-map-future-note {{ left:8px; }}
      }}
    </style>
    <div class='tta-map-toolrail' role='toolbar' aria-label='Outils cartographiques'>
      <button type='button' data-base='satellite' title='Satellite' aria-label='Satellite'>{_map_tool_svg("satellite")}</button>
      <button type='button' data-base='light' title='Clair' aria-label='Clair'>{_map_tool_svg("light")}</button>
      <button type='button' data-base='dark' title='Sombre' aria-label='Sombre'>{_map_tool_svg("dark")}</button>
      <button type='button' data-layer='communes' title='Frontières communales' aria-label='Frontières'>{_map_tool_svg("boundaries")}</button>
      <button type='button' data-layer='facilities' title='Établissements de santé' aria-label='Établissements'>{_map_tool_svg("facilities")}</button>
      <button type='button' data-layer='unassigned' title='Établissements non associés' aria-label='Non associés'>{_map_tool_svg("unassigned")}</button>
      <button type='button' data-layer='bubbles' title='Bulles proportionnelles' aria-label='Bulles'>{_map_tool_svg("bubbles")}</button>
      <button type='button' data-layer='heatmap' title='Carte de chaleur' aria-label='Heatmap'>{_map_tool_svg("heatmap")}</button>
      <button type='button' data-action='recenter' title='Recentrer la région' aria-label='Recentrer'>{_map_tool_svg("recenter")}</button>
      <button type='button' data-action='fullscreen' title='Plein écran' aria-label='Plein écran'>{_map_tool_svg("fullscreen")}</button>
    </div>
    <div class='tta-map-future-note'>
      Indicateurs validés de risque et d’accessibilité non encore intégrés.
    </div>
    <div class='tta-map-legend' role='note' aria-label='Légende cartographique'>
      <div class='tta-map-legend-title'>Milieu territorial</div>
      <div class='tta-map-legend-section'>{milieu_items}</div>
      <div class='tta-map-legend-divider'></div>
      <div class='tta-map-legend-title'>Établissements OSM ({facility_count:,} · {unassigned_count} non associés)</div>
      <div class='tta-map-legend-section'>{type_items}</div>
    </div>
    """
    script = f"""
    setTimeout(function() {{
    (function() {{
      const map = {map_name};
      const layers = {json.dumps(layer_names)};
      const bases = {json.dumps(base_names)};
      const hybridLabels = {json.dumps(hybrid_labels_name)};
      const bounds = {json.dumps(bounds)};
      const container = map.getContainer();
      container.insertAdjacentHTML('beforeend', {json.dumps(html_content)});
      const getLayer = (name) => window[name];
      const buttons = container.querySelectorAll('.tta-map-toolrail button');
      function setLayer(key, visible) {{
        const layer = getLayer(layers[key]);
        if (!layer) return;
        if (visible && !map.hasLayer(layer)) map.addLayer(layer);
        if (!visible && map.hasLayer(layer)) map.removeLayer(layer);
      }}
      function setBase(key) {{
        Object.keys(bases).forEach((name) => {{
          const layer = getLayer(bases[name]);
          if (layer && map.hasLayer(layer)) map.removeLayer(layer);
        }});
        if (hybridLabels) {{
          const labels = getLayer(hybridLabels);
          if (labels && map.hasLayer(labels)) map.removeLayer(labels);
        }}
        const selected = getLayer(bases[key]);
        if (selected) map.addLayer(selected);
        if (key === 'hybrid' && hybridLabels) {{
          const labels = getLayer(hybridLabels);
          if (labels) map.addLayer(labels);
        }}
      }}
      function syncButtons() {{
        buttons.forEach((button) => {{
          const layerKey = button.dataset.layer;
          if (layerKey && layers[layerKey]) {{
            const layer = getLayer(layers[layerKey]);
            button.setAttribute('aria-pressed', String(Boolean(layer && map.hasLayer(layer))));
          }}
          const baseKey = button.dataset.base;
          if (baseKey && bases[baseKey]) {{
            const layer = getLayer(bases[baseKey]);
            button.setAttribute('aria-pressed', String(Boolean(layer && map.hasLayer(layer))));
          }}
        }});
      }}
      buttons.forEach((button) => button.addEventListener('click', () => {{
        if (button.dataset.layer) {{
          const layer = getLayer(layers[button.dataset.layer]);
          if (layer) setLayer(button.dataset.layer, !map.hasLayer(layer));
        }} else if (button.dataset.base) {{
          setBase(button.dataset.base);
        }} else if (button.dataset.action === 'recenter') {{
          map.fitBounds(bounds, {{padding:[24,24], maxZoom:10}});
        }} else if (button.dataset.action === 'fullscreen') {{
          const target = container.requestFullscreen ? container : container.parentElement;
          if (target && target.requestFullscreen) target.requestFullscreen();
        }}
        syncButtons();
      }}));
      map.on('layeradd layerremove', syncButtons);
      syncButtons();
    }})();
    }}, 0);
    """
    class EnterpriseMapControls(MacroElement):
        def __init__(self, javascript: str):
            super().__init__()
            self.javascript = javascript
            self._template = Template(
                "{% macro script(this, kwargs) %}{{ this.javascript }}{% endmacro %}"
            )

    folium_map.add_child(EnterpriseMapControls(script))


def build_legend(
    unassigned_count: int | None = None,
    map_mode: str = "environment",
    province_colors: dict[str, str] | None = None,
    value_range: tuple[float, float] | None = None,
    milieu_colors: dict[str, str] | None = None,
):
    try:
        from branca.element import MacroElement
        from jinja2 import Template
    except ImportError as exc:
        raise RuntimeError(
            "Branca/Jinja2 ne sont pas disponibles avec l'installation Folium."
        ) from exc

    if unassigned_count is None:
        unassigned_label = "Hors polygones"
    elif unassigned_count:
        unassigned_label = f"Hors polygones ({unassigned_count})"
    else:
        unassigned_label = None
    unassigned_item = (
        f'<span style="color:{THEME.text_muted};">●</span> {unassigned_label}<br>'
        if unassigned_label
        else ""
    )
    environment_colors = milieu_colors or MILIEU_COLORS

    if map_mode == "environment":
        legend_content = f"""
        <div style="display: flex; gap: 24px; font-family: Inter, Segoe UI, sans-serif; font-size: 11px;">
            <div>
                <div style="font-weight: 700; color: #172B3A; margin-bottom: 7px;">Territorial Environment</div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-block; width:12px; height:12px; background:{environment_colors['Urbain']}; border-radius:2px;"></span> Urban
                </div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-block; width:12px; height:12px; background:{environment_colors['Mixte']}; border-radius:2px;"></span> Mixed
                </div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-block; width:12px; height:12px; background:{environment_colors['Rural']}; border-radius:2px;"></span> Rural
                </div>
                <div style="display: flex; align-items: center; gap: 7px;">
                    <span style="display:inline-block; width:12px; height:12px; background:#CBD5E1; border-radius:2px;"></span> Unassigned
                </div>
            </div>
            <div>
                <div style="font-weight: 700; color: #172B3A; margin-bottom: 7px;">Healthcare Facilities</div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; background:#2878B5; color:#fff; border-radius:50%; font-size:9px; font-weight:700;">H</span> Hospitals
                </div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; background:#CE5252; color:#fff; border-radius:50%; font-size:10px; font-weight:700;">+</span> Clinics
                </div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; background:#27966F; color:#fff; border-radius:50%; font-size:10px; font-weight:700;">+</span> Pharmacies
                </div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; background:#E5A13A; color:#fff; border-radius:50%; font-size:9px;">👤</span> Doctors
                </div>
                <div style="display: flex; align-items: center; gap: 7px; margin-bottom: 5px;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; background:#6C63A8; color:#fff; border-radius:50%; font-size:9px;">🧪</span> Laboratories
                </div>
                <div style="display: flex; align-items: center; gap: 7px;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; background:#718096; color:#fff; border-radius:50%; font-size:8px;">⋯</span> Other
                </div>
                <div style="font-size:10px; color:#64748B; margin-top:5px; border-top:1px solid #E2E8F0; padding-top:4px;">
                    {unassigned_item}
                </div>
            </div>
        </div>
        """
    elif map_mode == "province":
        province_items = "".join(
            f"<span style='color:{color}'>●</span> "
            f"{html.escape(province)}<br>"
            for province, color in sorted((province_colors or {}).items())
        )
        legend_content = f"<b>Province / préfecture</b><br>{province_items}"
    elif map_mode == "risk":
        legend_content = (
            "<b>Niveau de Risque Global</b><br>"
            f"<small style='color:{THEME.text_muted}'>Modèle en cours de validation backend</small><br>"
            f"<span style='color:{THEME.grey}'>●</span> Données non publiées<br>"
        )
    elif map_mode == "accessibility":
        legend_content = (
            "<b>Score d'Accessibilité aux Soins</b><br>"
            f"<small style='color:{THEME.text_muted}'>Calcul isochrone en cours de validation</small><br>"
            f"<span style='color:{THEME.grey}'>●</span> Données non publiées<br>"
        )
    else:
        labels = {
            "population": ("Population 2024", "habitants"),
            "density": ("Densité 2024", "hab./km²"),
            "facilities": ("Établissements associés", "établissements"),
        }
        title, unit = labels.get(map_mode, ("Indicateur", "unités"))
        if value_range:
            low, high = value_range

            def formatter(value: float) -> str:
                return (
                    f"{value:,.1f}".replace(",", " ")
                    if map_mode == "density"
                    else f"{value:,.0f}".replace(",", " ")
                )

            scale_labels = (
                f"<div style='display:flex;justify-content:space-between'>"
                f"<small>{formatter(low)}</small><small>{formatter(high)}</small></div>"
            )
        else:
            scale_labels = "<small>Données non disponibles</small>"
        gradient = ", ".join(COLORS["map_scale"])
        legend_content = (
            f"<b>{title}</b><br>"
            f"<div style='height:9px;margin:5px 0;"
            f"background:linear-gradient(to right,{gradient})'></div>"
            f"{scale_labels}<small>{unit}</small><br>"
            f"<span style='color:{THEME.grey}'>●</span> Non disponible<br>"
        )

    class Legend(MacroElement):
        def __init__(self):
            super().__init__()
            self._template = Template(
                f"""
                {{% macro header(this, kwargs) %}}
                <div style="position: absolute; bottom: 20px; right: 20px; z-index: 9999;
                            background: {THEME.surface}; color: {THEME.text};
                            padding: 12px 16px; border: 1px solid {THEME.border};
                            border-radius: 10px; font: 11px/1.5 Inter, Segoe UI, sans-serif;
                            box-shadow: 0 4px 16px rgba(11,34,53,.15);">
                    {legend_content}
                </div>
                <div style="position: absolute; bottom: 20px; left: 20px; z-index: 9999;
                            background: #EBF5FB; color: #1B4F72; border: 1px solid #AED6F1;
                            border-radius: 8px; padding: 7px 14px; font: 12px/1.4 Inter, sans-serif;
                            display: flex; align-items: center; gap: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <span style="font-weight: 700; font-size: 14px; color: #2878B5;">ℹ</span>
                    <span>Validated risk and accessibility indicators are not yet available.</span>
                </div>
                {{% endmacro %}}
                """
            )

    return Legend()


def render_map(
    folium_map,
    height: int = 650,
    key: str | None = None,
    returned_objects: Iterable[str] | None = None,
):
    try:
        from streamlit_folium import st_folium
    except ImportError as exc:
        raise RuntimeError(
            "streamlit-folium n'est pas installé. "
            "Installez les dépendances déclarées dans requirements/app.txt."
        ) from exc
    return st_folium(
        folium_map,
        width=None,
        height=height,
        key=key,
        returned_objects=returned_objects,
        use_container_width=True,
    )
