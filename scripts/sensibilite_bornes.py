"""Analyse de sensibilite des bornes de trajet (decision D-015).

Compare plusieurs decoupages du temps d'acces en trois classes et mesure leur
impact sur la repartition des communes et de la population.

Aucun appel reseau : tout derive de data/processed/travel_time_TTA_2024.csv.

Usage :
    python scripts/sensibilite_bornes.py

Sortie :
    data/processed/sensibilite_bornes.csv   (146 lignes, une colonne par variante)

Lecture : le classement des communes par temps d'acces ne depend pas des bornes ;
seules les etiquettes changent. La colonne nb_variantes_differentes compte combien
de variantes classent la commune autrement que le decoupage retenu (15/45 min).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RACINE = Path.cwd()
TRAVEL_TIME = RACINE / "data" / "processed" / "travel_time_TTA_2024.csv"
COMMUNES = RACINE / "data" / "processed" / "communes_TTA_2024.csv"
SORTIE = RACINE / "data" / "processed" / "sensibilite_bornes.csv"

RETENU = (15.0, 45.0)


def classes(temps, borne_1, borne_2):
    """Classe 1 sous borne_1, classe 2 jusqu'a borne_2, classe 3 au-dela."""
    return temps.map(lambda t: 1 if t < borne_1 else (2 if t <= borne_2 else 3))


def synthese(table, nom, bornes, colonne):
    """Affiche une ligne de synthese pour une variante de bornes."""
    valeurs = table[colonne]
    total = table.population_2024.sum()
    parts = [int((valeurs == i).sum()) for i in (1, 2, 3)]
    pops = [table.loc[valeurs == i, "population_2024"].sum() / total * 100 for i in (1, 2, 3)]
    changes = int((valeurs != table["classe_retenue"]).sum())
    print(
        f"{nom:<16} {bornes[0]:>5.1f}/{bornes[1]:<5.1f} | "
        f"{parts[0]:>3}/{parts[1]:>3}/{parts[2]:>3} | "
        f"{pops[0]:4.1f}/{pops[1]:4.1f}/{pops[2]:4.1f} % | "
        f"{changes:>3} communes"
    )


def main():
    """Construit la table de sensibilite et affiche la synthese."""
    if not TRAVEL_TIME.is_file() or not COMMUNES.is_file():
        print("ERREUR : fichiers absents de data/processed/")
        return 1

    temps = pd.read_csv(TRAVEL_TIME)
    communes = pd.read_csv(COMMUNES, usecols=["commune_code", "population_2024"])
    table = temps.merge(communes, on="commune_code", how="left")

    tercile_1 = round(float(table.temps_min.quantile(1 / 3)), 1)
    tercile_2 = round(float(table.temps_min.quantile(2 / 3)), 1)

    variantes = {
        "15_45": RETENU,
        "terciles": (tercile_1, tercile_2),
        "10_30": (10.0, 30.0),
        "20_60": (20.0, 60.0),
        "30_60": (30.0, 60.0),
        "15_60": (15.0, 60.0),
    }

    colonnes = ["commune_code", "name_fr", "province", "milieu", "population_2024", "temps_min"]
    resultat = table[colonnes].copy()
    for nom, bornes in variantes.items():
        resultat[f"classe_{nom}"] = classes(table.temps_min, *bornes).to_numpy()

    resultat["classe_retenue"] = resultat["classe_15_45"]
    colonnes_variantes = [f"classe_{nom}" for nom in variantes]
    resultat["nb_variantes_differentes"] = (
        resultat[colonnes_variantes].ne(resultat["classe_retenue"], axis=0).sum(axis=1)
    )
    resultat = resultat.sort_values("temps_min", ascending=False)
    resultat.to_csv(SORTIE, index=False, encoding="utf-8")

    print(f"{len(table)} communes | population {int(table.population_2024.sum())} habitants")
    print(f"terciles observes : {tercile_1} / {tercile_2} min")
    print("")
    print("variante         bornes      |  classes 1/2/3   |   population 1/2/3   | vs retenu")
    print("-----------------|------------------|----------------------|----------")
    for nom, bornes in variantes.items():
        synthese(resultat, nom, bornes, f"classe_{nom}")

    instables = int((resultat.nb_variantes_differentes > 0).sum())
    print("")
    print(f"communes dont la classe change selon la variante : {instables}")
    print(f"communes dans la meme classe partout            : {len(resultat) - instables}")
    print("")
    print("ecrit :", SORTIE, f"({len(resultat)} lignes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
