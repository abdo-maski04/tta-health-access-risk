"""Charge la table accessibility.travel_time depuis le CSV v2 (tache 3, D-019).

Entree  : data/processed/travel_time_TTA_2024.csv (146 lignes, une par commune,
          methode ORS_DRIVING_CAR, version v2 retenue par D-019).
Sortie  : table accessibility.travel_time, exactement 146 lignes.

Usage, depuis la racine du depot :

    python -m scripts.load_travel_time

Le script :
  1. execute sql/travel_time.sql (creation du schema et de la table, idempotent) ;
  2. controle le CSV avant d'ecrire : 146 lignes, codes uniques, aucun temps
     manquant, bornes de classe respectees. Si un controle echoue, rien n'est ecrit ;
  3. remplace le contenu de la table (TRUNCATE + INSERT) dans une seule transaction ;
  4. affiche les compteurs de verification.

Aucun appel reseau. Ne modifie aucun fichier de src/tta_risk/weather/ ni danger.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.tta_risk.db.database import get_connection

CSV = Path("data/processed/travel_time_TTA_2024.csv")
DDL = Path("sql/travel_time.sql")
ATTENDU = 146
BORNE_1 = 15.0
BORNE_2 = 45.0

COLONNES = [
    "commune_code",
    "name_fr",
    "province",
    "milieu",
    "start_lat",
    "start_lon",
    "hospital_osm_type",
    "hospital_osm_id",
    "hospital_name",
    "hospital_lat",
    "hospital_lon",
    "distance_km",
    "temps_min",
    "classe_trajet",
    "methode",
]

INSERT = """
INSERT INTO accessibility.travel_time
    (commune_code, name_fr, province, milieu,
     start_lat, start_lon,
     hospital_osm_type, hospital_osm_id, hospital_name,
     hospital_lat, hospital_lon,
     distance_km, temps_min, classe_trajet, methode)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def classe(temps_min: float) -> int:
    """Meme regle que le module de scoring (D-015) : jamais 0."""
    if temps_min < BORNE_1:
        return 1
    if temps_min <= BORNE_2:
        return 2
    return 3


def lire_csv() -> pd.DataFrame:
    if not CSV.is_file():
        raise SystemExit(f"ERREUR : {CSV} introuvable. Lance ce script depuis la racine du depot.")
    donnees = pd.read_csv(CSV, dtype={"commune_code": str, "hospital_osm_id": str})
    manquantes = [colonne for colonne in COLONNES if colonne not in donnees.columns]
    if manquantes:
        raise SystemExit("ERREUR : colonne(s) absente(s) du CSV : " + ", ".join(manquantes))
    return donnees


def verifier(donnees: pd.DataFrame) -> None:
    """Arrete le chargement si le CSV n'est pas conforme. Rien n'est ecrit en cas d'echec."""
    problemes = []

    if len(donnees) != ATTENDU:
        problemes.append(f"{len(donnees)} lignes au lieu de {ATTENDU}")
    if donnees["commune_code"].duplicated().any():
        doublons = sorted(donnees.loc[donnees["commune_code"].duplicated(), "commune_code"])
        problemes.append(f"codes dupliques : {', '.join(doublons[:5])}")
    if donnees["temps_min"].isna().any():
        problemes.append(f"{int(donnees['temps_min'].isna().sum())} temps de trajet manquants")

    temps = donnees["temps_min"].dropna()
    if not temps.between(0, 600).all():
        problemes.append("temps de trajet hors de l'intervalle 0-600 minutes")

    renseignees = donnees.loc[donnees["temps_min"].notna()]
    desaccords = renseignees.loc[
        renseignees["temps_min"].map(classe) != renseignees["classe_trajet"], "commune_code"
    ]
    if len(desaccords):
        problemes.append(
            f"{len(desaccords)} commune(s) dont classe_trajet ne suit pas les bornes "
            f"{BORNE_1:g}/{BORNE_2:g} : {', '.join(sorted(desaccords)[:5])}"
        )

    if problemes:
        raise SystemExit(
            "ERREUR : CSV non conforme, rien n'a ete ecrit.\n  - " + "\n  - ".join(problemes)
        )


def main() -> None:
    donnees = lire_csv()
    verifier(donnees)

    lignes = [
        tuple(None if pd.isna(valeur) else valeur for valeur in ligne)
        for ligne in donnees[COLONNES].itertuples(index=False, name=None)
    ]

    ddl = DDL.read_text(encoding="utf-8") if DDL.is_file() else ""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if ddl:
                cursor.execute(ddl)
            cursor.execute("TRUNCATE accessibility.travel_time")
            cursor.executemany(INSERT, lignes)
            cursor.execute(
                "SELECT count(*), count(DISTINCT commune_code),"
                "       round(min(temps_min)::numeric, 1), round(max(temps_min)::numeric, 1)"
                " FROM accessibility.travel_time"
            )
            total, communes, mini, maxi = cursor.fetchone()
            cursor.execute(
                "SELECT classe_trajet, count(*) FROM accessibility.travel_time"
                " GROUP BY 1 ORDER BY 1"
            )
            repartition = cursor.fetchall()
        conn.commit()

    print(f"{total} lignes ecrites dans accessibility.travel_time (attendu : {ATTENDU})")
    print(f"{communes} communes distinctes")
    print(f"temps de trajet : {mini} a {maxi} minutes")
    print("repartition des classes (attendu : 18 / 66 / 62) :")
    for classe_trajet, nombre in repartition:
        print(f"  classe {classe_trajet} : {nombre}")


if __name__ == "__main__":
    main()
