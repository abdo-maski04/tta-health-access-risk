"""Zones d'accessibilite aux soins : 15, 30, 45 et 60 minutes.

Pour chaque commune, indique si son hopital le plus proche est atteignable
en moins de 15, 30, 45 ou 60 minutes, et dans quelle zone elle se situe.
Agrege ensuite les communes et la population par zone.

Aucun appel reseau : le script derive tout de la table travel_time deja
calculee (voir scripts/build_travel_time.py).

Usage :
    python scripts/build_access_zones.py

Sortie :
    data/processed/access_zones_TTA.csv   (146 lignes)

Reference : docs/methodology.md, section accessibilite.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RACINE = Path.cwd()
TRAVEL_TIME = RACINE / "data" / "processed" / "travel_time_TTA_2024.csv"
COMMUNES = RACINE / "data" / "processed" / "communes_TTA_2024.csv"
SORTIE = RACINE / "data" / "processed" / "access_zones_TTA.csv"

SEUILS = (15, 30, 45, 60)


def zone(temps):
    """Etiquette de zone : la premiere borne atteinte, sinon 'hors zone'."""
    for seuil in SEUILS:
        if temps <= seuil:
            return f"moins de {seuil} min"
    return "plus de 60 min"


def main():
    """Construit la table des zones d'accessibilite et affiche la synthese."""
    if not TRAVEL_TIME.is_file() or not COMMUNES.is_file():
        print("ERREUR : fichiers absents de data/processed/")
        return 1

    temps = pd.read_csv(TRAVEL_TIME)
    communes = pd.read_csv(COMMUNES, usecols=["commune_code", "population_2024", "part_rurale_pct"])
    table = temps.merge(communes, on="commune_code", how="left")

    table = table[
        [
            "commune_code",
            "name_fr",
            "province",
            "milieu",
            "population_2024",
            "temps_min",
            "distance_km",
            "hospital_name",
        ]
    ].copy()

    for seuil in SEUILS:
        table[f"zone_{seuil}_min"] = (table.temps_min <= seuil).astype(int)
    table["zone"] = table.temps_min.map(zone)

    table = table.sort_values("temps_min", ascending=False)
    table.to_csv(SORTIE, index=False, encoding="utf-8")

    total_communes = len(table)
    total_population = int(table.population_2024.sum())

    print(f"{total_communes} communes | population {total_population} habitants")
    print("")
    print("seuil  | communes |  part  |  population |  part")
    print("-------|----------|--------|-------------|-------")
    for seuil in SEUILS:
        atteint = table.temps_min <= seuil
        nombre = int(atteint.sum())
        population = int(table.loc[atteint, "population_2024"].sum())
        print(
            f"{seuil:>4} m | {nombre:>8} | {nombre / total_communes:5.1%} | "
            f"{population:>11} | {population / total_population:5.1%}"
        )
    hors = table.temps_min > SEUILS[-1]
    print(
        f"  hors | {int(hors.sum()):>8} | {hors.sum() / total_communes:5.1%} | "
        f"{int(table.loc[hors, 'population_2024'].sum()):>11} | "
        f"{table.loc[hors, 'population_2024'].sum() / total_population:5.1%}"
    )
    print("")
    print("ecrit :", SORTIE, f"({len(table)} lignes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
