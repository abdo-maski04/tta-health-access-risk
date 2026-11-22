"""Construit la table travel_time des 146 communes de TTA (version 2024).

Pour chaque commune : hopital le plus proche joignable en voiture, distance
routiere et duree reelles (API OpenRouteService / HeiGIT), plus le trace de
l'itineraire dans un GeoJSON.

Usage :
    python scripts/build_travel_time.py            # 146 communes via ORS
    python scripts/build_travel_time.py --limit 5  # test sur 5 communes
    python scripts/build_travel_time.py --approx   # sans reseau (plan B)

Sans cle ORS (variable ORS_API_KEY dans .env) ou si le reseau echoue, le
script bascule sur une estimation a vol d'oiseau (methode DETOUR_1.4).
Les reponses sont mises en cache dans cache_ors/ : relancer le script ne
rejoue que les communes manquantes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import pandas as pd

RACINE = Path.cwd()
COMMUNES = RACINE / "data" / "processed" / "communes_TTA_2024.csv"
HOPITAUX = RACINE / "data" / "processed" / "health_facilities_TTA.csv"
SORTIE_CSV = RACINE / "data" / "processed" / "travel_time_TTA_2024.csv"
SORTIE_GEOJSON = RACINE / "data" / "processed" / "travel_routes_TTA.geojson"
CACHE = RACINE / "cache_ors"

BASE = "https://api.heigit.org/openrouteservice/v2"
K = 5
FACTEUR_DETOUR = 1.4
VITESSE = 50.0
PAUSE = 3.0
ESSAIS = 3
RAYONS = (None, 5000, 20000)  # rayon de recherche d'une route (m)


def haversine(lat1, lon1, lat2, lon2):
    """Distance en km a vol d'oiseau entre deux points."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2
    a += math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def classe(temps):
    """1 = moins de 15 min, 2 = 15 a 45 min, 3 = plus de 45 min."""
    if temps < 15:
        return 1
    return 2 if temps <= 45 else 3


def cle():
    """Lit ORS_API_KEY dans .env a la racine du depot."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return os.getenv("ORS_API_KEY") or None
    load_dotenv(RACINE / ".env")
    return os.getenv("ORS_API_KEY") or None


def itineraire(session, token, origine, hopital):
    """Renvoie la feature GeoJSON de l'itineraire, ou None si non joignable.

    ORS n'accepte par defaut qu'un point a moins de 350 m d'une route. Certains
    chefs-lieux ruraux en sont plus loin : on elargit alors le rayon.
    """
    coordonnees = [[origine[1], origine[0]], [hopital["lon"], hopital["lat"]]]
    entetes = {"Authorization": token, "Content-Type": "application/json"}
    for rayon in RAYONS:
        payload = {"coordinates": coordonnees}
        if rayon is not None:
            payload["radiuses"] = [rayon, rayon]
        for essai in range(1, ESSAIS + 1):
            try:
                rep = session.post(
                    BASE + "/directions/driving-car/geojson",
                    json=payload,
                    headers=entetes,
                    timeout=90,
                )
            except Exception as err:  # noqa: BLE001
                if essai == ESSAIS:
                    raise RuntimeError(f"reseau injoignable ({err})") from err
                print(f"      {err}, nouvel essai dans 5s")
                time.sleep(5 * essai)
                continue
            if rep.status_code == 200:
                return rep.json()["features"][0]
            if rep.status_code == 403:
                raise RuntimeError("quota ORS epuise ou cle refusee (403)")
            if rep.status_code == 429:
                print("      limite de debit atteinte, pause de 30s")
                time.sleep(30)
                continue
            if rep.status_code == 404:
                if "2010" in rep.text:
                    break  # point trop loin d'une route : on elargit le rayon
                return None  # aucune route entre ces deux points
            if essai == ESSAIS:
                raise RuntimeError(f"ORS indisponible ({rep.status_code})")
            print(f"      HTTP {rep.status_code}, nouvel essai dans 5s")
            time.sleep(5 * essai)
    return None


def par_ors(session, token, origine, candidats):
    """Essaie les 5 hopitaux les plus proches jusqu'a en trouver un joignable."""
    proches = sorted(
        candidats,
        key=lambda h: haversine(origine[0], origine[1], h["lat"], h["lon"]),
    )
    for hopital in proches:
        feature = itineraire(session, token, origine, hopital)
        if feature is None:
            continue
        resume = feature["properties"]["summary"]
        return {
            "hopital": hopital,
            "temps_min": round(resume["duration"] / 60, 1),
            "distance_km": round(resume["distance"] / 1000, 2),
            "trace": feature["geometry"]["coordinates"],
            "methode": "ORS_DRIVING_CAR",
        }
    raise RuntimeError("aucun des 5 hopitaux n'est joignable")


def par_estimation(candidats, origine):
    """Plan B : vol d'oiseau x facteur de detour, a 50 km/h."""
    distances = sorted(
        (haversine(origine[0], origine[1], h["lat"], h["lon"]), i) for i, h in enumerate(candidats)
    )
    km = distances[0][0] * FACTEUR_DETOUR
    return {
        "hopital": candidats[distances[0][1]],
        "temps_min": round(km / VITESSE * 60, 1),
        "distance_km": round(distances[0][0], 2),
        "trace": None,
        "methode": "DETOUR_1.4",
    }


def main():
    """Point d'entree du script."""
    parseur = argparse.ArgumentParser()
    parseur.add_argument("--limit", type=int, default=0, help="ne traiter que N communes")
    parseur.add_argument("--approx", action="store_true", help="forcer le plan B (sans reseau)")
    args = parseur.parse_args()

    if not COMMUNES.is_file() or not HOPITAUX.is_file():
        print("ERREUR : fichiers sources absents de data/processed/")
        return 1

    communes = pd.read_csv(COMMUNES)
    etablissements = pd.read_csv(HOPITAUX)
    hopitaux = etablissements[etablissements["facility_type"] == "hospital"].copy()
    hopitaux["name"] = hopitaux["name"].fillna("(sans nom)")
    print(f"{len(communes)} communes | {len(hopitaux)} hopitaux")

    token = None if args.approx else cle()
    session = None
    if token:
        import requests

        session = requests.Session()
    print("mode :", "ORS" if token else "APPROX (plan B)")
    if args.limit:
        communes = communes.head(args.limit)

    CACHE.mkdir(exist_ok=True)
    lignes, traces, echecs, cache_hits, dernier = [], [], 0, 0, 0.0

    for n, commune in enumerate(communes.itertuples(), start=1):
        origine = (float(commune.start_lat), float(commune.start_lon))
        proches = sorted(
            (
                haversine(origine[0], origine[1], h.lat, h.lon),
                i,
            )
            for i, h in hopitaux.iterrows()
        )[:K]
        candidats = [
            {
                "osm_type": hopitaux.at[i, "osm_type"],
                "osm_id": int(hopitaux.at[i, "osm_id"]),
                "name": hopitaux.at[i, "name"],
                "lat": float(hopitaux.at[i, "lat"]),
                "lon": float(hopitaux.at[i, "lon"]),
            }
            for _, i in proches
        ]

        fichier = CACHE / f"{commune.commune_code}.json"
        if fichier.is_file():
            resultat = json.loads(fichier.read_text(encoding="utf-8"))
            cache_hits += 1
        elif token:
            try:
                attente = PAUSE - (time.time() - dernier)
                if attente > 0:
                    time.sleep(attente)
                resultat = par_ors(session, token, origine, candidats)
                dernier = time.time()
                fichier.write_text(json.dumps(resultat, ensure_ascii=False), encoding="utf-8")
            except Exception as err:  # noqa: BLE001
                echecs += 1
                print(f"  ! {commune.commune_code} : {err} -> plan B")
                resultat = par_estimation(candidats, origine)
        else:
            resultat = par_estimation(candidats, origine)

        hopital = resultat["hopital"]
        lignes.append(
            {
                "commune_code": commune.commune_code,
                "name_fr": commune.name_fr,
                "province": commune.province,
                "milieu": commune.milieu,
                "start_lat": round(origine[0], 6),
                "start_lon": round(origine[1], 6),
                "hospital_osm_type": hopital["osm_type"],
                "hospital_osm_id": hopital["osm_id"],
                "hospital_name": hopital["name"],
                "hospital_lat": hopital["lat"],
                "hospital_lon": hopital["lon"],
                "distance_km": resultat["distance_km"],
                "temps_min": resultat["temps_min"],
                "classe_trajet": classe(resultat["temps_min"]),
                "methode": resultat["methode"],
            }
        )
        if resultat.get("trace"):
            traces.append(
                {
                    "type": "Feature",
                    "properties": {
                        "commune_code": commune.commune_code,
                        "name_fr": commune.name_fr,
                        "hospital_name": hopital["name"],
                        "temps_min": resultat["temps_min"],
                        "distance_km": resultat["distance_km"],
                    },
                    "geometry": {"type": "LineString", "coordinates": resultat["trace"]},
                }
            )
        if n % 10 == 0 or n == len(communes):
            print(f"  {n}/{len(communes)}")

    table = pd.DataFrame(lignes)
    SORTIE_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(SORTIE_CSV, index=False, encoding="utf-8")
    if traces:
        SORTIE_GEOJSON.write_text(
            json.dumps({"type": "FeatureCollection", "features": traces}, ensure_ascii=False),
            encoding="utf-8",
        )
    print("")
    print("ecrit :", SORTIE_CSV, f"({len(table)} lignes)")
    if traces:
        print("ecrit :", SORTIE_GEOJSON, f"({len(traces)} traces)")
    print("cache :", cache_hits, "| plan B :", echecs)
    if len(table):
        print(
            "temps min. median / max :",
            round(table.temps_min.min(), 1),
            round(table.temps_min.median(), 1),
            round(table.temps_min.max(), 1),
        )
        print("classes :", table.classe_trajet.value_counts().sort_index().to_dict())
        print("methodes :", table.methode.value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
