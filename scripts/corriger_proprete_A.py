"""Corrige les erreurs de proprete du depot TTA (volet A, sans base de donnees).

Ce script traite 11 des 14 erreurs qui te reviennent. Il ne touche NI au code
de scoring NI a PostgreSQL. Il fait :

   5. docs/methodology.md      : bornes "provisoires" -> retenues (D-015),
                                 temps "estimes" -> temps reels ORS
   6. docs/data_dictionary.md  : 5 hopitaux sans nom signales (§3.1),
                                 milieu Urbain/Mixte/Rural (§4)
   7. docs/rapport_qualite_v1.md      : CREE (controle qualite du referentiel)
   8. docs/anomalies_referentiel.md   : CREE (anomalies et ecarts documentes)
   9. README.md                : vraies instructions Docker (§3)
  16. .github/pull_request_template.md : CREE (modele de PR)
  17. Makefile                : CREE (raccourcis de commandes)
  19. src/tta_risk/routing/__init__.py et ingest/__init__.py : docstrings
  21. .github/workflows/ci.yml : seuil de couverture --cov-fail-under=10
  24. scripts/script_test_forecast_api_meteo.py : supprime

NE SONT PAS dans ce script (ils demandent autre chose qu'un fichier) :
   1-2. le score dans risk_daily  -> script separe + migration SQL (base requise)
   3.   table accessibility.travel_time -> idem
   4.   sensibilite_bornes.py -> fichier deja sur ton Drive, un simple copy
   20.  ruff format -> c'est une commande, pas un fichier

Utilisation, depuis la racine du depot :

    python scripts/corriger_proprete_A.py

Le script verifie TOUS les reperes avant d'ecrire. Si un seul manque, il
s'arrete sans rien modifier. Il est relancable.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

RACINE = Path.cwd()
AUJOURDHUI = date.today().isoformat()

# ---------------------------------------------------------------------------
# 5. Methodology : trois phrases perimees
# ---------------------------------------------------------------------------

CORRECTIONS_METHODOLOGY = [
    (
        "Les bornes 15 / 45 sont **provisoires** (D-015) : elles seront réexaminées quand les temps\n"
        "routiers OpenRouteService remplaceront l'estimation actuelle.",
        "Les bornes 15 / 45 sont **retenues** (D-015). L'analyse de sensibilité a été faite sur six\n"
        "variantes de bornes : 91 communes changent de classe, mais le **classement des communes par\n"
        "temps de trajet ne change jamais**. Les temps utilisés sont les temps routiers réels\n"
        "OpenRouteService, disponibles pour les **146 communes**.",
        "methodology : paragraphe des bornes",
    ),
    (
        "| Bornes 15 / 45 min **provisoires** | classe de trajet sensible au choix de bornes ; "
        "analyse de sensibilité en semaine 3 |",
        "| Bornes 15 / 45 min **retenues** (D-015) | classe de trajet sensible au choix de bornes ; "
        "sensibilité calculée sur 6 variantes : 91 communes changent de classe, le classement non |",
        "methodology : ligne des bornes (tableau des limites)",
    ),
    (
        "| Temps de trajet **estimés** (plan B : vol d'oiseau × 1,4 ÷ 50 km/h) | "
        "sous-estime les zones de montagne ; remplacés par OpenRouteService dès que possible |",
        "| Temps de trajet **réels** OpenRouteService (146/146) | le plan B (vol d'oiseau × 1,4 ÷ "
        "50 km/h) n'a pas été utilisé ; limite restante : pas de trafic réel, pas de route coupée |",
        "methodology : ligne des temps de trajet",
    ),
]

# ---------------------------------------------------------------------------
# 6. Dictionnaire : limites §3.1 + milieu §4
# ---------------------------------------------------------------------------

LIGNE_HOPITAUX_ANONYMES = (
    "| **5 hôpitaux sans nom** | Sur les 66 hôpitaux, **5 n'ont pas de `name`** dans OSM "
    "(identifiants `10558675910`, `363772898`, `411183375`, `478960842`, `908806511`). "
    "Ils sont conservés : leur position est valide et le temps de trajet ne dépend pas du nom. |\n"
)

AVANT_MILIEU = "| `milieu` | texte | — | Référentiel §1 | `OFFICIEL` | `Urbain` / `Rural`. |"
APRES_MILIEU = (
    "| `milieu` | texte | — | Référentiel §1 | `OFFICIEL` | `Urbain` (17 communes) / "
    "`Mixte` (60) / `Rural` (69). `Mixte` = commune ayant à la fois des douars urbains et ruraux "
    "(D-006), catégorie propre au projet et non officielle. |"
)

# ---------------------------------------------------------------------------
# 7 et 8. Deux documents qui n'ont jamais ete ecrits
# ---------------------------------------------------------------------------

RAPPORT_QUALITE = """# Rapport qualite v1 — referentiel territorial TTA

> Tenu par le **Membre A**. Date : __DATE__.
> Objet : prouver, chiffre par chiffre, que le referentiel des 146 communes est utilisable
> et que ses limites sont connues. Ce document repond a la tache **A-7**.

## 1. Ce qui est livre

| Fichier | Contenu | Taille |
|---|---|---|
| `data/processed/communes_TTA_2024.csv` | 146 lignes x 25 colonnes | 146 communes |
| `data/processed/communes_TTA.geojson` | 146 polygones + centroides, EPSG:4326 | 146 entites |
| `data/processed/health_facilities_TTA.csv` | 892 etablissements OSM | 892 lignes |
| `data/processed/travel_time_TTA_2024.csv` | temps de trajet ORS | 146 lignes |
| `data/processed/access_zones_TTA.csv` | zones 15 / 30 / 45 / 60 min | 146 lignes |

## 2. Les 6 controles qui sont passes

| # | Controle | Resultat | Comment le refaire |
|---|---|---|---|
| 1 | Nombre de communes | **146** exactement | `pytest -m territory` |
| 2 | Unicite de `commune_code` | **146 codes, 0 doublon** | `pytest -m territory` |
| 3 | Repartition par province | 36 / 28 / 22 / 19 / 17 / 12 / 7 / 5 = **146** | §3 ci-dessous |
| 4 | Somme de la population | **4 030 222** habitants | `communes_TTA_2024.csv` |
| 5 | Coordonnees manquantes | **0** (les 146 ont `centroid_lat` et `centroid_lon`) | controle pandas |
| 6 | Jointures | **0 orphelin** entre communes, hopitaux, temps et zones | controle pandas |

## 3. Repartition par province (controle contre le HCP)

| Province / Prefecture | HCP | Obtenu | Ecart |
|---|---|---|---|
| Al Hoceima | 36 | 36 | 0 |
| Chefchaouen | 28 | 28 | 0 |
| Tetouan | 22 | 22 | 0 |
| Larache | 19 | 19 | 0 |
| Ouezzane | 17 | 17 | 0 |
| Tanger-Assilah | 12 | 12 | 0 |
| Fahs-Anjra | 7 | 7 | 0 |
| M'diq-Fnideq | 5 | 5 | 0 |
| **Region TTA** | **146** | **146** | **0** |

## 4. Milieu de residence

| Milieu | Communes |
|---|---|
| Urbain | 17 |
| Mixte | 60 |
| Rural | 69 |

La categorie **Mixte** est propre au projet (D-006) : elle designe une commune qui contient
a la fois des douars urbains et ruraux. Elle n'est pas officielle et doit etre expliquee
a l'oral.

## 5. Ce que ce rapport ne prouve pas

- La **population** est la population **legale** (HCP), pas la population presente : la
  saisonnalite n'est pas couverte.
- Les **limites** sont simplifiees (tuilage zoom 7) : la superficie calculee (16 644 km2)
  depasse les valeurs des monographies HCP et **ne doit pas etre publiee** comme officielle.
- La **licence HCP** n'est pas encore confirmee par ecrit (D-010).
"""

ANOMALIES = """# Anomalies du referentiel — et comment elles sont traitees

> Tenu par le **Membre A**. Date : __DATE__. Ce document repond a la tache **A-12**.
> Regle : une anomalie n'est supprimee que si elle est expliquee. Aucune valeur inventee.

## 1. 150 geometries -> 146 communes officielles

| # | Cause | Effet | Traitement |
|---|---|---|---|
| 1 | **Ceuta** (`MA-01-573-0100`, « Sebta ») figure dans le jeu national | +1 | **Exclue** : hors souverainete marocaine, hors perimetre du datathon |
| 2 | **Tanger** livree en **4 arrondissements** (Bni Makada, Mghogha, Souani, Medina) alors que le HCP la compte pour **1 commune** | +3 | **Agreges** sous une cle unique, population sommee |

Resultat : 146 communes, identiques au decoupage HCP (2 prefectures + 6 provinces).

## 2. Population

| Anomalie | Traitement |
|---|---|
| Population **legale** et non population presente | Documente comme limite ; la saisonnalite n'est pas modelisee |
| Millesimes melanges (RGPH 2014 pour l'historique, RGPH 2024 pour la reference) | La colonne publiee est `population_2024` ; le fichier 2014 reste dans `data/raw/` |
| Somme regionale | **4 030 222** habitants, verifiee sur les 146 lignes |

## 3. Milieu de residence

Le HCP annonce **17 communes urbaines et 129 rurales**. Notre fichier contient
**17 urbaines, 60 mixtes et 69 rurales**. Ecart explique : la categorie `Mixte`
(D-006) separe les communes qui ont des douars urbains **et** ruraux ; elle n'existe pas
dans la nomenclature HCP. La somme reste 146.

## 4. Etablissements de sante

| Anomalie | Traitement |
|---|---|
| **5 hopitaux sans nom** sur 66 (OSM) | Conserves : position valide, identifiant OSM stable, le nom n'entre dans aucun calcul |
| **16 hopitaux officiels sur 24** retrouves par le nom | Documente ; les 8 autres ne sont pas geolocalises et ne sont pas inventes |
| Aucun `health_post` (dispensaire) dans OSM | Limite majeure assumee : le milieu rural est sous-represente (cf. 299 etablissements du MSPS) |
| Pas de hierarchie officielle ni de capacite | Non disponible en open data ; le score ne depend que du **temps** |

## 5. Temps de trajet et accessibilite

| Anomalie | Traitement |
|---|---|
| Temps « normaux », sans trafic ni route coupee | Documente ; la variante « route coupee » est un scenario du rapport, pas une donnee |
| Communes tres isolees | 38 communes a plus de 60 min ; maximum **120,2 min** (Tamorot, Chefchaouen) |
| 5 hopitaux sans nom utilises comme destination | Aucun impact : le temps est calcule vers un point, pas vers un nom |
| Bornes 15 / 45 min | Sensibilite faite sur 6 variantes : 91 communes changent de classe, le classement ne change pas (D-015) |

## 6. Codes et noms

| Anomalie | Traitement |
|---|---|
| Zero initial dans les codes (`051`) | Tous les codes sont lus en **texte** ; jamais de jointure sur le nom |
| Meme commune ecrite de plusieurs facons (M'diq / Mdiq / المضيق) | Jointure uniquement sur `commune_code` ; `name_fr` sert a l'affichage |

## 7. Ce qu'il reste a faire

- Confirmer la **licence HCP** (D-010) avant toute redistribution.
- Geocoder les **8 hopitaux officiels** manquants.
- Integrer la liste MSPS (`essp-2025.xlsx`) pour couvrir le milieu rural.
"""

# ---------------------------------------------------------------------------
# 9. README : vraies instructions Docker
# ---------------------------------------------------------------------------

AVANT_DOCKER = (
    "Les instructions pour Docker (Airflow, PostgreSQL) et Streamlit seront ajoutées ici."
)
APRES_DOCKER = """### Base de données (PostgreSQL)

```bat
copy .env.example .env
docker compose up -d
docker compose ps
```

La base écoute sur le port **5433** (et non 5432, pour ne pas gêner un PostgreSQL déjà
installé). Les tables sont créées automatiquement au premier démarrage par `sql/init.sql`.
Pour vérifier :

```bat
docker exec -it postgres_tta_risk psql -U user -d tta_risk -c "\\dt weather.*"
```

> **Ne jamais lancer `docker compose down -v`** : l'option `-v` efface le volume, donc
> les 10 ans d'historique météorologique et les seuils. Pour repartir de zéro sur les
> seuils uniquement : `DROP TABLE weather.thresholds;` puis `psql -f sql/init.sql`.

### Airflow et Streamlit

Les deux sont **encore à écrire** (`airflow/dags/daily_risk_dag.py`,
`airflow/Dockerfile` et `app/streamlit_app.py` sont vides). Les commandes seront ajoutées
ici à leur livraison."""

# ---------------------------------------------------------------------------
# 16. Modele de Pull Request
# ---------------------------------------------------------------------------

MODELE_PR = """## Ce que fait cette PR

<!-- Une phrase. Exemple : ajoute les 4 colonnes du score dans weather.risk_daily. -->

## Pourquoi

<!-- Le probleme corrige ou la tache du plan concernee (A-xx, T-xx, D-xx). -->

## Comment le tester

```bat
python -m pytest -q
```

<!-- Une commande precise si la PR touche la base ou un script. -->

## Checklist

- [ ] `python -m pytest -q` passe en local
- [ ] `ruff check .` passe
- [ ] une branche = une PR (pas de `main` en direct)
- [ ] aucun fichier ajoute avec `git add .` (un `git add` par fichier)
- [ ] aucun secret : pas de cle ORS, pas de `.env`
- [ ] si la base change : migration SQL fournie et testee
- [ ] si un fichier de donnees change : le dictionnaire des variables est mis a jour

## Donnees touchees

<!-- Cocher ce qui est concerne -->
- [ ] aucune
- [ ] `data/processed/*.csv`
- [ ] `data/processed/*.geojson`
- [ ] `sql/init.sql`
- [ ] `docs/data_dictionary.md`
"""

# ---------------------------------------------------------------------------
# 17. Makefile (attention : les recettes EXIGENT des tabulations)
# ---------------------------------------------------------------------------

MAKEFILE = """# Raccourcis du projet TTA Health Access Risk.
# Sous Windows, utiliser Git Bash ou WSL : make n'est pas fourni avec CMD.
# Les commandes CMD equivalentes sont dans le README, section 3.

.PHONY: help install test lint format check travel zones thresholds forecast risk app clean

help:
\t@echo "install     installe les dependances de developpement"
\t@echo "test        lance les tests rapides (sans base, sans reseau)"
\t@echo "lint        ruff check"
\t@echo "format      ruff format (reecrit les fichiers)"
\t@echo "check       lint + format check + tests"
\t@echo "travel      calcule les temps de trajet (OpenRouteService)"
\t@echo "zones       calcule les zones 15/30/45/60 min"
\t@echo "thresholds  calcule les seuils p65/p80/p90"
\t@echo "forecast    charge les previsions Open-Meteo dans la base"
\t@echo "risk        calcule le danger et le score du jour"
\t@echo "app         lance l'application Streamlit"
\t@echo "clean       supprime les caches Python"

install:
\tpip install -r requirements/dev.txt

test:
\tpython -m pytest -q -m "not integration and not external"

lint:
\truff check .

format:
\truff format .

check: lint test

travel:
\tpython scripts/build_travel_time.py

zones:
\tpython scripts/build_access_zones.py

thresholds:
\tpython scripts/build_thresholds.py

forecast:
\tpython -m src.tta_risk.weather.forecast_loader

risk:
\tpython scripts/run_risk_daily.py

app:
\tstreamlit run app/streamlit_app.py

clean:
\tpython -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
"""

# ---------------------------------------------------------------------------
# 19. Docstrings des deux paquets encore vides
# ---------------------------------------------------------------------------

INIT_ROUTING = '''"""Calcul des temps de trajet (reserve).

Le code vit pour l'instant dans `scripts/build_travel_time.py` : ce script contient
l'appel a OpenRouteService, la gestion des `radiuses` et le cache des reponses.
Il sera deplace ici quand il devra etre appele autrement que depuis la ligne de
commande.
"""
'''

INIT_INGEST = '''"""Chargement des donnees sources (reserve).

Le chargement des communes, des hopitaux et des contours se fait aujourd'hui dans
`src/tta_risk/reference/` (`build_referentiel.py`, `build_milieu.py`,
`build_demographics.py`). Ce paquet reste vide tant que ces scripts n'ont pas
besoin d'une API commune.
"""
'''

# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------


def lire(chemin: str) -> str:
    fichier = RACINE / chemin
    if not fichier.is_file():
        sys.exit(
            f"ERREUR : {chemin} introuvable.\n"
            "Lance ce script depuis la racine du depot (le dossier qui contient README.md)."
        )
    return fichier.read_text(encoding="utf-8")


def corriger(texte: str, avant: str, apres: str) -> str:
    if avant not in texte:
        sys.exit(
            "ERREUR : un texte attendu est introuvable (fichier deja corrige, ou version "
            "differentielle). Rien n'a ete ecrit. Relance apres avoir verifie ta branche."
        )
    return texte.replace(avant, apres, 1)


def main() -> None:
    print("corriger_proprete_A v1")

    a_ecrire: list[tuple[str, str]] = []
    a_supprimer: list[str] = []
    deja: list[str] = []

    # --- 5. methodology.md ------------------------------------------------
    methodo_avant = lire("docs/methodology.md")
    methodo = methodo_avant
    for avant, apres, etiquette in CORRECTIONS_METHODOLOGY:
        if apres in methodo:
            deja.append(etiquette)
            continue
        methodo = corriger(methodo, avant, apres)
    if methodo != methodo_avant:
        a_ecrire.append(("docs/methodology.md", methodo))

    # --- 6. dictionnaire --------------------------------------------------
    dico_avant = lire("docs/data_dictionary.md")
    dico = dico_avant
    if "5 hôpitaux sans nom" not in dico:
        ancre = "| Recoupement Ministère |"
        if ancre not in dico:
            sys.exit("ERREUR : ancre §3.1 introuvable. Rien n'a ete ecrit.")
        dico = dico.replace(ancre, LIGNE_HOPITAUX_ANONYMES + ancre, 1)
    else:
        deja.append("dictionnaire : hopitaux sans nom")
    if AVANT_MILIEU in dico:
        dico = dico.replace(AVANT_MILIEU, APRES_MILIEU, 1)
    elif "`Mixte` (60)" in dico:
        deja.append("dictionnaire : milieu")
    else:
        sys.exit("ERREUR : ligne `milieu` du §4 introuvable. Rien n'a ete ecrit.")
    if dico != dico_avant:
        a_ecrire.append(("docs/data_dictionary.md", dico))

    # --- 7 et 8. documents manquants -------------------------------------
    for chemin, contenu in (
        ("docs/rapport_qualite_v1.md", RAPPORT_QUALITE),
        ("docs/anomalies_referentiel.md", ANOMALIES),
    ):
        if (RACINE / chemin).is_file():
            deja.append(chemin)
        else:
            a_ecrire.append((chemin, contenu.replace("__DATE__", AUJOURDHUI)))

    # --- 9. README : Docker ----------------------------------------------
    readme_avant = lire("README.md")
    readme = readme_avant
    if AVANT_DOCKER in readme:
        readme = readme.replace(AVANT_DOCKER, APRES_DOCKER, 1)
    elif "### Base de donnees (PostgreSQL)" in readme:
        deja.append("README : Docker")
    else:
        sys.exit("ERREUR : phrase Docker du README introuvable. Rien n'a ete ecrit.")
    if readme != readme_avant:
        a_ecrire.append(("README.md", readme))

    # --- 16. modele de PR -------------------------------------------------
    modele = RACINE / ".github/pull_request_template.md"
    if modele.is_file() and modele.stat().st_size > 0:
        deja.append("modele de PR")
    else:
        a_ecrire.append((".github/pull_request_template.md", MODELE_PR))

    # --- 17. Makefile ------------------------------------------------------
    makefile = RACINE / "Makefile"
    if makefile.is_file() and makefile.stat().st_size > 0:
        deja.append("Makefile")
    else:
        a_ecrire.append(("Makefile", MAKEFILE))

    # --- 19. paquets vides -------------------------------------------------
    for chemin, contenu in (
        ("src/tta_risk/routing/__init__.py", INIT_ROUTING),
        ("src/tta_risk/ingest/__init__.py", INIT_INGEST),
    ):
        fichier = RACINE / chemin
        if fichier.is_file() and fichier.stat().st_size > 0:
            deja.append(chemin)
        else:
            a_ecrire.append((chemin, contenu))

    # --- 21. seuil de couverture dans la CI -------------------------------
    ci = lire(".github/workflows/ci.yml")
    si = 'pytest -m "not integration and not external" --cov=src'
    if "--cov-fail-under" in ci:
        deja.append("CI : seuil de couverture")
    elif si in ci:
        ci = ci.replace(si, si + " --cov-fail-under=10", 1)
        a_ecrire.append((".github/workflows/ci.yml", ci))
    else:
        sys.exit("ERREUR : ligne pytest du ci.yml introuvable. Rien n'a ete ecrit.")

    # --- 24. script de bricolage ------------------------------------------
    bricolage = "scripts/script_test_forecast_api_meteo.py"
    if (RACINE / bricolage).is_file():
        a_supprimer.append(bricolage)
    else:
        deja.append(bricolage)

    # --- Ecriture ---------------------------------------------------------
    for chemin, contenu in a_ecrire:
        destination = RACINE / chemin
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(contenu, encoding="utf-8")
        print(f"OK   {chemin}")

    for chemin in a_supprimer:
        (RACINE / chemin).unlink()
        print(f"SUPPRIME  {chemin}")

    for etiquette in deja:
        print(f"deja fait : {etiquette}")

    print()
    print(f"{len(a_ecrire)} fichier(s) ecrit(s), {len(a_supprimer)} supprime(s).")
    print("Aucun fichier de scoring, aucune base de donnees n'a ete touche.")
    print("Pense a : git rm scripts/script_test_forecast_api_meteo.py")


if __name__ == "__main__":
    main()
