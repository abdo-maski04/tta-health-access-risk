"""Cartes KPI reutilisables."""

from __future__ import annotations

import html
from collections.abc import Iterable
from typing import Any

import streamlit as st

KPI_ICONS = (
    ("population", "👥"),
    ("établissement", "🏥"),
    ("commune", "👥"),
    ("province", "📍"),
    ("urbaine", "🏙️"),
    ("mixte", "🏘️"),
    ("rurale", "🏡"),
)


def kpi_card(
    label: str,
    value: Any,
    description: str = "",
    source: str = "",
    icon: str | None = None,
    unit: str = "",
) -> None:
    display_value = "Données non disponibles" if value is None else str(value)
    if icon is None:
        normalized_label = label.casefold()
        icon = next(
            (symbol for hint, symbol in KPI_ICONS if hint in normalized_label),
            "◉",
        )
    unit_html = (
        f"<span class='tta-kpi-unit'>{html.escape(unit)}</span>"
        if unit and value is not None
        else ""
    )
    source_html = (
        f"<div class='tta-kpi-source'>{html.escape(source)}</div>"
        if source
        else ""
    )
    desc_html = ""
    if description:
        if description.startswith("+") or "vs 2014" in description:
            desc_html = (
                f"<div class='tta-kpi-description'><span class='tta-kpi-badge-green'>"
                f"{html.escape(description)}</span></div>"
            )
        else:
            desc_html = (
                f"<div class='tta-kpi-description'>{html.escape(description)}</div>"
            )

    st.markdown(
        "<div class='tta-kpi'>"
        "<div class='tta-kpi-heading'>"
        f"<span class='tta-kpi-icon' aria-hidden='true'>{html.escape(icon)}</span>"
        f"<div class='tta-kpi-label'>{html.escape(label)}</div>"
        "</div>"
        f"<div class='tta-kpi-value'>{html.escape(display_value)}{unit_html}</div>"
        f"{desc_html}"
        f"{source_html}"
        "</div>",
        unsafe_allow_html=True,
    )


def kpi_row(items: Iterable[dict[str, Any]], columns: int = 4) -> None:
    cards = list(items)
    if not cards:
        return
    for offset in range(0, len(cards), columns):
        cols = st.columns(min(columns, len(cards) - offset))
        for column, item in zip(cols, cards[offset:offset + columns], strict=False):
            with column:
                kpi_card(**item)
