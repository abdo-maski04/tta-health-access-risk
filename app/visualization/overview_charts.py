"""Compact Plotly visualisations for the Overview dashboard."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

import plotly.graph_objects as go
from config.theme import COLORS, THEME

CHART_HEIGHT = 250
LAYOUT_DEFAULTS = {
    "paper_bgcolor": THEME.surface,
    "plot_bgcolor": THEME.surface,
    "font": {"family": "Inter, Segoe UI, sans-serif", "color": THEME.text, "size": 10},
    "margin": {"l": 38, "r": 14, "t": 44, "b": 42},
    "showlegend": False,
}

FACILITY_LABELS = {
    "pharmacy": "Pharmacies",
    "hospital": "Hôpitaux",
    "clinic": "Cliniques",
    "doctors": "Médecins",
    "laboratory": "Laboratoires",
    "healthcare_unspecified": "Autres",
    "physiotherapist": "Autres",
}


def apply_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left", "font": {"size": 13}},
        height=CHART_HEIGHT,
        **LAYOUT_DEFAULTS,
    )
    fig.update_xaxes(
        gridcolor=THEME.border,
        zeroline=False,
        tickfont={"size": 9, "color": THEME.text_muted},
        title_font={"size": 9, "color": THEME.text_muted},
    )
    fig.update_yaxes(
        gridcolor=THEME.border,
        zeroline=False,
        tickfont={"size": 9, "color": THEME.text_muted},
        title_font={"size": 9, "color": THEME.text_muted},
    )
    return fig


def empty_figure(
    title: str,
    message: str = "Données non disponibles",
) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 12, "color": THEME.text_muted},
    )
    return apply_layout(fig, title)


def _numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _sum_complete(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [row.get(field) for row in rows]
    if not values or any(not _numeric(value) for value in values):
        return None
    return sum(values)


def _population_years(rows: list[dict[str, Any]]) -> list[int]:
    if not rows:
        return []
    common_fields = set.intersection(*(set(row) for row in rows))
    years = []
    for field in common_fields:
        year_text = field.removeprefix("population_")
        if field.startswith("population_") and year_text.isdigit():
            if all(_numeric(row.get(field)) for row in rows):
                years.append(int(year_text))
    return sorted(years)


def milieu_donut(communes: Iterable[dict[str, Any]]) -> go.Figure:
    rows = list(communes)
    if not rows:
        return empty_figure("Communes par milieu")

    counts = Counter(row["milieu"] for row in rows)
    categories = ["Urbain", "Mixte", "Rural"]
    values = [counts[label] for label in categories]
    labels = [f"{label} ({count})" for label, count in zip(categories, values)]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            sort=False,
            marker={
                "colors": [COLORS["overview_milieu"][label] for label in categories],
                "line": {"color": THEME.surface, "width": 2},
            },
            textinfo="percent",
            textfont={"size": 10, "color": THEME.surface},
            hovertemplate="%{label}: %{value} communes (%{percent})<extra></extra>",
            domain={"x": [0.0, 0.68], "y": [0, 1]},
        )
    )
    fig.update_layout(
        title={"text": "Répartition des communes par milieu", "x": 0.02, "font": {"size": 13}},
        height=CHART_HEIGHT,
        margin={"l": 4, "r": 4, "t": 42, "b": 8},
        paper_bgcolor=THEME.surface,
        font={"family": "Inter, Segoe UI, sans-serif", "color": THEME.text},
        showlegend=True,
        legend={
            "orientation": "v",
            "x": 0.7,
            "y": 0.5,
            "font": {"size": 9, "color": THEME.text_muted},
        },
        annotations=[
            {
                "text": str(sum(values)),
                "x": 0.34,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 15, "color": THEME.navy, "weight": 700},
            }
        ],
    )
    return fig


def population_by_province(
    communes: Iterable[dict[str, Any]],
    year: int = 2024,
) -> go.Figure:
    rows = list(communes)
    title = f"Population {year} par province"
    if not rows:
        return empty_figure(title)

    field = f"population_{year}"
    if any(not _numeric(row.get(field)) for row in rows):
        return empty_figure(title, f"Population {year} indisponible ou incomplète")
    totals: dict[str, int] = {}
    for row in rows:
        totals[row["province"]] = totals.get(row["province"], 0) + row[field]
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    fig = go.Figure(
        go.Bar(
            x=[name for name, _ in ordered],
            y=[value for _, value in ordered],
            marker={"color": COLORS["overview_chart"]["primary"], "line": {"width": 0}},
            text=[f"{value:,}".replace(",", " ") for _, value in ordered],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y:,.0f} habitants<extra></extra>",
        )
    )
    fig.update_layout(yaxis_title="Habitants")
    fig.update_xaxes(tickangle=-28, automargin=True)
    return apply_layout(fig, title)


def urban_rural_by_province(
    communes: Iterable[dict[str, Any]],
    year: int = 2024,
) -> go.Figure:
    rows = list(communes)
    title = f"Population urbaine vs rurale ({year})"
    if not rows:
        return empty_figure(title)
    if year != 2024:
        return empty_figure(
            title,
            "Répartition urbaine/rurale 2014 non disponible",
        )
    if any(
        not _numeric(row.get(field))
        for row in rows
        for field in ("population_urbaine_2024", "population_rurale_2024")
    ):
        return empty_figure(title, "Données urbaines/rurales indisponibles ou incomplètes")

    provinces = sorted({row["province"] for row in rows})
    urban = []
    rural = []
    for province in provinces:
        province_rows = [row for row in rows if row["province"] == province]
        urban.append(sum(row["population_urbaine_2024"] for row in province_rows))
        rural.append(sum(row["population_rurale_2024"] for row in province_rows))
    order = sorted(
        range(len(provinces)),
        key=lambda index: urban[index] + rural[index],
        reverse=True,
    )
    provinces = [provinces[index] for index in order]
    urban = [urban[index] for index in order]
    rural = [rural[index] for index in order]

    fig = go.Figure()
    fig.add_bar(
        name="Urbaine",
        x=provinces,
        y=urban,
        marker={"color": COLORS["overview_chart"]["primary"]},
        hovertemplate="%{x}: %{y:,.0f} habitants urbains<extra></extra>",
    )
    fig.add_bar(
        name="Rurale",
        x=provinces,
        y=rural,
        marker={"color": COLORS["overview_chart"]["rural"]},
        hovertemplate="%{x}: %{y:,.0f} habitants ruraux<extra></extra>",
    )
    fig.update_layout(
        barmode="stack",
        barnorm="percent",
        yaxis_title="Part de la population",
        yaxis={"range": [0, 100], "ticksuffix": "%"},
        showlegend=True,
        legend={
            "orientation": "h",
            "x": 0.02,
            "y": 1.12,
            "font": {"size": 9, "color": THEME.text_muted},
        },
    )
    fig.update_xaxes(tickangle=-28, automargin=True)
    return apply_layout(fig, title)


def demographic_evolution(communes: Iterable[dict[str, Any]]) -> go.Figure:
    rows = list(communes)
    title = "Évolution démographique 2014–2024"
    if not rows:
        return empty_figure(title)

    years = _population_years(rows)
    if not years:
        return empty_figure(title, "Données historiques non disponibles ou incomplètes")
    populations = [_sum_complete(rows, f"population_{year}") for year in years]
    fig = go.Figure(
        go.Scatter(
            x=years,
            y=populations,
            mode="lines+markers",
            line={"color": COLORS["overview_chart"]["secondary"], "width": 3, "shape": "spline"},
            fill="tozeroy",
            fillcolor="rgba(23,133,130,0.12)",
            marker={
                "color": COLORS["overview_chart"]["secondary"],
                "size": 8,
                "line": {"color": THEME.surface, "width": 2},
            },
            hovertemplate="%{x}: %{y:,.0f} habitants<extra></extra>",
        )
    )
    fig.update_layout(yaxis_title="Habitants")
    if len(populations) > 1 and populations[0] and populations[-1] is not None:
        growth = (populations[-1] - populations[0]) / populations[0] * 100
        fig.add_annotation(
            text=f"{growth:+.1f}% entre {years[0]} et {years[-1]}",
            xref="paper",
            yref="paper",
            x=0.98,
            y=1.12,
            showarrow=False,
            xanchor="right",
            font={"size": 9, "color": COLORS["overview_chart"]["secondary"]},
        )
    return apply_layout(fig, title)


def population_top_bottom(
    communes: Iterable[dict[str, Any]],
    bottom: bool = False,
    year: int = 2024,
) -> go.Figure:
    rows = list(communes)
    polarity = "moins" if bottom else "plus"
    title = f"Top 10 communes les {polarity} peuplées ({year})"
    if not rows:
        return empty_figure(title)

    field = f"population_{year}"
    ordered = [row for row in rows if _numeric(row.get(field))]
    ordered = sorted(
        ordered,
        key=lambda row: (
            row[field] if bottom else -row[field],
            row["name_fr"].casefold(),
        ),
    )[:10]
    if not ordered:
        return empty_figure(title, f"Population {year} non disponible")
    fig = go.Figure(
        go.Bar(
            x=[row[field] for row in ordered],
            y=[row["name_fr"] for row in ordered],
            orientation="h",
            marker={
                "color": COLORS["overview_chart"]["rural"]
                if bottom
                else COLORS["overview_chart"]["primary"]
            },
            text=[f"{row[field]:,}".replace(",", " ") for row in ordered],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f} habitants<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Habitants",
        margin={"l": 118, "r": 42, "t": 42, "b": 32},
    )
    if bottom:
        fig.update_yaxes(
            categoryorder="array",
            categoryarray=[row["name_fr"] for row in ordered],
            autorange="reversed",
        )
    return apply_layout(fig, title)


def facilities_by_type(facilities: Iterable[dict[str, Any]]) -> go.Figure:
    rows = list(facilities)
    if not rows:
        return empty_figure("Établissements OSM par type")

    raw_counts = Counter(row["facility_type"] for row in rows)
    counts: Counter[str] = Counter()
    color_by_label = {
        "Pharmacies": COLORS["facility"]["pharmacy"],
        "Hôpitaux": COLORS["facility"]["hospital"],
        "Cliniques": COLORS["facility"]["clinic"],
        "Médecins": COLORS["facility"]["doctors"],
        "Laboratoires": COLORS["facility"]["laboratory"],
        "Autres": COLORS["facility"]["healthcare_unspecified"],
    }
    for facility_type, count in raw_counts.items():
        counts[FACILITY_LABELS.get(facility_type, "Autres")] += count
    labels = sorted(counts, key=counts.get, reverse=True)
    values = [counts[label] for label in labels]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            sort=False,
            marker={
                "colors": [color_by_label[label] for label in labels],
                "line": {"color": THEME.surface, "width": 2},
            },
            textinfo="none",
            hovertemplate="%{label}: %{value} établissements OSM<extra></extra>",
        )
    )
    fig.update_layout(
        title={"text": "Établissements OSM par type", "x": 0.02, "font": {"size": 13}},
        height=CHART_HEIGHT,
        margin={"l": 4, "r": 4, "t": 42, "b": 8},
        paper_bgcolor=THEME.surface,
        font={"family": "Inter, Segoe UI, sans-serif", "color": THEME.text},
        showlegend=True,
        legend={
            "orientation": "v",
            "x": 0.7,
            "y": 0.5,
            "font": {"size": 9, "color": THEME.text_muted},
        },
        annotations=[
            {
                "text": f"{len(rows)}<br><span style='font-size:9px'>Total OSM</span>",
                "x": 0.34,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 14, "color": THEME.navy, "weight": 700},
            }
        ],
    )
    return fig


def associated_facilities_by_province(
    communes: Iterable[dict[str, Any]],
    facilities: Iterable[dict[str, Any]],
) -> go.Figure:
    commune_rows = list(communes)
    facility_rows = list(facilities)
    title = "Établissements associés par province"
    if not commune_rows:
        return empty_figure(title)

    associated = {str(row["commune_code"]): row["province"] for row in commune_rows}
    counts = Counter(
        associated[str(row["commune_code"])]
        for row in facility_rows
        if row.get("commune_code") is not None and str(row["commune_code"]) in associated
    )
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    fig = go.Figure(
        go.Bar(
            x=[province for province, _ in ordered],
            y=[count for _, count in ordered],
            marker={"color": THEME.turquoise},
            text=[str(count) for _, count in ordered],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y} établissements associés<extra></extra>",
        )
    )
    fig.update_xaxes(tickangle=-28, automargin=True)
    fig.update_layout(yaxis_title="Établissements")
    return apply_layout(fig, title)
