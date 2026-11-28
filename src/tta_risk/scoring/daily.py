"""Ajoute le score aux lignes de danger quotidien (module A, decision D-018).

Entree : un DataFrame contenant, pour chaque commune et chaque jour vise,
`rain_level`, `heat_level` et `danger` (produits par `danger.py`), plus le temps
de trajet `temps_min`.

Sortie : le meme DataFrame avec quatre colonnes de plus :

    classe_trajet   1 (moins de 15 min) / 2 (15 a 45 min) / 3 (plus de 45 min)
    score           danger x classe_trajet -> 0, 1, 2, 3, 4, 6, 9
    niveau          vert / jaune / orange / rouge
    raison          pluie / chaleur / eloignement  (facteur affiche, D-018)

Aucune base de donnees, aucun appel reseau : ce module est testable en unitaire.
"""

from __future__ import annotations

import pandas as pd

from .score import DEFAUTS, charger_config, classe_trajet, couleur, raison, score

CHEMIN_TRAJET = "data/processed/travel_time_TTA_2024.csv"
COLONNES_REQUISES = ("commune_code", "rain_level", "heat_level", "danger", "temps_min")


def charger_temps(chemin: str = CHEMIN_TRAJET) -> pd.DataFrame:
    """Deux colonnes : `commune_code` (texte) et `temps_min` (minutes)."""
    temps = pd.read_csv(
        chemin,
        usecols=["commune_code", "temps_min"],
        dtype={"commune_code": str},
    )
    return temps.drop_duplicates(subset="commune_code")


def verifier_temps(df: pd.DataFrame) -> None:
    """Leve ValueError si une commune n'a pas de temps de trajet.

    On ne fabrique pas une classe de trajet : une commune sans temps est une
    erreur de donnees, pas un cas normal.
    """
    for colonne in COLONNES_REQUISES:
        if colonne not in df.columns:
            raise ValueError(f"colonne manquante : {colonne}")
    manquantes = sorted(set(df.loc[df["temps_min"].isna(), "commune_code"]))
    if manquantes:
        raise ValueError(
            f"{len(manquantes)} commune(s) sans temps de trajet : " + ", ".join(manquantes)
        )


def ajouter_score(df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    """Ajoute `classe_trajet`, `score`, `niveau` et `raison` au DataFrame."""
    if config is None:
        config = charger_config()
    bornes = config.get("bornes_trajet", DEFAUTS["bornes_trajet"])
    couleurs = config.get("couleurs", DEFAUTS["couleurs"])

    resultat = df.copy()
    classes: list[int] = []
    valeurs: list[int] = []
    niveaux: list[str] = []
    raisons: list[str] = []

    for ligne in resultat.itertuples(index=False):
        classe = classe_trajet(ligne.temps_min, bornes)
        valeur = score(int(ligne.danger), classe)
        classes.append(classe)
        valeurs.append(valeur)
        niveaux.append(couleur(valeur, couleurs))
        raisons.append(raison(int(ligne.rain_level), int(ligne.heat_level), classe))

    resultat["classe_trajet"] = classes
    resultat["score"] = valeurs
    resultat["niveau"] = niveaux
    resultat["raison"] = raisons
    return resultat
