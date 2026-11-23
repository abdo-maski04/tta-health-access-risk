"""Etats visuels uniformes pour les donnees et erreurs."""

from __future__ import annotations

import html

import streamlit as st


def empty_state(title: str, message: str) -> None:
    st.markdown(
        "<div class='tta-empty'>"
        f"<div class='tta-empty-title'>{html.escape(title)}</div>"
        f"{html.escape(message)}"
        "</div>",
        unsafe_allow_html=True,
    )


def unavailable_state(title: str, dependency: str) -> None:
    empty_state(title, f"Données non disponibles — dépendance requise : {dependency}")


def error_state(message: str) -> None:
    st.error(message)


def loading_state(message: str = "Chargement des données...") -> None:
    st.caption(html.escape(message))
