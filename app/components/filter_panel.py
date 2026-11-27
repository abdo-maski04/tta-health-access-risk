"""Panneau de filtres reutilisable."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import streamlit as st


def multiselect_filter(
    label: str,
    options: Iterable[Any],
    key: str,
    container=None,
) -> list[Any]:
    target = container if container is not None else st.sidebar
    return target.multiselect(label, options=sorted(set(options)), key=key)
