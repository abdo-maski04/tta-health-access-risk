"""Corrige d'un seul coup les erreurs de documentation du depot TTA.

Ce script ne touche NI au code NI a la base de donnees. Il corrige uniquement
des textes qui ne correspondent plus a la realite de `main` :

  1. docs/data_dictionary.md  : sections 4, 5 et 6 reecrites sur les vraies
                                colonnes + sommaire + numero de version
  2. README.md                : sql/schema.sql, liste reelle des tables,
                                `git add .` (interdit par l'equipe), noms de
                                branches, activation du venv en CMD, modules
                                annonces mais encore vides
  3. docs/decisions.md        : nouvelle decision D-018 + ligne D-008 perimee
  4. LICENSE                  : texte MIT (le fichier etait vide alors que le
                                README annoncait deja une licence MIT)

Utilisation, depuis la racine du depot (le dossier qui contient README.md) :

    python scripts/corriger_erreurs_A.py

Securite : le script controle d'abord que chaque colonne des CSV livres et
chaque colonne des tables SQL est bien documentee, puis verifie tous les
reperes. Si un seul controle echoue, il s'arrete SANS RIEN ecrire.
Aucune dependance externe, aucun appel reseau, aucune base de donnees.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

RACINE = Path.cwd()
AUJOURDHUI = date.today().isoformat()

# ---------------------------------------------------------------------------
# 1. Nouveau contenu des sections 4, 5 et 6 du dictionnaire des variables
# ---------------------------------------------------------------------------

BLOC_4 = """## 4. `travel_time` — temps de trajet *(propriété A)*

**Fichier livré :** `data/processed/travel_time_TTA_2024.csv` — **146 lignes × 15 colonnes**, une ligne par commune.
**Statut en base :** les temps sont aujourd'hui lus depuis ce CSV ; une table `accessibility.travel_time` est prévue
et devra contenir exactement les mêmes colonnes.

| Variable | Type | Unité | Source | Statut | Description / limites |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé. Une seule ligne par commune. |
| `name_fr` | texte | — | Référentiel §1 | `OFFICIEL` | Nom d'affichage. **Jamais utilisé pour une jointure.** |
| `province` | texte | — | Référentiel §1 | `OFFICIEL` | Province ou préfecture (8 valeurs). |
| `milieu` | texte | — | Référentiel §1 | `OFFICIEL` | `Urbain` / `Rural`. |
| `start_lat` / `start_lon` | décimal | degrés | Référentiel §1 | `CALCULE` | Point de départ : point représentatif intérieur (D-002). Ordre lat puis lon. |
| `hospital_osm_type` | texte | — | OpenStreetMap | `OBSERVE` | `node` / `way` / `relation` de l'établissement retenu. |
| `hospital_osm_id` | texte | — | OpenStreetMap | `OBSERVE` | Identifiant OSM : clé stable de l'établissement. |
| `hospital_name` | texte | — | OpenStreetMap | `OBSERVE` | Nom de l'hôpital (parfois en arabe). |
| `hospital_lat` / `hospital_lon` | décimal | degrés | OpenStreetMap | `OBSERVE` | Coordonnées de l'hôpital. |
| `distance_km` | décimal | km | OpenRouteService | `CALCULE` | Distance routière réelle. |
| `temps_min` | décimal | minutes | OpenRouteService | `CALCULE` | Temps de trajet routier : 1,0 (min) / 36,7 (médiane) / 120,2 (max). **Ne vaut pas garantie en urgence.** |
| `classe_trajet` | entier | 1-3 | Calculé | `CALCULE` | 1 = moins de 15 min, 2 = de 15 à 45 min, 3 = plus de 45 min (D-015). Distribution : 22 / 66 / 58. |
| `methode` | texte | — | — | — | `ORS_DRIVING_CAR` sur les 146 lignes. Aucun `DETOUR_1.4` n'a été livré. |

La population de la commune n'est **pas** dans ce fichier : elle se trouve dans `communes_TTA_2024.csv` (§1)
et elle est reprise dans `access_zones_TTA.csv` (§4.1).

### 4.1 Zones d'accessibilité — `access_zones_TTA.csv`

**146 lignes × 13 colonnes**, dérivées du fichier ci-dessus par `scripts/build_access_zones.py` (PR #15) :
`commune_code`, `name_fr`, `province`, `milieu`, `population_2024`, `temps_min`, `distance_km`, `hospital_name`,
`zone_15_min`, `zone_30_min`, `zone_45_min`, `zone_60_min` (drapeaux 0/1) et `zone` (texte).

| Zone | Communes | Part | Population | Part |
|---|---|---|---|---|
| ≤ 15 min | 22 | 15,1 % | 2 543 958 | 63,1 % |
| ≤ 30 min | 59 | 40,4 % | 3 087 495 | 76,6 % |
| ≤ 45 min | 88 | 60,3 % | 3 374 547 | 83,7 % |
| ≤ 60 min | 108 | 74,0 % | 3 591 480 | 89,1 % |
| > 60 min | 38 | 26,0 % | 438 742 | 10,9 % |

**Colonnes retirées du dictionnaire v1 :** `facility_id` (remplacé par `hospital_osm_type` + `hospital_osm_id`),
`minutes` (vrai nom : `temps_min`) et `unpaved_share` (jamais calculé : le tag OSM `surface` n'est pas disponible
sur les 146 tracés).

---

"""

BLOC_5 = """## 5. Météo & seuils *(propriété B)*

Trois tables PostgreSQL du schéma `weather` (créées par `sql/init.sql`). Ce ne sont pas des fichiers livrés :
elles sont alimentées par `src/tta_risk/weather/` et les scripts de `scripts/`.

### 5.1 `weather.weather_daily` — historique météorologique

| Variable | Type | Unité | Source | Statut | Description |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé, avec `date`. |
| `date` | date | — | Open-Meteo | `OBSERVE` | Jour observé. |
| `precipitation_sum` | décimal | mm | Open-Meteo | `OBSERVE` | Cumul de pluie du jour. |
| `temperature_2m_max` | décimal | °C | Open-Meteo | `OBSERVE` | Température maximale du jour. |
| `ingested_at` | horodatage | — | Base | — | Date d'écriture, automatique. |

### 5.2 `weather.thresholds` — seuils mensuels

| Variable | Type | Unité | Source | Statut | Description |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé, avec `month`. |
| `month` | petit entier | 1-12 | — | — | Mois calendaire. |
| `rain_p65` / `rain_p80` / `rain_p90` | décimal | mm | Historique calculé | `CALCULE` | Niveau 1 = p65, 2 = p80, 3 = p90 (D-014). |
| `heat_p65` / `heat_p80` / `heat_p90` | décimal | °C | Historique calculé | `CALCULE` | Mêmes seuils appliqués à `temperature_2m_max`. |
| `computed_at` | horodatage | — | Base | — | Date de calcul. |

Une ligne par commune et par mois : 146 × 12 = 1 752 attendues.

### 5.3 `weather.forecast_daily` — prévisions

| Variable | Type | Unité | Source | Statut | Description |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé, avec les deux dates. |
| `forecast_issued_on` | date | — | — | — | **Date de récupération** de la prévision. |
| `target_date` | date | — | — | `PREVU` | **Jour visé** par la prévision (horizon de 3 jours). |
| `precip_mm` | réel | mm | Open-Meteo | `PREVU` | Pluie prévue. |
| `tmax_c` | réel | °C | Open-Meteo | `PREVU` | Température maximale prévue. |
| `ingested_at` | horodatage | — | Base | — | Date d'écriture, automatique. |

Clé : (`commune_code`, `forecast_issued_on`, `target_date`).

> Piège : ne jamais confondre `forecast_issued_on` (quand on a récupéré) et `target_date` (le jour prévu).
> C'était exactement le bug corrigé en PR #14.

**Colonnes retirées du dictionnaire v1 :** `precipitation_probability_max` (non récupérée),
`horizon_jours` (= `target_date` − `forecast_issued_on`, recalculable), `source_fetch_time` (= `ingested_at`),
`nb_observations` (non stocké ; la fiabilité des seuils est contrôlée par `tests/test_thresholds.py`).

---

"""

BLOC_6 = """## 6. `weather.risk_daily` — sortie du danger quotidien *(propriété B, complétée par A)*

Table écrite par `scripts/run_risk_daily.py`. **État actuel : le danger météo est écrit, le score ne l'est pas
encore** — les quatre colonnes du score sont ajoutées à l'étape suivante (dernière ligne de ce tableau).

| Variable | Type | Unité | Statut | Description |
|---|---|---|---|---|
| `commune_code` | texte | — | — | Clé, avec les deux dates. |
| `forecast_issued_on` | date | — | — | Date de récupération de la prévision. |
| `target_date` | date | — | — | Jour visé. |
| `precip_mm` | réel | mm | `PREVU` | Pluie prévue. |
| `tmax_c` | réel | °C | `PREVU` | Température maximale prévue. |
| `rain_level` | petit entier | 0-3 | `CALCULE` | Niveau pluie : 0 si moins de 1 mm ; 1 si ≥ p65 ; 2 si ≥ p80 ; 3 si ≥ p90. |
| `heat_level` | petit entier | 0-3 | `CALCULE` | Niveau chaleur, mêmes seuils appliqués à `tmax_c`. |
| `danger` | petit entier | 0-3 | `CALCULE` | `max(rain_level, heat_level)`. C'est le `danger_meteo` de la méthodologie. |
| `dominant` | texte | — | `CALCULE` | Météo dominante **uniquement** : `rain` / `heat` / `both` / `none`. Ne vaut jamais `eloignement` (D-018). |
| `computed_at` | horodatage | — | — | Date d'écriture, automatique. |

> Les quatre colonnes suivantes seront ajoutées par le module de scoring (décision D-018) :
> `classe_trajet` (1-3), `score` (0, 1, 2, 3, 4, 6, 9), `niveau` (`vert` / `jaune` / `orange` / `rouge`)
> et `raison` (`pluie` / `chaleur` / `eloignement`).
> **`raison` est le facteur affiché ; `dominant` ne parle que de météo.** Les deux colonnes coexistent,
> aucune ne remplace l'autre.

**Colonnes retirées du dictionnaire v1 :** `danger_meteo` (nom réel : `danger`), `composante_pluie` et
`composante_chaleur` (noms réels : `rain_level` et `heat_level`), `date` (nom réel : `target_date`),
`population_exposee` (calculée à l'affichage et dans l'export, jamais stockée commune par commune),
`qualite_donnees` et `statut_peremption` (jamais calculés : la fraîcheur se lit avec `forecast_issued_on`
et `computed_at`).

---

"""

# ---------------------------------------------------------------------------
# 2. Corrections du README : (texte exact present dans le fichier, remplacement)
# ---------------------------------------------------------------------------

CORRECTIONS_README = [
    (
        "| `Makefile` | Raccourcis de commandes (installer, tester, lancer l'application, "
        "construire les données). |",
        "| `Makefile` | **Encore vide.** Destiné aux raccourcis de commandes (installer, tester, lancer). |",
        "README : ligne Makefile",
    ),
    (
        "| `docker-compose.yml` | Lance Airflow et PostgreSQL ensemble en une commande. |",
        "| `docker-compose.yml` | Lance PostgreSQL seul (service `postgres`, port 5433) et applique "
        "`sql/init.sql`. Le service Airflow n'est pas encore ajouté. |",
        "README : ligne docker-compose.yml",
    ),
    (
        "| `data/raw/` | Fichiers sources tels que reçus (HCP 2024, GeoVulnera). Ne pas modifier. |",
        "| `data/raw/` | Fichiers sources tels que reçus (HCP : population légale RGPH 2014 et 2024). "
        "Ne pas modifier. |",
        "README : ligne data/raw",
    ),
    (
        "| `data/processed/` | Jeu de données final livrable (CSV/Parquet/GeoJSON) et export de démo hors ligne. |",
        "| `data/processed/` | Jeu de données livrable : 4 CSV et 2 GeoJSON, tous construits par les "
        "scripts de `scripts/`. |",
        "README : ligne data/processed",
    ),
    (
        "| `src/tta_risk/config.py` | Paramètres centraux (chemins, URLs, lecture du `.env`). |",
        "| `src/tta_risk/config.py` | **Encore vide.** Destiné aux paramètres centraux "
        "(chemins, URLs, lecture du `.env`). |",
        "README : ligne config.py",
    ),
    (
        "| `src/tta_risk/ingest/` | Chargement des communes, des hôpitaux et des contours. |",
        "| `src/tta_risk/ingest/` | **Encore vide** : le chargement des communes, des hôpitaux et des "
        "contours se fait dans `src/tta_risk/reference/`. |",
        "README : ligne ingest/",
    ),
    (
        "| `src/tta_risk/routing/` | Client OpenRouteService et calcul des temps de trajet. |",
        "| `src/tta_risk/routing/` | **Encore vide** : le client OpenRouteService est pour l'instant "
        "dans `scripts/build_travel_time.py`. |",
        "README : ligne routing/",
    ),
    (
        "| `src/tta_risk/scoring/` | Danger météo, classe de trajet, score, couleur, raison principale. |",
        "| `src/tta_risk/scoring/` | Danger météo (`danger.py`, B), classe de trajet, score, couleur et "
        "raison principale (`score.py`, A). |\n"
        "| `src/tta_risk/reference/` | Construction du référentiel, de la démographie, du milieu et du "
        "livrable (`build_referentiel.py`, `build_demographics.py`, `build_milieu.py`, `build_livrable.py`). |",
        "README : ligne scoring/ + ajout reference/",
    ),
    (
        "| `scripts/` | Points d'entrée de la partie fixe, lancés une seule fois (`build_communes`, "
        "`build_hospitals`, `build_travel_time`, `build_thresholds`). |",
        "| `scripts/` | Points d'entrée : partie fixe lancée une seule fois (`build_travel_time.py`, "
        "`build_access_zones.py`, `build_thresholds.py`) et partie quotidienne (`run_risk_daily.py`). |",
        "README : ligne scripts/",
    ),
    (
        "| `sql/schema.sql` | Création des tables (`communes`, `hospitals`, `travel_time`, "
        "`thresholds`, `forecast_daily`, `risk_daily`). |",
        "| `sql/init.sql` | Crée les tables au premier démarrage de PostgreSQL : "
        "`weather.weather_daily`, `weather.thresholds`, `weather.forecast_daily`, `weather.risk_daily`. |",
        "README : ligne sql/schema.sql",
    ),
    (
        "| `docker/postgres/init.sql` | Crée automatiquement la base `tta_risk` au premier "
        "démarrage de PostgreSQL. |",
        "| `sql/upsert.sql` | Requête d'insertion avec mise à jour (`ON CONFLICT`) "
        "pour l'historique météo. |",
        "README : ligne docker/postgres/init.sql",
    ),
    (
        "| `airflow/dags/` | Le DAG quotidien (`daily_risk_dag.py`). Il reste **fin** : "
        "il appelle seulement des fonctions de `src/`. |",
        "| `airflow/dags/` | Le DAG quotidien (`daily_risk_dag.py`). **Encore vide, à écrire** ; "
        "il restera **fin** : il appellera seulement des fonctions de `src/`. |",
        "README : ligne airflow/dags",
    ),
    (
        "| `airflow/Dockerfile` | Image Airflow avec nos dépendances et accès à `src/`. |",
        "| `airflow/Dockerfile` | Image Airflow avec nos dépendances et accès à `src/`. "
        "**Encore vide, à écrire.** |",
        "README : ligne airflow/Dockerfile",
    ),
    (
        "| `app/streamlit_app.py` | Application web : carte, filtres, détail par commune. |",
        "| `app/streamlit_app.py` | Application web : carte, filtres, détail par commune. "
        "**Encore vide, à écrire.** |",
        "README : ligne streamlit_app.py",
    ),
    (
        "```powershell\ngit clone",
        "```bat\ngit clone",
        "README : bloc de commandes tagué powershell",
    ),
    (
        ".venv\\Scripts\\Activate.ps1\n",
        ".venv\\Scripts\\activate.bat\n",
        "README : activation du venv en CMD",
    ),
    (
        "Linux/macOS : `source .venv/bin/activate` et `cp .env.example .env`.",
        "Sous PowerShell, remplacer `activate.bat` par `.venv\\Scripts\\Activate.ps1`.\n"
        "Linux/macOS : `source .venv/bin/activate` et `cp .env.example .env`.",
        "README : variante PowerShell",
    ),
    (
        "1. **Chacun a sa branche personnelle** : `abderrahmane`, `membre-b`, `membre-c`.\n"
        "   On ne commite **jamais** directement sur `main`.",
        "1. **`main` est protégée.** On ne commite **jamais** directement dessus : on travaille sur une\n"
        "   branche (`abderrahmane/dev` pour le pipeline, `feat/...` ou `fix/...` pour une modification\n"
        "   précise). **Une branche = une Pull Request.**",
        "README : noms de branches",
    ),
    (
        "# 3. Enregistrer\ngit add .\n",
        "# 3. Enregistrer UN fichier a la fois (jamais git add .)\ngit add scripts/build_thresholds.py\n",
        "README : git add dans la boucle quotidienne",
    ),
    (
        "| `git add .` | Prépare toutes les modifications pour le commit. |",
        "| `git add <fichier>` | Prépare **un** fichier pour le commit. Jamais `git add .` "
        "ni `git add -A` : ça ramasse des fichiers oubliés. |",
        "README : tableau des commandes git",
    ),
    (
        "puis `git add .` et `git commit`.",
        "puis `git add` sur chaque fichier corrigé et `git commit`.",
        "README : résolution de conflit",
    ),
]

# ---------------------------------------------------------------------------
# 3. Décisions : ligne D-008 périmée + nouvelle décision D-018
# ---------------------------------------------------------------------------

D_008_AVANT = (
    "| D-008 | Seuils de trajet : garder 15/45 min ou ajuster ? | Semaine 2 (avec B) | "
    "Classes du score | **Examiner la distribution d'abord**, puis figer par écrit |"
)
D_008_APRES = (
    "| D-008 | Seuils de trajet : garder 15/45 min ou ajuster ? | **Tranchée** | "
    "Classes du score | Voir **D-015** : bornes 15/45 conservées après analyse de sensibilité |"
)

D_018 = """
---

## D-018 — Deux champs, deux rôles : `dominant` (météo) et `raison` (facteur affiché)
**Date :** __DATE__ · **Décideur :** Membre A (validée avec B) · **Statut :** ✅ adoptée

**Contexte.** Deux vocabulaires coexistent et ne décrivent pas la même chose :
`score.py` renvoie une `raison` en français (`pluie`, `chaleur`, `eloignement`), alors que la table
`weather.risk_daily` stocke `dominant` en anglais (`rain`, `heat`, `both`, `none`) avec une contrainte
`CHECK`. Écrire `eloignement` dans `dominant` fait **rejeter la ligne par PostgreSQL**.

**Décision.** On garde les deux colonnes, chacune avec son rôle :

| Champ | Où | Valeurs | Ce qu'il dit |
|---|---|---|---|
| `dominant` | `weather.risk_daily` (B) | `rain` / `heat` / `both` / `none` | Quelle **météo** domine, et rien d'autre |
| `raison` | `weather.risk_daily` (A) | `pluie` / `chaleur` / `eloignement` | Quel **facteur est affiché** à l'utilisateur |

**Règle de départage de `raison`.** On compare les trois composantes (`rain_level`, `heat_level`,
`classe_trajet`) et on garde la plus grande ; en cas d'égalité, l'ordre est **pluie**, puis **chaleur**,
puis **éloignement**. Une commune sans danger météo (`dominant = none`) a donc toujours
`raison = eloignement` : le seul facteur qui reste est la distance.

**Conséquence.** Aucun renommage, aucune donnée existante ne bouge, aucune contrainte SQL ne casse.
Le dictionnaire des variables (§6) documente la différence.

**Alternative écartée.** Renommer `dominant` en `raison` et y mettre les valeurs françaises : cela casse
la contrainte `CHECK` existante et impose une migration des lignes déjà écrites par B, pour un gain nul.
"""

# ---------------------------------------------------------------------------
# 4. Licence MIT (le fichier était vide, le README annonçait déjà MIT)
# ---------------------------------------------------------------------------

LICENCE_MIT = """MIT License

Copyright (c) 2026 Equipe TTA Health Access Risk - FST Tanger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------


def lire(chemin: str) -> str:
    """Lit un fichier du depot, ou arrete tout si le fichier manque."""
    fichier = RACINE / chemin
    if not fichier.is_file():
        sys.exit(
            f"ERREUR : {chemin} introuvable.\n"
            "Lance ce script depuis la racine du depot (le dossier qui contient README.md)."
        )
    return fichier.read_text(encoding="utf-8")


def colonnes_csv(chemin: str) -> list[str]:
    """Entete d'un CSV livre, ou liste vide si le fichier n'est pas la."""
    fichier = RACINE / chemin
    if not fichier.is_file():
        return []
    entete = fichier.read_text(encoding="utf-8").splitlines()[0]
    return [nom.strip().strip('"') for nom in entete.split(",")]


def colonnes_table(sql: str, table: str) -> list[str]:
    """Noms de colonnes d'une table declaree dans sql/init.sql."""
    debut = sql.find(f"CREATE TABLE IF NOT EXISTS weather.{table}")
    if debut < 0:
        return []
    fin = sql.find(");", debut)
    corps = sql[debut:fin].splitlines()[1:]
    noms = []
    for ligne in corps:
        ligne = ligne.strip()
        if (
            not ligne
            or ligne.startswith("--")
            or ligne.upper().startswith(("PRIMARY", "CONSTRAINT"))
        ):
            continue
        nom = re.split(r"[\s,]+", ligne)[0].strip()
        if nom:
            noms.append(nom)
    return noms


def verifier_colonnes_documentees() -> None:
    """Controle qu'aucune colonne livree n'est oubliee dans les nouvelles sections."""
    controles = [
        ("data/processed/travel_time_TTA_2024.csv", BLOC_4, "section 4"),
        ("data/processed/access_zones_TTA.csv", BLOC_4, "section 4.1"),
    ]
    for chemin, bloc, etiquette in controles:
        oubliees = [c for c in colonnes_csv(chemin) if f"`{c}`" not in bloc]
        if oubliees:
            sys.exit(
                f"ERREUR : colonnes de {chemin} absentes du dictionnaire ({etiquette}) : "
                f"{', '.join(oubliees)}. Rien n'a ete ecrit."
            )

    sql = lire("sql/init.sql")
    for table, bloc in (
        ("weather_daily", BLOC_5),
        ("thresholds", BLOC_5),
        ("forecast_daily", BLOC_5),
        ("risk_daily", BLOC_6),
    ):
        oubliees = [c for c in colonnes_table(sql, table) if f"`{c}`" not in bloc]
        if oubliees:
            sys.exit(
                f"ERREUR : colonnes de weather.{table} absentes du dictionnaire : "
                f"{', '.join(oubliees)}. Rien n'a ete ecrit."
            )


def remplacer_bloc(texte: str, debut: str, fin: str, nouveau: str) -> str:
    """Remplace tout ce qui se trouve entre deux reperes par `nouveau`."""
    if debut not in texte:
        sys.exit(f"ERREUR : repere de debut introuvable ({debut[:45]}). Rien n'a ete ecrit.")
    depart = texte.index(debut)
    if fin not in texte[depart:]:
        sys.exit(f"ERREUR : repere de fin introuvable ({fin[:45]}). Rien n'a ete ecrit.")
    arrivee = texte.index(fin, depart)
    return texte[:depart] + nouveau + texte[arrivee:]


def corriger(texte: str, avant: str, apres: str, etiquette: str) -> str:
    """Remplace une chaine unique, ou arrete tout si elle est absente."""
    if avant not in texte:
        sys.exit(f"ERREUR : texte attendu introuvable -> {etiquette}. Rien n'a ete ecrit.")
    return texte.replace(avant, apres, 1)


def main() -> None:
    print("corriger_erreurs_A v1")
    verifier_colonnes_documentees()
    modifs: list[tuple[str, str]] = []

    # --- 1. Dictionnaire des variables -----------------------------------
    dico = lire("docs/data_dictionary.md")
    if "Version 1.1" in dico:
        print("Info : dictionnaire deja corrige (version 1.1), il n'est pas retouche.")
    else:
        dico = corriger(
            dico,
            "Version 1.0 — 17 novembre 2026.",
            f"Version 1.1 — {AUJOURDHUI} (alignée sur le code de `main`).",
            "dictionnaire : numero de version",
        )
        dico = corriger(
            dico,
            "| 4 | Accessibilité *(semaine 2 — C)* | `accessibility.parquet` | à venir |",
            "| 4 | Temps de trajet et zones | `data/processed/travel_time_TTA_2024.csv`, "
            "`data/processed/access_zones_TTA.csv` | 146 × 15 et 146 × 13 |",
            "dictionnaire : ligne 4 du sommaire",
        )
        dico = corriger(
            dico,
            "| 5 | Météo & seuils *(semaine 2 — B)* | `historical_weather` / `thresholds` | à venir |",
            "| 5 | Météo & seuils *(B)* | `weather.weather_daily`, `weather.thresholds`, "
            "`weather.forecast_daily` | voir section 5 |",
            "dictionnaire : ligne 5 du sommaire",
        )
        dico = corriger(
            dico,
            "| 6 | Risque quotidien *(semaine 3)* | `risk_daily` | à venir |",
            "| 6 | Risque quotidien | `weather.risk_daily` (PostgreSQL) | 10 colonnes, voir section 6 |",
            "dictionnaire : ligne 6 du sommaire",
        )
        dico = remplacer_bloc(dico, "## 4. `accessibility`", "## 5. Météo & seuils", BLOC_4)
        dico = remplacer_bloc(dico, "## 5. Météo & seuils", "## 6. `risk_daily`", BLOC_5)
        dico = remplacer_bloc(dico, "## 6. `risk_daily`", "## 7. Pièges", BLOC_6)
        modifs.append(("docs/data_dictionary.md", dico))

    # --- 2. README --------------------------------------------------------
    readme = lire("README.md")
    if "| `sql/init.sql` |" in readme:
        print("Info : README deja corrige, il n'est pas retouche.")
    else:
        for avant, apres, etiquette in CORRECTIONS_README:
            readme = corriger(readme, avant, apres, etiquette)
        modifs.append(("README.md", readme))

    # --- 3. Journal des decisions ----------------------------------------
    decisions = lire("docs/decisions.md")
    if "D-018" in decisions:
        print("Info : D-018 deja presente, elle n'est pas ajoutee une deuxieme fois.")
    else:
        decisions = corriger(decisions, D_008_AVANT, D_008_APRES, "decisions : ligne D-008")
        decisions = decisions.rstrip() + "\n" + D_018.replace("__DATE__", AUJOURDHUI)
        modifs.append(("docs/decisions.md", decisions))

    # --- 4. Licence -------------------------------------------------------
    licence = RACINE / "LICENSE"
    if licence.is_file() and licence.stat().st_size == 0:
        modifs.append(("LICENSE", LICENCE_MIT))
    else:
        print("Info : LICENSE non vide, il n'est pas modifie.")

    # --- Ecriture de tout, a la fin seulement ----------------------------
    if not modifs:
        print("Rien a corriger : tout est deja a jour.")
        return

    for chemin, contenu in modifs:
        (RACINE / chemin).write_text(contenu, encoding="utf-8")
        print(f"OK   {chemin}")

    print()
    print(f"{len(modifs)} fichier(s) corrige(s).")
    print("Aucun fichier de code, aucune base de donnees n'a ete touche.")


if __name__ == "__main__":
    main()
