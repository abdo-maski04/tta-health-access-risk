"""Conteneur commun des visualisations."""

from __future__ import annotations

import html

import streamlit as st


def chart_card(title: str, figure=None, source: str | None = None):
    with st.container(border=True):
        st.markdown(
            f"<div class='tta-card-title'>{html.escape(title)}</div>",
            unsafe_allow_html=True,
        )
        if figure is not None:
            figure.update_layout(title=None)
            st.plotly_chart(
                figure,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
        else:
            st.markdown(
                "<div class='tta-table-empty'>Visualisation indisponible.</div>",
                unsafe_allow_html=True,
            )
        if source:
            st.caption(html.escape(source))
