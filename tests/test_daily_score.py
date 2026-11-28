"""Tests unitaires du calcul du score quotidien (D-018).

Aucune base, aucun reseau : on construit de petits DataFrames a la main.
"""

import pandas as pd
import pytest

from tta_risk.scoring.daily import ajouter_score, verifier_temps

pytestmark = pytest.mark.unit


def ligne(commune="MA-01-511-0100", rain=0, heat=0, temps=10.0):
    return {
        "commune_code": commune,
        "rain_level": rain,
        "heat_level": heat,
        "danger": max(rain, heat),
        "temps_min": temps,
    }


def scorer(**kwargs):
    return ajouter_score(pd.DataFrame([ligne(**kwargs)])).iloc[0]


def test_pluie_forte_et_commune_isolee_donnent_9_rouge():
    resultat = scorer(rain=3, temps=120.0)
    assert resultat["classe_trajet"] == 3
    assert resultat["score"] == 9
    assert resultat["niveau"] == "rouge"
    assert resultat["raison"] == "pluie"


def test_chaleur_moderee_et_trajet_moyen():
    resultat = scorer(heat=2, temps=20.0)
    assert resultat["classe_trajet"] == 2
    assert resultat["score"] == 4
    assert resultat["niveau"] == "orange"
    assert resultat["raison"] == "chaleur"


def test_sans_danger_la_raison_est_l_eloignement():
    resultat = scorer(temps=10.0)
    assert resultat["classe_trajet"] == 1
    assert resultat["score"] == 0
    assert resultat["niveau"] == "vert"
    assert resultat["raison"] == "eloignement"


def test_egalite_pluie_chaleur_l_ordre_departage_choisit_pluie():
    resultat = scorer(rain=2, heat=2, temps=10.0)
    assert resultat["danger"] == 2
    assert resultat["raison"] == "pluie"


@pytest.mark.parametrize(
    "temps,classe",
    [(0.1, 1), (14.9, 1), (15.0, 2), (45.0, 2), (45.1, 3), (120.2, 3)],
)
def test_bornes_15_45(temps, classe):
    assert scorer(temps=temps)["classe_trajet"] == classe


def test_temps_manquant_leve_une_erreur():
    with pytest.raises(ValueError):
        ajouter_score(pd.DataFrame([ligne(temps=float("nan"))]))


def test_verifier_temps_nomme_les_communes_sans_temps():
    df = pd.DataFrame([ligne(commune="A", temps=float("nan")), ligne(commune="B")])
    with pytest.raises(ValueError, match="A"):
        verifier_temps(df)


def test_verifier_temps_signale_une_colonne_manquante():
    with pytest.raises(ValueError, match="colonne manquante"):
        verifier_temps(pd.DataFrame([{"commune_code": "A"}]))


def test_personne_exposee_n_entre_pas_dans_le_score():
    # Deux communes de meme danger et meme temps : score identique, quelle que
    # soit leur population. La population est un axe separe (methodologie §4).
    deux = pd.DataFrame(
        [ligne(commune="A", rain=2, temps=20.0), ligne(commune="B", rain=2, temps=20.0)]
    )
    resultat = ajouter_score(deux)
    assert resultat["score"].tolist() == [4, 4]
