"""Table travel_time : 146 communes -> hopital le plus proche (OpenRouteService).

Usage (depuis la racine du depot) :
    python build_travel_time.py --limit 3   # test sur 3 communes
    python build_travel_time.py             # les 146 communes
    python build_travel_time.py --approx    # sans cle ORS (plan B)

Sorties :
    data/processed/travel_time_TTA_2024.csv
    data/processed/travel_routes_TTA.geojson
    cache_ors/   (cache local, ignore par git : relancer ne consomme pas de quota)
"""

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

BASES = ["https://api.heigit.org/v2", "https://api.openrouteservice.org/v2"]
K = 5
FACTEUR_DETOUR = 1.4
VITESSE = 50.0
PAUSE = 1.6
ESSAIS = 3


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def classe(temps):
    if temps < 15:
        return 1
    return 2 if temps <= 45 else 3


def cle():
    try:
        from dotenv import load_dotenv
        load_dotenv(RACINE / ".env")
    except ImportError:
        pass
    return os.getenv("ORS_API_KEY") or None


def poster(session, chemin, payload, token):
    for essai in range(1, ESSAIS + 1):
        for base in BASES:
            rep = session.post(base + chemin, json=payload, timeout=60,
                               headers={"Authorization": token, "Content-Type": "application/json"})
            if rep.status_code == 200:
                return rep.json()
            if rep.status_code in (401, 403):
                raise RuntimeError(f"cle ORS refusee ({rep.status_code})")
        if essai < ESSAIS:
            print(f"      erreur {rep.status_code}, nouvel essai dans 5s")
            time.sleep(5 * essai)
    raise RuntimeError(f"ORS indisponible ({rep.status_code})")


def par_ors(session, token, origine, candidats):
    payload = {
        "locations": [[origine[1], origine[0]]] + [[h["lon"], h["lat"]] for h in candidats],
        "sources": [0],
        "destinations": list(range(1, len(candidats) + 1)),
        "metrics": ["distance", "duration"],
        "units": "m",
    }
    data = poster(session, "/matrix/driving-car", payload, token)
    durees = data["durations"][0]
    i = min(range(len(candidats)), key=lambda k: durees[k] if durees[k] is not None else 9e9)
    if durees[i] is None:
        raise RuntimeError("aucun hopital joignable")
    hopital = candidats[i]
    data = poster(session, "/directions/driving-car/geojson",
                  {"coordinates": [[origine[1], origine[0]], [hopital["lon"], hopital["lat"]]]}, token)
    f = data["features"][0]["properties"]["summary"]
    return {"hopital": hopital, "temps_min": round(f["duration"] / 60, 1),
            "distance_km": round(f["distance"] / 1000, 2),
            "trace": data["features"][0]["geometry"]["coordinates"], "methode": "ORS_DRIVING_CAR"}


def par_estimation(candidats, origine):
    d = [(haversine(origine[0], origine[1], h["lat"], h["lon"]), i) for i, h in enumerate(candidats)]
    d.sort()
    km = d[0][0] * FACTEUR_DETOUR
    return {"hopital": candidats[d[0][1]], "temps_min": round(km / VITESSE * 60, 1),
            "distance_km": round(d[0][0], 2), "trace": None, "methode": "DETOUR_1.4"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--approx", action="store_true")
    args = p.parse_args()

    if not COMMUNES.is_file() or not HOPITAUX.is_file():
        print("ERREUR : fichiers sources absents de data/processed/")
        return 1

    communes = pd.read_csv(COMMUNES)
    etab = pd.read_csv(HOPITAUX)
    hopitaux = etab[etab["facility_type"] == "hospital"].copy()
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

    for n, c in enumerate(communes.itertuples(), start=1):
        origine = (float(c.start_lat), float(c.start_lon))
        proches = sorted(((haversine(origine[0], origine[1], h.lat, h.lon), i)
                          for i, h in hopitaux.iterrows()))[:K]
        candidats = [{"osm_type": hopitaux.at[i, "osm_type"], "osm_id": int(hopitaux.at[i, "osm_id"]),
                      "name": hopitaux.at[i, "name"], "lat": float(hopitaux.at[i, "lat"]),
                      "lon": float(hopitaux.at[i, "lon"])} for _, i in proches]

        fichier = CACHE / f"{c.commune_code}.json"
        if token and fichier.is_file():
            res = json.loads(fichier.read_text(encoding="utf-8"))
            cache_hits += 1
        elif token:
            try:
                attente = PAUSE - (time.time() - dernier)
                if attente > 0:
                    time.sleep(attente)
                res = par_ors(session, token, origine, candidats)
                dernier = time.time()
                fichier.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
            except Exception as err:
                echecs += 1
                print(f"  ! {c.commune_code} : {err} -> plan B")
                res = par_estimation(candidats, origine)
        else:
            res = par_estimation(candidats, origine)

        h = res["hopital"]
        lignes.append({
            "commune_code": c.commune_code, "name_fr": c.name_fr, "province": c.province,
            "milieu": c.milieu, "start_lat": round(origine[0], 6), "start_lon": round(origine[1], 6),
            "hospital_osm_type": h["osm_type"], "hospital_osm_id": h["osm_id"],
            "hospital_name": h["name"], "hospital_lat": h["lat"], "hospital_lon": h["lon"],
            "distance_km": res["distance_km"], "temps_min": res["temps_min"],
            "classe_trajet": classe(res["temps_min"]), "methode": res["methode"],
        })
        if res.get("trace"):
            traces.append({"type": "Feature", "properties": {
                "commune_code": c.commune_code, "name_fr": c.name_fr, "hospital_name": h["name"],
                "temps_min": res["temps_min"], "distance_km": res["distance_km"]},
                "geometry": {"type": "LineString", "coordinates": res["trace"]}})
        if n % 10 == 0 or n == len(communes):
            print(f"  {n}/{len(communes)}")

    table = pd.DataFrame(lignes)
    SORTIE_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(SORTIE_CSV, index=False, encoding="utf-8")
    if traces:
        SORTIE_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": traces},
                                             ensure_ascii=False), encoding="utf-8")
    print("")
    print("ecrit :", SORTIE_CSV, f"({len(table)} lignes)")
    if traces:
        print("ecrit :", SORTIE_GEOJSON, f"({len(traces)} traces)")
    print("cache :", cache_hits, "| plan B :", echecs)
    if len(table):
        print("temps min. median / max :", round(table.temps_min.min(), 1),
              round(table.temps_min.median(), 1), round(table.temps_min.max(), 1))
        print("classes :", table.classe_trajet.value_counts().sort_index().to_dict())
        print("methodes :", table.methode.value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
