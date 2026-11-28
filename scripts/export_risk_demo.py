"""Exporte une journee "type" du risque d'acces aux soins (tache T9).

Le pipeline quotidien (`scripts/run_risk_daily.py`) travaille sur les previsions
des 3 prochains jours. Pour le rapport et la demonstration, on a besoin d'une
journee REELLE, avec de la pluie, et d'un fichier lisible dans Excel.

Ce script rejoue donc le score sur une journee passee de `weather.weather_daily`
(pluie et temperature reellement observees) :

    meteo observee + seuils du mois -> compute_danger (module de B, inchange)
    temps de trajet (CSV)           -> classe_trajet / score / niveau / raison

Deux usages, depuis la racine du depot :

    python -m scripts.export_risk_demo              # liste les 15 journees les plus pluvieuses
    python -m scripts.export_risk_demo 2024-11-19   # ecrit data/processed/risk_demo_2024-11-19.csv

Aucun fichier de `src/tta_risk/weather/` ni `scoring/danger.py` n'est modifie.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from src.tta_risk.scoring.daily import ajouter_score, charger_temps, verifier_temps

from src.tta_risk.db.database import get_connection
from src.tta_risk.scoring.danger import compute_danger
from src.tta_risk.scoring.score import personnes_exposees

REFERENTIEL = Path("data/processed/communes_TTA_2024.csv")
DOSSIER_SORTIE = Path("data/processed")

COLONNES_SORTIE = [
    "commune_code",
    "name_fr",
    "province",
    "milieu",
    "population_2024",
    "precip_mm",
    "tmax_c",
    "rain_level",
    "heat_level",
    "danger",
    "dominant",
    "temps_min",
    "classe_trajet",
    "score",
    "niveau",
    "raison",
    "personnes_exposees",
]

REQUETE_JOURNEE = """
    SELECT w.commune_code,
           w.date AS target_date,
           w.precipitation_sum AS precip_mm,
           w.temperature_2m_max AS tmax_c,
           t.rain_p65, t.rain_p80, t.rain_p90,
           t.heat_p65, t.heat_p80, t.heat_p90
    FROM weather.weather_daily w
    JOIN weather.thresholds t
      ON t.commune_code = w.commune_code
     AND t.month = EXTRACT(MONTH FROM w.date)::int
    WHERE w.date = %s
    ORDER BY w.commune_code
"""

REQUETE_DATES = """
    SELECT date,
           COUNT(*) FILTER (WHERE precipitation_sum >= 10) AS communes_10mm,
           ROUND(MAX(precipitation_sum)::numeric, 1)       AS pluie_max_mm,
           ROUND(SUM(precipitation_sum)::numeric, 0)       AS pluie_totale_mm
    FROM weather.weather_daily
    GROUP BY date
    HAVING COUNT(*) FILTER (WHERE precipitation_sum >= 10) > 0
    ORDER BY communes_10mm DESC, pluie_totale_mm DESC
    LIMIT %s
"""


def _lire(requete: str, parametres: tuple) -> pd.DataFrame:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(requete, parametres)
            colonnes = [col.name for col in cursor.description]
            donnees = cursor.fetchall()
    return pd.DataFrame(donnees, columns=colonnes)


def dates_pluvieuses(limite: int = 15) -> pd.DataFrame:
    """Les journees ou la pluie a touche le plus de communes."""
    return _lire(REQUETE_DATES, (limite,))


def charger_journee(jour: str) -> pd.DataFrame:
    """Meteo observee d'une journee, jointe aux seuils du mois."""
    donnees = _lire(REQUETE_JOURNEE, (jour,))
    if donnees.empty:
        raise SystemExit(
            f"Aucune donnee pour le {jour}. Verifie la date (format AAAA-MM-JJ) "
            "et que l'historique couvre bien cette annee."
        )
    return donnees


def enrichir(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute nom, province, milieu et population depuis le referentiel."""
    referentiel = pd.read_csv(
        REFERENTIEL,
        usecols=["commune_code", "name_fr", "province", "milieu", "population_2024"],
        dtype={"commune_code": str},
    )
    return df.merge(referentiel, on="commune_code", how="left", validate="many_to_one")


def construire(jour: str) -> pd.DataFrame:
    """Journee complete : danger + score + population exposee."""
    resultat = compute_danger(charger_journee(jour))
    resultat = resultat.merge(
        charger_temps(), on="commune_code", how="left", validate="many_to_one"
    )
    verifier_temps(resultat)
    resultat = ajouter_score(resultat)
    resultat = enrichir(resultat)
    resultat["personnes_exposees"] = [
        personnes_exposees(population, couleur)
        for population, couleur in zip(resultat["population_2024"], resultat["niveau"])
    ]
    return resultat[COLONNES_SORTIE]


def resumer(resultat: pd.DataFrame, jour: str) -> None:
    print(f"Journee du {jour} : {len(resultat)} communes")
    print("niveau :")
    print(
        resultat["niveau"]
        .value_counts()
        .reindex(["rouge", "orange", "jaune", "vert"])
        .fillna(0)
        .astype(int)
        .to_string()
    )
    print("score :")
    print(resultat["score"].value_counts().sort_index().to_string())
    print("raison (communes non vertes) :")
    non_vertes = resultat[resultat["niveau"] != "vert"]
    if non_vertes.empty:
        print("  aucune commune en jaune, orange ou rouge ce jour-la")
    else:
        print(non_vertes["raison"].value_counts().to_string())
    print(f"Personnes en rouge : {int(resultat['personnes_exposees'].sum()):,}".replace(",", " "))
    print("\n10 communes les plus exposees :")
    colonnes = ["name_fr", "precip_mm", "temps_min", "danger", "score", "niveau", "raison"]
    print(resultat.sort_values("score", ascending=False).head(10)[colonnes].to_string(index=False))


def main() -> None:
    if len(sys.argv) < 2:
        print("Journees les plus pluvieuses de l'historique :\n")
        print(dates_pluvieuses().to_string(index=False))
        print("\nChoisis une date, puis :")
        print("    python -m scripts.export_risk_demo 2024-11-19")
        return

    jour = sys.argv[1]
    resultat = construire(jour)
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    sortie = DOSSIER_SORTIE / f"risk_demo_{jour}.csv"
    resultat.to_csv(sortie, index=False, encoding="utf-8")
    resumer(resultat, jour)
    print(f"\nFichier ecrit : {sortie}")


if __name__ == "__main__":
    main()
