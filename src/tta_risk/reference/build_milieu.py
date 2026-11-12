"""
TTA Health Access Risk — Membre A
Étape 3 : détermination du milieu de résidence (Urbain / Rural / Mixte) par commune.

Méthode 100 % officielle, sans invention :
  1. Le HCP publie la population et les ménages de CHAQUE DOUAR (fichier officiel
     « Population et ménages par douar de la région TTA selon le RGPH 2024 »).
  2. Les douars ne couvrent que le milieu RURAL. On somme donc la population rurale
     par commune.
  3. Comparaison avec la population légale totale de la commune :
        rural = 0                  -> Urbain
        rural = population totale  -> Rural
        0 < rural < total          -> Mixte
  4. Contrôle : la somme des populations rurales doit égaler le total régional rural
     officiel (1 382 463 habitants au RGPH 2024).

Entrée  : data/raw_downloads/hcp_douars_rural_TTA_rgph2024.xlsx
          data/reference/communes_TTA_146.csv   (contient name_ar)
          data/reference/demographics.csv
Sortie  : data/reference/demographics.csv      (colonnes milieu_*, ajoutées)
          data/reference/qc_milieu.json
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DOUARS = ROOT / "data" / "raw_downloads" / "hcp_douars_rural_TTA_rgph2024.xlsx"
REF146 = ROOT / "data" / "reference" / "communes_TTA_146.csv"
DEMO = ROOT / "data" / "reference" / "demographics.csv"
OUT_DIR = ROOT / "data" / "reference"

POP_RURALE_REGION_OFFICIELLE = 1_382_463
MENAGES_RURAUX_REGION_OFFICIELS = 320_093
SHEET = "خصائص السكان TTA"


def norm_ar(s: str) -> str:
    """Normalise l'arabe : diacritiques, tatweel, alif/ya/ta marbuta, ponctuation."""
    s = (s or "").strip()
    s = re.sub(r"[\u064B-\u0652\u0640]", "", s)
    s = re.sub("[أإآ]", "ا", s)
    for a, b in (("ة", "ه"), ("ى", "ي"), ("ئ", "ي"), ("ؤ", "و")):
        s = s.replace(a, b)
    s = re.sub(r"[^\w\u0600-\u06FF]+", " ", s)
    return " ".join(s.split())


def strip_ar_prefix(s: str) -> str:
    return re.sub(r"^(جماعة|مقاطعة|عمالة|إقليم|جهة|دائرة)\s*", "", (s or "").strip())


def main() -> None:
    # --- 1. population rurale par nom arabe de commune -----------------------
    wb = openpyxl.load_workbook(DOUARS, read_only=True, data_only=True)
    ws = wb[SHEET]
    rows = [r for r in ws.iter_rows(values_only=True)][4:]

    pop_rural: dict[str, int] = defaultdict(int)
    men_rural: dict[str, int] = defaultdict(int)
    nb_douars: dict[str, int] = defaultdict(int)
    codes_douars: dict[str, set] = defaultdict(set)

    for r in rows:
        if not r[0]:
            continue
        nom = norm_ar(r[4])
        if not nom:
            continue
        pop_rural[nom] += int(r[9] or 0)
        men_rural[nom] += int(r[8] or 0)
        nb_douars[nom] += 1
        codes_douars[nom].add(str(r[0]).strip())

    # --- 2. correspondance nom arabe -> commune_code du référentiel ----------
    ref = {r["commune_code"]: r for r in csv.DictReader(REF146.open(encoding="utf-8"))}
    ar_to_code: dict[str, str] = {}
    for code, r in ref.items():
        ar_to_code[norm_ar(strip_ar_prefix(r["name_ar"]))] = code

    # --- 3. lecture de la démographie et calcul du milieu --------------------
    demo_rows = list(csv.DictReader(DEMO.open(encoding="utf-8")))
    non_appariees = []
    controle_code_geo = []

    for d in demo_rows:
        code = d["commune_code"]
        name_ar = ref[code]["name_ar"]
        key = norm_ar(strip_ar_prefix(name_ar))
        rp = pop_rural.get(key)
        rm = men_rural.get(key)
        total = int(d["population_2024"])

        if rp is None:
            rp, rm, nd = 0, 0, 0
            if total > 0 and key not in ar_to_code:
                non_appariees.append({"commune_code": code, "name_fr": d["name_fr"], "name_ar": name_ar})
        else:
            nd = nb_douars.get(key, 0)

        rp = int(rp or 0)
        rm = int(rm or 0)

        if rp == 0:
            milieu = "Urbain"
        elif rp >= total:
            milieu = "Rural"
        else:
            milieu = "Mixte"

        d["population_rurale_2024"] = rp
        d["population_urbaine_2024"] = total - rp
        d["menages_ruraux_2024"] = rm
        d["part_rurale_pct"] = round(100 * rp / total, 1) if total else 0.0
        d["nb_douars"] = nd
        d["milieu"] = milieu

        # contrôle croisé : code douar (6 premiers chiffres) -> code officiel
        six = sorted(codes_douars.get(key, []))
        if six:
            # Code douar officiel = 13 caractères : PP(2) P(1) CC(2) SS(2) FFFF(4)
            #   ex. '1510303201001' -> province 151, commune 03, série 03, douar 201001
            #   ATTENTION : pour Al Hoceima (province 051), le fichier Excel a perdu le zéro
            #   initial -> le code ne fait que 12 caractères. On réaligne avant découpage.
            s = six[0]
            if len(s) == 12:
                s = "0" + s
            prov, comm = s[0:3], s[3:5]
            expected_prefix = f"MA-01-{prov}-{comm}"
            controle_code_geo.append(
                {
                    "commune_code": code,
                    "prefixe_attendu_depuis_douars": expected_prefix,
                    "prefixe_referentiel": code[:13],
                    "coherent": code.startswith(expected_prefix),
                }
            )

    # --- 4. contrôles -------------------------------------------------------
    tot_rural = sum(int(d["population_rurale_2024"]) for d in demo_rows)
    tot_men_rural = sum(int(d["menages_ruraux_2024"]) for d in demo_rows)
    from collections import Counter

    repartition = Counter(d["milieu"] for d in demo_rows)
    incoh_code = [c for c in controle_code_geo if not c["coherent"]]

    qc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "methode": "Somme de la population des douars (milieu rural uniquement) comparée à la population légale totale",
        "source_douars": str(DOUARS.relative_to(ROOT)),
        "communes_rurales_dans_fichier_douars": len(pop_rural),
        "repartition_milieu": dict(repartition),
        "population_rurale_totale": tot_rural,
        "population_rurale_officielle": POP_RURALE_REGION_OFFICIELLE,
        "ecart_rural": tot_rural - POP_RURALE_REGION_OFFICIELLE,
        "menages_ruraux_total": tot_men_rural,
        "menages_ruraux_officiel": MENAGES_RURAUX_REGION_OFFICIELS,
        "ecart_menages_ruraux": tot_men_rural - MENAGES_RURAUX_REGION_OFFICIELS,
        "communes_non_appariees_douars": non_appariees,
        "controle_codes_geographiques": {
            "verifiees": len(controle_code_geo),
            "incoherentes": incoh_code,
        },
        "checks": {
            "population_rurale_conforme": tot_rural == POP_RURALE_REGION_OFFICIELLE,
            "menages_ruraux_conformes": tot_men_rural == MENAGES_RURAUX_REGION_OFFICIELS,
            "codes_geo_coherents": len(incoh_code) == 0,
            "aucune_commune_sans_milieu": all(d["milieu"] for d in demo_rows),
        },
    }

    # --- 5. écriture --------------------------------------------------------
    cols = [
        "commune_code", "name_fr", "province", "province_code",
        "population_2024", "marocains_2024", "etrangers_2024", "menages_2024",
        "milieu",
        "population_urbaine_2024", "population_rurale_2024",
        "menages_ruraux_2024", "part_rurale_pct", "nb_douars",
        "annee_reference", "source", "statut_valeur", "code_geo_officiel",
    ]
    with DEMO.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(demo_rows)

    (OUT_DIR / "qc_milieu.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(qc["checks"], ensure_ascii=False, indent=2))
    print(f"\nRépartition : {dict(repartition)}")
    print(f"Population rurale : {tot_rural:,} (officiel {POP_RURALE_REGION_OFFICIELLE:,}, écart {qc['ecart_rural']:+d})".replace(",", " "))
    print(f"Ménages ruraux    : {tot_men_rural:,} (officiel {MENAGES_RURAUX_REGION_OFFICIELS:,}, écart {qc['ecart_menages_ruraux']:+d})".replace(",", " "))
    if incoh_code:
        print(f"⚠ {len(incoh_code)} codes géographiques incohérents :")
        for c in incoh_code[:10]:
            print("   ", c)


if __name__ == "__main__":
    main()
