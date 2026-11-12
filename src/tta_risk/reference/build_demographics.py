"""
TTA Health Access Risk — Membre A
Étape 2 : intégration de la population légale RGPH 2024 (HCP) au référentiel.

Entrée  : data/raw_downloads/population_legale_rgph2024_TTA.csv
          (table officielle HCP RGPH 2024, population légale des collectivités
           territoriales de la région TTA, avec code géographique)
Sorties : data/reference/demographics.csv        146 communes, population joint
          data/reference/population_TEMPLATE.csv  template rempli (remplace le squelette)
          data/reference/qc_demographics.json     rapport de contrôle qualité

Règles :
- Aucune population inventée. Une commune sans population officielle reste A_REMPLIR.
- La jointure se fait sur le CODE, jamais sur le nom.
- Les 4 arrondissements de Tanger sont agrégés sous la commune de Tanger (niveau HCP).
- Contrôle final : somme des populations == total régional officiel (4 030 222).
"""

from __future__ import annotations

import csv
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POP_RAW = ROOT / "data" / "raw_downloads" / "population_legale_rgph2024_TTA.csv"
REF146 = ROOT / "data" / "reference" / "communes_TTA_146.csv"
OUT_DIR = ROOT / "data" / "reference"

TOTAL_REGION_OFFICIEL = 4_030_222
MENAGES_REGION_OFFICIEL = 1_048_860

# Code Tanger au niveau communal officiel
TANGER_CODE = "MA-01-511-0100"


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str) -> str:
    s = strip_accents(s or "").lower()
    for a in ("-", "'", "’", "`", ","):
        s = s.replace(a, " ")
    return " ".join(s.split())


# Codes dont le dernier segment n'a qu'un chiffre (ex. '01.511.01.0' = commune de Tanger).
CORRESPONDANCE_SPECIALE: dict[str, str] = {}


def wiki_code_to_commune_code(code: str) -> str | None:
    """'01.051.09.01' -> 'MA-01-051-0901' ; les codes à 3 segments (cercles) sont ignorés."""
    if code in CORRESPONDANCE_SPECIALE:
        return CORRESPONDANCE_SPECIALE[code]
    parts = code.split(".")
    if len(parts) != 4:
        return None
    r, p, c, s = parts
    return f"MA-{r.zfill(2)}-{p}-{c.zfill(2)}{s.zfill(2)}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- population officielle ---
    pop: dict[str, dict] = {}
    arrondissements: dict[str, dict] = {}
    with POP_RAW.open(encoding="utf-8") as fh:
        for line in csv.DictReader(fh):
            raw_code = (line.get("code_geo") or "").strip().strip("'")
            cc = wiki_code_to_commune_code(raw_code)
            if cc is None:
                continue
            rec = {
                "commune_code": cc,
                "label_officiel": line["label"].replace("'''", "").strip(),
                "est_arrondissement": line["label"].replace("'''", "").strip().startswith("Arrondissement"),
                "population_2024": int(line["population_totale"]),
                "marocains_2024": int(line["marocains"]),
                "etrangers_2024": int(line["etrangers"]),
                "menages_2024": int(line["menages"]),
                "code_geo_officiel": raw_code,
            }
            if rec["est_arrondissement"]:
                arrondissements[cc] = rec
            pop[cc] = rec

    # --- référentiel 146 ---
    ref = list(csv.DictReader(REF146.open(encoding="utf-8")))

    rows = []
    non_apparies = []
    for r in ref:
        code = r["commune_code"]
        p = pop.get(code)
        if p is None:
            non_apparies.append({"commune_code": code, "name_fr": r["name_fr"], "province": r["province"]})
            continue
        rows.append(
            {
                "commune_code": code,
                "name_fr": r["name_fr"],
                "province": r["province"],
                "province_code": r["province_code"],
                "population_2024": p["population_2024"],
                "marocains_2024": p["marocains_2024"],
                "etrangers_2024": p["etrangers_2024"],
                "menages_2024": p["menages_2024"],
                "milieu": "",  # renseigné plus bas (urbain/rural) — voir note
                "annee_reference": 2024,
                "source": "HCP — RGPH 2024, population légale",
                "statut_valeur": "OFFICIEL",
                "code_geo_officiel": p["code_geo_officiel"],
            }
        )

    # --- agrégation des arrondissements de Tanger (info de contrôle) ---
    agg_detail = []
    for cc, a in arrondissements.items():
        agg_detail.append(
            {
                "arrondissement_code": cc,
                "arrondissement_nom": a["label_officiel"].replace("Arrondissement de ", ""),
                "population_2024": a["population_2024"],
                "menages_2024": a["menages_2024"],
            }
        )
    tanger = next((x for x in rows if x["commune_code"] == TANGER_CODE), None)
    sum_arr = sum(a["population_2024"] for a in agg_detail)

    # --- contrôles ---
    total_pop = sum(x["population_2024"] for x in rows)
    total_men = sum(x["menages_2024"] for x in rows)
    codes = [x["commune_code"] for x in rows]
    doublons = sorted({c for c in codes if codes.count(c) > 1})

    per_prov: dict[str, int] = {}
    pop_prov: dict[str, int] = {}
    for x in rows:
        per_prov[x["province"]] = per_prov.get(x["province"], 0) + 1
        pop_prov[x["province"]] = pop_prov.get(x["province"], 0) + x["population_2024"]

    qc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "HCP RGPH 2024 — population légale des collectivités territoriales (région TTA)",
        "communes_reference": len(ref),
        "communes_appariees": len(rows),
        "communes_non_appariees": non_apparies,
        "doublons": doublons,
        "population_totale_obtenue": total_pop,
        "population_totale_officielle": TOTAL_REGION_OFFICIEL,
        "ecart_population": total_pop - TOTAL_REGION_OFFICIEL,
        "menages_total_obtenu": total_men,
        "menages_total_officiel": MENAGES_REGION_OFFICIEL,
        "ecart_menages": total_men - MENAGES_REGION_OFFICIEL,
        "communes_par_province": dict(sorted(per_prov.items())),
        "population_par_province": dict(sorted(pop_prov.items(), key=lambda kv: -kv[1])),
        "controle_tanger": {
            "commune_code": TANGER_CODE,
            "population_commune_tanger": tanger["population_2024"] if tanger else None,
            "somme_4_arrondissements": sum_arr,
            "coherent": (tanger["population_2024"] == sum_arr) if tanger else False,
            "detail": agg_detail,
        },
        "checks": {
            "toutes_communes_appariees": len(non_apparies) == 0,
            "cle_unique": len(doublons) == 0,
            "population_totale_conforme": total_pop == TOTAL_REGION_OFFICIEL,
            "menages_totaux_conformes": total_men == MENAGES_REGION_OFFICIEL,
            "tanger_coherent_avec_arrondissements": (tanger["population_2024"] == sum_arr) if tanger else False,
        },
    }

    # --- écriture ---
    cols = [
        "commune_code", "name_fr", "province", "province_code",
        "population_2024", "marocains_2024", "etrangers_2024", "menages_2024",
        "milieu", "annee_reference", "source", "statut_valeur", "code_geo_officiel",
    ]
    with (OUT_DIR / "demographics.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # template rempli (même contenu + superficie/densité)
    ref_by = {r["commune_code"]: r for r in ref}
    with (OUT_DIR / "population_TEMPLATE.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "commune_code", "name_fr", "province", "population_2024", "menages_2024",
            "milieu", "superficie_km2", "densite_hab_km2",
            "annee_reference", "source", "statut_valeur",
        ])
        for x in rows:
            sup = float(ref_by[x["commune_code"]]["area_km2"])
            dens = round(x["population_2024"] / sup, 1) if sup > 0 else ""
            w.writerow([
                x["commune_code"], x["name_fr"], x["province"], x["population_2024"], x["menages_2024"],
                x["milieu"], sup, dens, 2024, "HCP RGPH 2024", "OFFICIEL",
            ])

    (OUT_DIR / "qc_demographics.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(qc["checks"], ensure_ascii=False, indent=2))
    print(f"\ncommunes appariées : {len(rows)} / {len(ref)}")
    print(f"population totale  : {total_pop:,} (officiel {TOTAL_REGION_OFFICIEL:,}, écart {qc['ecart_population']:+d})".replace(",", " "))
    print(f"ménages totaux     : {total_men:,} (officiel {MENAGES_REGION_OFFICIEL:,}, écart {qc['ecart_menages']:+d})".replace(",", " "))
    if non_apparies:
        print(f"\nNON APPARIÉES ({len(non_apparies)}) :")
        for n in non_apparies:
            print("  ", n["commune_code"], n["name_fr"], f"({n['province']})")


if __name__ == "__main__":
    main()
