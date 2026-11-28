"""Construit et met a jour la table travel_time des 146 communes de TTA (version 2024).

Pour chaque commune : hopital le plus proche joignable en voiture, distance
routiere et duree reelles (API OpenRouteService / HeiGIT), plus le trace de
l'itineraire dans un GeoJSON.

Fonctionnalites v2 (Missions 3 & 4) :
- Selection des hopitaux basee sur config/hospital_whitelist.json (15 officiels + candidats locaux).
- Filtrage cible des communes via --communes-list ou --communes-file.
- Cache versionne par destination dans data/cache/ors_v2/.
- Options --force-recompute et --dry-run.
- Strategie d'upsert/merge sans ecrasement destructif des 96 communes preservees.
- Normalisation documentaire des toponymes sans alteration des traces valides.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

RACINE = Path.cwd()
COMMUNES = RACINE / "data" / "processed" / "communes_TTA_2024.csv"
WHITELIST_PATH = RACINE / "config" / "hospital_whitelist.json"
BASE_CSV = RACINE / "data" / "processed" / "travel_time_TTA_2024.csv"
BASE_GEOJSON = RACINE / "data" / "processed" / "travel_routes_TTA.geojson"
DEFAULT_OUTPUT_DIR = RACINE / "data" / "processed" / "v2"
CACHE_V2_DIR = RACINE / "data" / "cache" / "ors_v2"

BASE = "https://api.heigit.org/openrouteservice/v2"
K = 5
FACTEUR_DETOUR = 1.4
VITESSE = 50.0
PAUSE = 3.0
ESSAIS = 3
RAYONS = (None, 5000, 20000)  # rayon de recherche d'une route (m)

# Communes concernees par la normalisation documentaire des toponymes OSM
DOC_NORMALIZATION_MAP = {
    # 18 communes rattachees au CHP Abou Kacem Zahraoui d'Ouezzane
    "MA-01-151-0607": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Bni Ahmed Gharbia (Chefchaouen)
    "MA-01-405-0109": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Ouezzane
    "MA-01-405-0701": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Bni Quolla
    "MA-01-405-0705": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Masmouda
    "MA-01-405-0707": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Mzefroune
    "MA-01-405-0715": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Sidi Redouane
    "MA-01-405-0901": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Ain Beida (snap > 1000m)
    "MA-01-405-0903": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Asjen
    "MA-01-405-0905": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Brikcha
    "MA-01-405-0909": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Moqrissat
    "MA-01-405-1107": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Kalaat Bouqorra
    "MA-01-405-1111": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Zoumi (snap > 1000m)
    "MA-01-405-1303": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Lamjaara
    "MA-01-405-1309": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Ouannana
    "MA-01-405-1311": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Sidi Ahmed Cherif
    "MA-01-405-1313": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Sidi Bousber
    "MA-01-405-1317": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Teroual
    "MA-01-405-1319": "CHP Abou Kacem Zahraoui (Ouezzane)",  # Zghira
    # 1 commune Imzouren
    "MA-01-051-0105": "HPr Imzouren",
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en km a vol d'oiseau entre deux points."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2
    a += math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def classe(temps: float) -> int:
    """1 = moins de 15 min, 2 = 15 a 45 min, 3 = plus de 45 min."""
    if temps < 15:
        return 1
    return 2 if temps <= 45 else 3


def cle() -> str | None:
    """Lit ORS_API_KEY dans .env a la racine du depot."""
    try:
        from dotenv import load_dotenv

        load_dotenv(RACINE / ".env")
    except ImportError:
        pass
    return os.getenv("ORS_API_KEY") or None


def load_whitelist(path: Path | None = None) -> dict[str, Any]:
    """Charge le referentiel qualifie des destinations sanitaires."""
    p = path or WHITELIST_PATH
    if not p.is_file():
        raise FileNotFoundError(f"Whitelist non trouvee : {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_cache_path(cache_dir: Path, commune_code: str, osm_type: str, osm_id: int) -> Path:
    """Genere la cle de cache qualifiee par commune et etablissement cible."""
    return cache_dir / f"{commune_code}__{osm_type}_{osm_id}.json"


def validate_ors_response(feature: dict[str, Any]) -> bool:
    """Verifie l'integrite et la conformite d'une reponse ORS GeoJSON."""
    if not isinstance(feature, dict):
        return False
    geom = feature.get("geometry", {})
    props = feature.get("properties", {})
    summary = props.get("summary", {})

    if geom.get("type") != "LineString":
        return False
    coords = geom.get("coordinates", [])
    if not isinstance(coords, list) or len(coords) < 2:
        return False
    if "duration" not in summary or "distance" not in summary:
        return False
    if summary["duration"] < 0 or summary["distance"] < 0:
        return False
    return True


def get_candidates_for_commune(
    commune_code: str,
    start_lat: float,
    start_lon: float,
    whitelist: dict[str, Any],
    k_nearest: int = K,
) -> list[dict[str, Any]]:
    """Determine la liste ordonnee des etablissements admissibles selon les arbitrages."""
    # Arbitrage A : Fnideq & Belyounech -> Fallback provisoire CHP M'Diq
    if commune_code in ("MA-01-573-0101", "MA-01-573-0109"):
        return [
            {
                "osm_type": "way",
                "osm_id": 293247182,
                "name": "Hopital Mohamed 6",
                "canonical_name": "CHP Mohamed 6 (M'Diq)",
                "lat": 35.692040,
                "lon": -5.329870,
                "destination_status": "PROVISIONAL_FALLBACK",
                "official_status": "OFFICIAL_MINISTRY",
                "notes": "Fallback provisoire Fnideq/Belyounech vers CHP M'Diq via N16",
            }
        ]

    # Arbitrage B : Anjra -> Fallback provisoire CHR Sania R'mel (ou test CHU Tanger)
    if commune_code == "MA-01-227-0305":
        return [
            {
                "osm_type": "way",
                "osm_id": 484204214,
                "name": "Hôpital Sanyat Rmel",
                "canonical_name": "CHR Sania R'mel (Tétouan)",
                "lat": 35.573345,
                "lon": -5.355885,
                "destination_status": "PROVISIONAL_FALLBACK",
                "official_status": "OFFICIAL_MINISTRY",
                "notes": "Destination provisoire Anjra (CHR Sania R'mel)",
            },
            {
                "osm_type": "way",
                "osm_id": 871505068,
                "name": "CHU de Tanger-Tétouan-Al Hoceima",
                "canonical_name": "CHU de Tanger",
                "lat": 35.683432,
                "lon": -5.925265,
                "destination_status": "COMPARISON_CANDIDATE",
                "official_status": "OFFICIAL_MINISTRY",
                "notes": "Candidat alternatif de comparaison administrative Anjra",
            },
        ]

    # Arbitrage C : Communes rattachees a l'Hopital Bni Said
    bni_said_communes = set()
    bni_said_facility = None
    for cand in whitelist.get("local_operational_candidates", []):
        if cand.get("osm_id") == 1547030549:
            bni_said_facility = cand
            bni_said_communes = set(cand.get("connected_communes", []))

    pool: list[dict[str, Any]] = []

    # Si la commune est une des 9 de Bni Said, inclure le candidat local
    if commune_code in bni_said_communes and bni_said_facility:
        pool.append(
            {
                "osm_type": bni_said_facility["osm_type"],
                "osm_id": bni_said_facility["osm_id"],
                "name": bni_said_facility["osm_name"],
                "canonical_name": bni_said_facility["name"],
                "lat": bni_said_facility["latitude"],
                "lon": bni_said_facility["longitude"],
                "destination_status": "LOCAL_OPERATIONAL_CANDIDATE",
                "official_status": "NOT_OFFICIAL",
                "notes": "Candidat local operationnel Bni Said",
            }
        )

    # Ajouter les 15 hopitaux publics officiels de la whitelist
    for fac in whitelist.get("facilities", []):
        if fac.get("osm_id") is not None:
            pool.append(
                {
                    "osm_type": fac["osm_type"],
                    "osm_id": fac["osm_id"],
                    "name": fac["osm_name"],
                    "canonical_name": fac["name"],
                    "lat": fac["latitude"],
                    "lon": fac["longitude"],
                    "destination_status": "VERIFIED_PUBLIC_HOSPITAL",
                    "official_status": "OFFICIAL_MINISTRY",
                    "notes": fac.get("notes", ""),
                }
            )

    # Ordonner par distance a vol d'oiseau initiale et restreindre aux K plus proches
    pool_sorted = sorted(pool, key=lambda h: haversine(start_lat, start_lon, h["lat"], h["lon"]))
    return pool_sorted[:k_nearest]


def itineraire(
    session: Any, token: str, origine: tuple[float, float], hopital: dict[str, Any]
) -> dict[str, Any] | None:
    """Appelle ORS Directions pour calculer l'itineraire."""
    coordonnees = [[origine[1], origine[0]], [hopital["lon"], hopital["lat"]]]
    entetes = {"Authorization": token, "Content-Type": "application/json"}
    for rayon in RAYONS:
        payload: dict[str, Any] = {"coordinates": coordonnees}
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
            except Exception as err:
                if essai == ESSAIS:
                    raise RuntimeError(f"reseau injoignable ({err})") from err
                time.sleep(5 * essai)
                continue
            if rep.status_code == 200:
                data = rep.json()
                features = data.get("features", [])
                if features and validate_ors_response(features[0]):
                    return features[0]
                return None
            if rep.status_code in (401, 403):
                raise RuntimeError(
                    f"Authentification refusee ou quota ORS epuise ({rep.status_code})"
                )
            if rep.status_code == 429:
                time.sleep(30)
                continue
            if rep.status_code == 404:
                if "2010" in rep.text:
                    break  # point trop loin d'une route : on elargit le rayon
                return None
            if essai == ESSAIS:
                raise RuntimeError(f"ORS indisponible ({rep.status_code})")
            time.sleep(5 * essai)
    return None


def par_ors_v2(
    session: Any,
    token: str,
    commune_code: str,
    origine: tuple[float, float],
    candidats: list[dict[str, Any]],
    cache_dir: Path,
    force_recompute: bool = False,
) -> dict[str, Any]:
    """Tente de router vers le meilleur candidat parmi la selection qualifiee."""
    meilleur: dict[str, Any] | None = None

    for hopital in candidats:
        cache_path = get_cache_path(cache_dir, commune_code, hopital["osm_type"], hopital["osm_id"])

        # Verification du cache versionne : ne jamais retourner avant d'avoir compare tous les candidats
        if not force_recompute and cache_path.is_file():
            try:
                cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
                if cached_data.get("status") == "SUCCESS" and "temps_min" in cached_data:
                    if meilleur is None or cached_data["temps_min"] < meilleur["temps_min"]:
                        meilleur = cached_data
                    continue
            except Exception:
                pass

        feature = itineraire(session, token, origine, hopital)
        if feature is None:
            continue
        resume = feature["properties"]["summary"]
        temps_min = round(resume["duration"] / 60, 1)
        dist_km = round(resume["distance"] / 1000, 2)

        resultat = {
            "commune_code": commune_code,
            "hopital": hopital,
            "temps_min": temps_min,
            "distance_km": dist_km,
            "trace": feature["geometry"]["coordinates"],
            "methode": "ORS_DRIVING_CAR",
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "status": "SUCCESS",
            "profile": "driving-car",
        }

        # Sauvegarde immediate dans le cache versionne
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(resultat, ensure_ascii=False), encoding="utf-8")

        if meilleur is None or temps_min < meilleur["temps_min"]:
            meilleur = resultat

    if meilleur:
        return meilleur
    raise RuntimeError(f"Aucun des hopitaux admissibles n'est joignable pour {commune_code}")


def par_estimation(candidats: list[dict[str, Any]], origine: tuple[float, float]) -> dict[str, Any]:
    """Plan B : vol d'oiseau x facteur de detour, a 50 km/h."""
    distances = sorted(
        (haversine(origine[0], origine[1], h["lat"], h["lon"]), i) for i, h in enumerate(candidats)
    )
    km = distances[0][0] * FACTEUR_DETOUR
    hopital = candidats[distances[0][1]]
    return {
        "hopital": hopital,
        "temps_min": round(km / VITESSE * 60, 1),
        "distance_km": round(km, 2),
        "trace": None,
        "methode": "DETOUR_1.4",
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "status": "ESTIMATED_FALLBACK",
    }


def upsert_travel_data(
    base_csv_path: Path,
    base_geojson_path: Path,
    output_dir: Path,
    new_rows: list[dict[str, Any]],
    new_features: list[dict[str, Any]],
    apply_doc_norm: bool = True,
) -> tuple[int, int]:
    """Fusionne (upsert) les lignes et traces sans ecraser les 96 communes conservees."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / "travel_time_TTA_2024.csv"
    out_geojson = output_dir / "travel_routes_TTA.geojson"

    # Charger le CSV de base
    df_base = pd.read_csv(base_csv_path, dtype={"commune_code": str})

    # Appliquer la normalisation documentaire si demandee
    if apply_doc_norm:
        for code, norm_name in DOC_NORMALIZATION_MAP.items():
            mask = df_base["commune_code"] == code
            if mask.any():
                df_base.loc[mask, "hospital_name"] = norm_name

    # Indexer par commune_code
    df_base = df_base.set_index("commune_code")

    # Mettre a jour avec les nouveaux calculs
    for r in new_rows:
        code = str(r["commune_code"])
        for k, v in r.items():
            if k in df_base.columns:
                df_base.at[code, k] = v

    # Re-appliquer la normalisation documentaire sur l'ensemble final
    if apply_doc_norm:
        for code, norm_name in DOC_NORMALIZATION_MAP.items():
            if code in df_base.index:
                df_base.at[code, "hospital_name"] = norm_name

    df_final = df_base.reset_index()

    # Charger le GeoJSON de base
    with base_geojson_path.open("r", encoding="utf-8") as f:
        gj_base = json.load(f)

    # Remplacer les features recalculées
    new_features_map = {f["properties"]["commune_code"]: f for f in new_features}
    final_features = []
    for feat in gj_base["features"]:
        code = feat["properties"]["commune_code"]
        if code in new_features_map:
            feat_to_add = new_features_map[code]
            if apply_doc_norm and code in DOC_NORMALIZATION_MAP:
                feat_to_add["properties"]["hospital_name"] = DOC_NORMALIZATION_MAP[code]
            final_features.append(feat_to_add)
        else:
            # Appliquer normalisation documentaire dans properties GeoJSON
            if apply_doc_norm and code in DOC_NORMALIZATION_MAP:
                feat["properties"]["hospital_name"] = DOC_NORMALIZATION_MAP[code]
            final_features.append(feat)

    # Ecriture atomique CSV
    tmp_csv = out_csv.with_suffix(".csv.tmp")
    df_final.to_csv(tmp_csv, index=False, encoding="utf-8")
    if out_csv.exists():
        shutil.copy2(out_csv, out_csv.with_suffix(".csv.bak"))
    tmp_csv.replace(out_csv)

    # Ecriture atomique GeoJSON
    tmp_gj = out_geojson.with_suffix(".geojson.tmp")
    tmp_gj.write_text(
        json.dumps({"type": "FeatureCollection", "features": final_features}, ensure_ascii=False),
        encoding="utf-8",
    )
    if out_geojson.exists():
        shutil.copy2(out_geojson, out_geojson.with_suffix(".geojson.bak"))
    tmp_gj.replace(out_geojson)

    return len(df_final), len(final_features)


def main(argv: list[str] | None = None) -> int:
    """Point d'entree principal avec options de securite et de ciblage."""
    parseur = argparse.ArgumentParser(
        description="Calcul d'accessibilite hospitaliere GeoVulnera TTA"
    )
    parseur.add_argument("--limit", type=int, default=0, help="Ne traiter que N communes")
    parseur.add_argument(
        "--approx", action="store_true", help="Forcer le plan B (estimation a vol d'oiseau)"
    )
    parseur.add_argument(
        "--communes-list", type=str, default="", help="Codes HCP separes par des virgules"
    )
    parseur.add_argument(
        "--communes-file", type=str, default="", help="Fichier texte listant les codes HCP"
    )
    parseur.add_argument(
        "--force-recompute", action="store_true", help="Ignorer le cache et forcer le recalcul"
    )
    parseur.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation hors ligne sans appel API ni ecriture finale",
    )
    parseur.add_argument(
        "--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Repertoire de sortie"
    )
    parseur.add_argument(
        "--whitelist",
        type=str,
        default=str(WHITELIST_PATH),
        help="Chemin vers hospital_whitelist.json",
    )
    parseur.add_argument(
        "--no-doc-norm", action="store_true", help="Desactiver la normalisation documentaire"
    )
    args = parseur.parse_args(argv)

    if not COMMUNES.is_file() or not BASE_CSV.is_file() or not BASE_GEOJSON.is_file():
        print("ERREUR : Fichiers sources absents de data/processed/")
        return 1

    # Charger la whitelist qualifiee
    whitelist = load_whitelist(Path(args.whitelist))
    communes_df = pd.read_csv(COMMUNES, dtype={"commune_code": str})
    print(
        f"Referentiel charge : {len(communes_df)} communes | Whitelist : {whitelist['metadata']['total_official_hospitals']} hopitaux officiels"
    )

    # Filtrage cible des communes
    target_codes: list[str] | None = None
    if args.communes_list:
        target_codes = [c.strip() for c in args.communes_list.split(",") if c.strip()]
    elif args.communes_file:
        f_path = Path(args.communes_file)
        if not f_path.is_file():
            print(f"ERREUR : Fichier communes introuvable : {f_path}")
            return 1
        target_codes = [
            line.strip() for line in f_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    if target_codes:
        valid_set = set(communes_df["commune_code"])
        invalids = [c for c in target_codes if c not in valid_set]
        if invalids:
            print(
                f"ERREUR : {len(invalids)} codes HCP invalides dans la selection : {invalids[:5]}"
            )
            return 1
        communes_df = communes_df[communes_df["commune_code"].isin(target_codes)].copy()
        print(f"Selection ciblee activee : {len(communes_df)} communes a traiter.")

    if args.limit and args.limit > 0:
        communes_df = communes_df.head(args.limit)

    token = None if (args.approx or args.dry_run) else cle()
    session = None
    if token:
        import requests

        session = requests.Session()

    mode_label = (
        "DRY-RUN (SIMULATION)"
        if args.dry_run
        else ("ORS (EN LIGNE)" if token else "APPROX (PLAN B)")
    )
    print(f"Mode d'execution : {mode_label}")
    if args.dry_run:
        print("Avertissement : Mode simulation, aucun appel reseau ne sera effectue.")

    cache_dir = CACHE_V2_DIR
    lignes, traces = [], []
    echecs = 0
    dernier = 0.0

    for n, commune in enumerate(communes_df.itertuples(), start=1):
        origine = (float(commune.start_lat), float(commune.start_lon))
        candidats = get_candidates_for_commune(
            commune.commune_code, origine[0], origine[1], whitelist
        )

        if args.dry_run:
            # Verification statique des candidats
            resultat = par_estimation(candidats, origine)
            resultat["methode"] = "DRY_RUN_VALIDATED"
        elif token:
            try:
                attente = PAUSE - (time.time() - dernier)
                if attente > 0:
                    time.sleep(attente)
                resultat = par_ors_v2(
                    session=session,
                    token=token,
                    commune_code=commune.commune_code,
                    origine=origine,
                    candidats=candidats,
                    cache_dir=cache_dir,
                    force_recompute=args.force_recompute,
                )
                dernier = time.time()
            except Exception as err:
                err_msg = str(err)
                if any(k in err_msg.lower() for k in ("authentification", "quota", "401", "403")):
                    print(f"  [ERREUR CRITIQUE AUTH/QUOTA] {err_msg} -> Arret immediat des appels.")
                    raise
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
        if n % 10 == 0 or n == len(communes_df):
            print(f"  Progression : {n}/{len(communes_df)} communes analysees")

    if args.dry_run:
        print(
            f"\n[DRY-RUN TERMINE] {len(lignes)} communes verifiees avec succes. Aucune donnee modifiee."
        )
        return 0

    # Fusion atomique securisee sans ecrasement des 96 communes
    out_dir = Path(args.output_dir)
    total_csv, total_gj = upsert_travel_data(
        base_csv_path=BASE_CSV,
        base_geojson_path=BASE_GEOJSON,
        output_dir=out_dir,
        new_rows=lignes,
        new_features=traces,
        apply_doc_norm=not args.no_doc_norm,
    )

    print(f"\nSucces de l'ecriture securisee dans {out_dir} :")
    print(f"  - CSV : {out_dir / 'travel_time_TTA_2024.csv'} ({total_csv} lignes)")
    print(f"  - GeoJSON : {out_dir / 'travel_routes_TTA.geojson'} ({total_gj} entites)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
