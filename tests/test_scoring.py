"""Tests unitaires du module de scoring (aucune base, aucun reseau)."""

import pytest

from tta_risk.scoring.score import (
    classe_trajet,
    couleur,
    niveau,
    personnes_exposees,
    raison,
    score,
    scorer_commune,
)

pytestmark = pytest.mark.unit

SEUILS = (12.0, 20.0, 30.0)  # p65, p80, p90


# --------------------------------------------------------------- etape 1 : danger


def test_sous_le_premier_seuil_donne_zero():
    assert niveau(5.0, SEUILS) == 0


def test_egal_au_premier_seuil_donne_un():
    assert niveau(12.0, SEUILS) == 1


def test_entre_p65_et_p80_donne_un():
    assert niveau(15.0, SEUILS) == 1


def test_egal_au_deuxieme_seuil_donne_deux():
    assert niveau(20.0, SEUILS) == 2


def test_egal_au_troisieme_seuil_donne_trois():
    assert niveau(30.0, SEUILS) == 3


def test_tres_au_dessus_donne_trois():
    assert niveau(80.0, SEUILS) == 3


def test_seuil_absent_donne_zero():
    assert niveau(50.0, (None, None, None)) == 0


def test_valeur_absente_donne_zero():
    assert niveau(None, SEUILS) == 0


# --------------------------------------------------------------- etape 2 : trajet


@pytest.mark.parametrize(
    "temps,classe",
    [
        (0.5, 1),
        (10.0, 1),
        (14.9, 1),
        (15.0, 2),
        (30.0, 2),
        (45.0, 2),
        (45.1, 3),
        (77.7, 3),
    ],
)
def test_classes_de_trajet(temps, classe):
    assert classe_trajet(temps) == classe


def test_classe_jamais_nulle_et_erreur_si_inconnu():
    with pytest.raises(ValueError):
        classe_trajet(None)


# --------------------------------------------------------------- etape 3 : score


@pytest.mark.parametrize(
    "danger,classe,attendu",
    [
        (0, 3, 0),
        (1, 1, 1),
        (1, 3, 3),
        (2, 2, 4),
        (2, 3, 6),
        (3, 3, 9),
    ],
)
def test_produit_danger_par_classe(danger, classe, attendu):
    assert score(danger, classe) == attendu


def test_les_scores_impossibles_sont_refuses():
    with pytest.raises(ValueError):
        score(4, 1)
    with pytest.raises(ValueError):
        score(1, 0)


# --------------------------------------------------------------- etape 4 : couleur


@pytest.mark.parametrize(
    "valeur,attendu",
    [
        (0, "vert"),
        (1, "jaune"),
        (2, "jaune"),
        (3, "orange"),
        (4, "orange"),
        (6, "rouge"),
        (9, "rouge"),
    ],
)
def test_couleurs(valeur, attendu):
    assert couleur(valeur) == attendu


def test_couleur_impossible():
    with pytest.raises(ValueError):
        couleur(5)


# --------------------------------------------------------------- raison et population


def test_raison_pluie_quand_elle_domine():
    assert raison(3, 1, 2) == "pluie"


def test_raison_chaleur_quand_elle_domine():
    assert raison(1, 3, 2) == "chaleur"


def test_raison_eloignement_quand_il_domine():
    assert raison(1, 1, 3) == "eloignement"


def test_egalite_pluie_avant_chaleur():
    assert raison(3, 3, 1) == "pluie"


def test_egalite_pluie_avant_eloignement():
    assert raison(3, 1, 3) == "pluie"


def test_population_seulement_si_rouge():
    assert personnes_exposees(300000, "rouge") == 300000
    assert personnes_exposees(300000, "orange") == 0


# --------------------------------------------------------------- cas complet


def test_commune_pluvieuse_et_isolee_donne_rouge():
    resultat = scorer_commune(
        pluie_mm=45.0,
        tmax_c=25.0,
        temps_min=60.0,
        population=25000,
        seuils_pluie=SEUILS,
        seuils_chaleur=(30.0, 34.0, 38.0),
    )
    assert resultat["danger_meteo"] == 3
    assert resultat["classe_trajet"] == 3
    assert resultat["score"] == 9
    assert resultat["niveau"] == "rouge"
    assert resultat["raison"] == "pluie"
    assert resultat["personnes_exposees"] == 25000


def test_commune_par_beau_temps_reste_verte_meme_isolee():
    resultat = scorer_commune(
        pluie_mm=1.0,
        tmax_c=22.0,
        temps_min=90.0,
        population=800,
        seuils_pluie=SEUILS,
        seuils_chaleur=(30.0, 34.0, 38.0),
    )
    assert resultat["danger_meteo"] == 0
    assert resultat["score"] == 0
    assert resultat["niveau"] == "vert"
    assert resultat["raison"] == "eloignement"
    assert resultat["personnes_exposees"] == 0


def test_commune_proche_sous_la_pluie_reste_jaune():
    resultat = scorer_commune(
        pluie_mm=45.0,
        tmax_c=22.0,
        temps_min=8.0,
        seuils_pluie=SEUILS,
        seuils_chaleur=(30.0, 34.0, 38.0),
    )
    assert resultat["danger_meteo"] == 3
    assert resultat["score"] == 3
    assert resultat["niveau"] == "orange"
