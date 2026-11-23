"""Module de scoring du risque d'acces aux soins — TTA.

Formule (voir docs/methodology.md) :

    danger_pluie   = niveau(pluie_prevue, [rain_p65, rain_p80, rain_p90])
    danger_chaleur = niveau(tmax_prevue,  [heat_p65, heat_p80, heat_p90])
    danger_meteo   = max(danger_pluie, danger_chaleur)
    classe_trajet  = 1 (< 15 min) | 2 (15-45 min) | 3 (> 45 min)
    score          = danger_meteo x classe_trajet     -> 0, 1, 2, 3, 4, 6, 9
    couleur        = vert 0 | jaune 1-2 | orange 3-4 | rouge 6-9
    raison         = composante dominante (egalite : pluie, puis chaleur, puis eloignement)
    personnes_exposees = population si rouge, sinon 0 (axe separe)
"""

from __future__ import annotations

import math

DEFAUTS = {
    "seuils": {
        "pluie": {"niveau_1": "rain_p65", "niveau_2": "rain_p80", "niveau_3": "rain_p90"},
        "chaleur": {"niveau_1": "heat_p65", "niveau_2": "heat_p80", "niveau_3": "heat_p90"},
    },
    "bornes_trajet": {"classe_1_max_min": 15.0, "classe_2_max_min": 45.0},
    "couleurs": {"vert": [0], "jaune": [1, 2], "orange": [3, 4], "rouge": [6, 9]},
}

ORDRE_DEPARTAGE = ("pluie", "chaleur", "eloignement")


def est_manquant(valeur) -> bool:
    """True si la valeur est absente (None ou NaN)."""
    if valeur is None:
        return True
    try:
        return math.isnan(float(valeur))
    except (TypeError, ValueError):
        return False


def charger_config(chemin=None) -> dict:
    """Lit config/scoring_config.yaml si PyYAML est installe, sinon utilise DEFAUTS."""
    if chemin is None:
        chemin = "config/scoring_config.yaml"
    try:
        import yaml
    except ImportError:
        return DEFAUTS
    try:
        with open(chemin, encoding="utf-8") as fichier:
            return yaml.safe_load(fichier)
    except FileNotFoundError:
        return DEFAUTS


def niveau(valeur, seuils) -> int:
    """Niveau 0 a 3 d'une valeur face a trois seuils croissants.

    `seuils` = (niveau_1, niveau_2, niveau_3). Un seuil absent est ignore.
    Une valeur absente, ou un seuil de niveau 1 absent, donne 0.
    """
    if est_manquant(valeur):
        return 0
    valeur = float(valeur)
    for rang, seuil in ((3, seuils[2]), (2, seuils[1]), (1, seuils[0])):
        if not est_manquant(seuil) and valeur >= float(seuil):
            return rang
    return 0


def classe_trajet(temps_min, bornes=None) -> int:
    """1 si < 15 min, 2 de 15 a 45 min, 3 au-dela. Jamais 0.

    Une duree inconnue leve ValueError : on ne fabrique pas une classe.
    """
    if est_manquant(temps_min):
        raise ValueError("temps de trajet inconnu : la classe ne peut pas etre calculee")
    if bornes is None:
        bornes = DEFAUTS["bornes_trajet"]
    temps_min = float(temps_min)
    if temps_min < float(bornes["classe_1_max_min"]):
        return 1
    if temps_min <= float(bornes["classe_2_max_min"]):
        return 2
    return 3


def score(danger_meteo: int, classe: int) -> int:
    """Score = danger x classe. Valeurs possibles : 0, 1, 2, 3, 4, 6, 9."""
    if not 0 <= danger_meteo <= 3:
        raise ValueError("danger_meteo doit etre entre 0 et 3")
    if not 1 <= classe <= 3:
        raise ValueError("classe de trajet doit etre entre 1 et 3")
    return int(danger_meteo) * int(classe)


def couleur(valeur_score: int, couleurs=None) -> str:
    """vert / jaune / orange / rouge."""
    if couleurs is None:
        couleurs = DEFAUTS["couleurs"]
    for nom, valeurs in couleurs.items():
        if int(valeur_score) in [int(v) for v in valeurs]:
            return nom
    raise ValueError(f"score impossible : {valeur_score}")


def raison(danger_pluie: int, danger_chaleur: int, classe: int) -> str:
    """Composante dominante : pluie, chaleur ou eloignement."""
    composantes = {"pluie": danger_pluie, "chaleur": danger_chaleur, "eloignement": classe}
    maximum = max(composantes.values())
    for nom in ORDRE_DEPARTAGE:
        if composantes[nom] == maximum:
            return nom
    raise AssertionError("inatteignable")


def personnes_exposees(population, niveau_couleur: str) -> int:
    """Population des communes rouges ; 0 sinon (axe separe, jamais multiplie)."""
    if niveau_couleur != "rouge" or est_manquant(population):
        return 0
    return int(population)


def scorer_commune(pluie_mm, tmax_c, temps_min, population=None,
                   seuils_pluie=(None, None, None), seuils_chaleur=(None, None, None),
                   config=None) -> dict:
    """Scoring complet d'une commune pour un jour donne."""
    if config is None:
        config = DEFAUTS
    bornes = config.get("bornes_trajet", DEFAUTS["bornes_trajet"])
    couleurs = config.get("couleurs", DEFAUTS["couleurs"])

    danger_pluie = niveau(pluie_mm, seuils_pluie)
    danger_chaleur = niveau(tmax_c, seuils_chaleur)
    danger_meteo = max(danger_pluie, danger_chaleur)
    classe = classe_trajet(temps_min, bornes)
    valeur = score(danger_meteo, classe)
    niveau_couleur = couleur(valeur, couleurs)

    return {
        "composante_pluie": danger_pluie,
        "composante_chaleur": danger_chaleur,
        "danger_meteo": danger_meteo,
        "classe_trajet": classe,
        "score": valeur,
        "niveau": niveau_couleur,
        "raison": raison(danger_pluie, danger_chaleur, classe),
        "personnes_exposees": personnes_exposees(population, niveau_couleur),
    }
