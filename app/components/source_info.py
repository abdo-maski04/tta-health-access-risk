"""Bloc d'information sur la source des donnees."""

from __future__ import annotations

import html

import streamlit as st


def source_info(source: str, reference: str | None = None, note: str | None = None) -> None:
    parts = [f"Source : {source}"]
    if reference:
        parts.append(f"Période/référence : {reference}")
    if note:
        parts.append(note)
    st.markdown(
        "<div class='tta-source'>"
        "<span class='tta-source-icon' aria-hidden='true'>i</span>"
        "<div class='tta-source-content'>"
        + "<br>".join(html.escape(part) for part in parts)
        + "</div></div>",
        unsafe_allow_html=True,
    )
