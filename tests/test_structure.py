"""
Tests structurels de base pour le projet TTA Health Access Risk.
Vérifie la découvrabilité des modules Python et des répertoires clés.
"""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_project_root_structure():
    """Vérifie la présence des répertoires fondamentaux du projet."""
    root = Path(__file__).resolve().parents[1]
    expected_dirs = [
        "src/tta_risk",
        "data",
        "requirements",
        "tests",
        "docs",
    ]
    for d in expected_dirs:
        dir_path = root / d
        assert dir_path.is_dir(), f"Le dossier attendu '{d}' est manquant dans {root}."


@pytest.mark.unit
def test_import_package():
    """Vérifie que le package principal src/tta_risk peut être importé."""
    import tta_risk
    assert tta_risk is not None
