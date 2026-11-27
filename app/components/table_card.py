"""Conteneur commun des tableaux."""

from __future__ import annotations

import html
from collections.abc import Callable, Iterable
from typing import Any

import streamlit as st


def table_card(
    title: str,
    data: Iterable[dict[str, Any]],
    *,
    height: int | None = 420,
    action_label: str | None = None,
    action_callback: Callable[[], None] | None = None,
) -> None:
    with st.container(border=True):
        if action_label:
            col_t, col_a = st.columns([3, 1], vertical_alignment="center")
            col_t.markdown(
                f"<div class='tta-card-title' style='display:flex; align-items:center; gap:8px;'>"
                f"<span style='opacity:0.7;'>▦</span> {html.escape(title)}</div>",
                unsafe_allow_html=True,
            )
            if action_callback:
                col_a.button(
                    action_label,
                    on_click=action_callback,
                    key=f"table-action-{title}",
                    use_container_width=True,
                )
            else:
                col_a.markdown(
                    f"<div style='text-align:right;'><span style='color:#087F8C; font-size:12px; font-weight:600;'>{html.escape(action_label)}</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f"<div class='tta-card-title'>{html.escape(title)}</div>",
                unsafe_allow_html=True,
            )
        rows = list(data)
        if rows:
            dataframe_kwargs = {"use_container_width": True, "hide_index": True}
            if height is not None:
                dataframe_kwargs["height"] = height
            st.dataframe(rows, **dataframe_kwargs)
        else:
            st.markdown(
                "<div class='tta-table-empty'>Données non disponibles.</div>",
                unsafe_allow_html=True,
            )

