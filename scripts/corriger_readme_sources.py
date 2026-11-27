"""Corrige le dernier reste : la section 6 du README (Sources et licences).

Le README citait GeoVulnera comme source des contours : ce jeu de donnees n'est
pas dans le depot et n'a jamais servi. Les vraies sources sont HCP (RGPH 2024),
OpenStreetMap via Geofabrik, et la liste MSPS pour le croisement des hopitaux.

Utilisation, depuis la racine du depot :

    python scripts/corriger_readme_sources.py

Le script est relancable : la deuxieme fois, il repond "deja corrige".
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path.cwd()

NOUVEAU = """## 6. Sources et licences

- **HCP — RGPH 2024** : limites communales et population légale. Licence à confirmer (D-010).
- **OpenStreetMap, extrait Geofabrik** : hôpitaux et réseau routier — licence ODbL,
  « © contributeurs OpenStreetMap ». À citer dans toute publication.
- **Ministère de la Santé (MSPS)** : liste de 24 hôpitaux, utilisée pour un croisement partiel
  (16 retrouvés par leur nom).
- **OpenRouteService** : temps de trajet routiers.
- **Open-Meteo** : prévisions et historique météorologique.
- Code : licence MIT (voir `LICENSE`).

"""


def main() -> None:
    print("corriger_readme_sources v1")

    readme = RACINE / "README.md"
    if not readme.is_file():
        sys.exit(
            "ERREUR : README.md introuvable. Lance ce script depuis la racine du depot."
        )

    texte = readme.read_text(encoding="utf-8")

    if "GeoVulnera" not in texte:
        print("Info : deja corrige, rien a faire.")
        return

    debut = texte.find("## 6. Sources et licences")
    fin = texte.find("## 7. Limites")
    if debut < 0 or fin < 0 or fin < debut:
        sys.exit("ERREUR : reperes de la section 6 introuvables. Rien n'a ete ecrit.")

    readme.write_text(texte[:debut] + NOUVEAU + texte[fin:], encoding="utf-8")
    print("OK   README.md")
    print()
    print("Section 6 (Sources et licences) remplacee :")
    print("  - GeoVulnera retire (jeu de donnees absent du depot)")
    print("  - HCP RGPH 2024, OSM/Geofabrik et MSPS cites a la place")
    print("  - doublon OpenStreetMap supprime")


if __name__ == "__main__":
    main()
