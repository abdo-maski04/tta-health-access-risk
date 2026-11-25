# tta-health-access-risk

Classement **quotidien** des 146 communes de la région Tanger-Tétouan-Al Hoceima (TTA)
selon le **risque de difficulté d'accès aux soins** :
météo prévue (pluie, chaleur) × temps de trajet vers l'hôpital × population.

Projet de l'équipe FST Tanger pour le **Datathon Data-Territoires 2026** (HCP).
Chaque commune reçoit une couleur (vert, jaune, orange, rouge) et une raison principale
(pluie, chaleur ou éloignement), affichée sur une carte Streamlit.

> ⚠️ Indicateur d'aide à la décision, **pas une alerte officielle**.

---

## 1. Comment ça marche (en bref)

1. **Partie fixe** (calculée une fois) : communes (HCP), hôpitaux (OpenStreetMap),
   temps de trajet (OpenRouteService), seuils météo locaux (Open-Meteo, 10 ans).
2. **Partie quotidienne** (Airflow) : prévisions → comparaison aux seuils →
   score de risque → classement → enregistrement en base.
3. **Affichage** : application Streamlit (carte, détail par commune, sélecteur de jour).

Formule détaillée : `docs/methodology.md`.

---

## 2. Contenu du dépôt : à quoi sert chaque élément

### Fichiers à la racine

| Fichier | Rôle |
|---|---|
| `README.md` | Ce document : présentation, installation, règles de travail. |
| `LICENSE` | Licence du **code** (MIT). Les données gardent leurs propres licences. |
| `.gitignore` | Liste ce que Git ne doit jamais versionner (`.env`, `.venv`, logs, fichiers temporaires). |
| `.env.example` | Modèle des variables secrètes attendues (ex. `ORS_API_KEY=`), **sans valeurs**. Chacun le copie en `.env` (jamais commité). |
| `pytest.ini` | Configuration des tests (indique que le code est dans `src/`). |
| `Makefile` | **Encore vide.** Destiné aux raccourcis de commandes (installer, tester, lancer). |
| `docker-compose.yml` | Lance PostgreSQL seul (service `postgres`, port 5433) et applique `sql/init.sql`. Le service Airflow n'est pas encore ajouté. |

### Dossiers

| Dossier | Contenu et intérêt |
|---|---|
| `requirements/` | Dépendances Python, en trois fichiers : `base.txt` (communes, données, base), `app.txt` (Streamlit, cartes), `dev.txt` (tests). Séparés pour éviter les conflits de versions avec Airflow. |
| `data/raw/` | Fichiers sources tels que reçus (HCP : population légale RGPH 2014 et 2024). Ne pas modifier. |
| `data/interim/` | Résultats intermédiaires (ex. historique météo brut). **Non versionné** (lourd, régénérable). |
| `data/processed/` | Jeu de données livrable : 4 CSV et 2 GeoJSON, tous construits par les scripts de `scripts/`. |
| `src/tta_risk/` | **Le cœur du projet** : tout le code réutilisable. |
| `src/tta_risk/config.py` | **Encore vide.** Destiné aux paramètres centraux (chemins, URLs, lecture du `.env`). |
| `src/tta_risk/ingest/` | **Encore vide** : le chargement des communes, des hôpitaux et des contours se fait dans `src/tta_risk/reference/`. |
| `src/tta_risk/routing/` | **Encore vide** : le client OpenRouteService est pour l'instant dans `scripts/build_travel_time.py`. |
| `src/tta_risk/weather/` | Client Open-Meteo (prévisions, historique) et calcul des seuils. |
| `src/tta_risk/scoring/` | Danger météo (`danger.py`, B), classe de trajet, score, couleur et raison principale (`score.py`, A). |
| `src/tta_risk/reference/` | Construction du référentiel, de la démographie, du milieu et du livrable (`build_referentiel.py`, `build_demographics.py`, `build_milieu.py`, `build_livrable.py`). |
| `src/tta_risk/db/` | Accès à la base PostgreSQL (connexion, lecture, écriture). |
| `scripts/` | Points d'entrée : partie fixe lancée une seule fois (`build_travel_time.py`, `build_access_zones.py`, `build_thresholds.py`) et partie quotidienne (`run_risk_daily.py`). |
| `sql/init.sql` | Crée les tables au premier démarrage de PostgreSQL : `weather.weather_daily`, `weather.thresholds`, `weather.forecast_daily`, `weather.risk_daily`. |
| `sql/upsert.sql` | Requête d'insertion avec mise à jour (`ON CONFLICT`) pour l'historique météo. |
| `airflow/dags/` | Le DAG quotidien (`daily_risk_dag.py`). **Encore vide, à écrire** ; il restera **fin** : il appellera seulement des fonctions de `src/`. |
| `airflow/Dockerfile` | Image Airflow avec nos dépendances et accès à `src/`. **Encore vide, à écrire.** |
| `app/streamlit_app.py` | Application web : carte, filtres, détail par commune. **Encore vide, à écrire.** |
| `notebooks/` | Exploration et essais. Le code final va dans `src/`, pas ici. |
| `tests/` | Tests automatiques. `tests/fixtures/` contient de petites données fictives pour tester sans réseau. |
| `docs/methodology.md` | La formule du risque, en une page. |
| `docs/data_dictionary.md` | Description de chaque colonne du jeu de données livrable. |
| `docs/decisions.md` | Registre des décisions (quoi, pourquoi, qui, quand). |
| `docs/report/` | Rapport du datathon (5 à 10 pages). |
| `.github/` | Modèle de Pull Request, modèles d'issues et workflow de tests automatiques (`ci.yml`). |

> Les fichiers `.gitkeep` ne servent qu'à garder un dossier vide dans Git. On peut les supprimer
> quand le dossier contient autre chose.

---

## 3. Installation

```bat
git clone https://github.com/abdo-maski04/tta-health-access-risk.git
cd tta-health-access-risk
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements/dev.txt
copy .env.example .env
pytest
```

Sous PowerShell, remplacer `activate.bat` par `.venv\Scripts\Activate.ps1`.
Linux/macOS : `source .venv/bin/activate` et `cp .env.example .env`.
Les instructions pour Docker (Airflow, PostgreSQL) et Streamlit seront ajoutées ici.

---

## 4. Travailler avec Git : le guide simple

### Les règles

1. **`main` est protégée.** On ne commite **jamais** directement dessus : on travaille sur une
   branche (`abderrahmane/dev` pour le pipeline, `feat/...` ou `fix/...` pour une modification
   précise). **Une branche = une Pull Request.**
2. **`main` doit toujours fonctionner.** On y fusionne seulement du code qui tourne.
3. **On fusionne souvent** (au moins une fois par jour de travail) pour éviter les gros conflits.
4. **Aucun secret dans Git** : clés API uniquement dans `.env`.
5. **Un coup d'œil d'un coéquipier** avant de fusionner une grosse modification.

### Pourquoi une branche personnelle ?

- `main` reste propre et démontrable à tout moment (important pour le jury).
- On peut tester, se tromper et recommencer sans gêner les autres.
- Chacun voit clairement qui a fait quoi.
- Les domaines étant séparés (données, pipeline, application), les conflits sont rares.

### Première fois : se placer sur sa branche

```bash
git clone <url-du-repo>
cd tta-health-access-risk
git checkout -b abderrahmane        # crée ta branche et s'y place
git push -u origin abderrahmane     # la publie sur GitHub
```

Ensuite, pour y revenir : `git checkout abderrahmane`.

### La boucle de tous les jours

```bash
# 1. Se mettre à jour AVANT de travailler
git checkout abderrahmane
git pull origin main        # récupère le travail des autres

# 2. Travailler, puis vérifier ce qui a changé
git status

# 3. Enregistrer UN fichier a la fois (jamais git add .)
git add scripts/build_thresholds.py
git commit -m "feat: ajoute le calcul des seuils de pluie"

# 4. Envoyer sur GitHub
git push
```

### Fusionner dans `main` (quand une étape est terminée)

1. Sur GitHub, ouvre une **Pull Request** : `abderrahmane` → `main`.
2. Décris en deux lignes ce qui change et comment le tester.
3. Un coéquipier jette un œil (idéalement).
4. Clique sur **Squash and merge**.
5. Retour en local : `git checkout abderrahmane` puis `git pull origin main`.

### Commandes essentielles

| Commande | Ce qu'elle fait |
|---|---|
| `git status` | Montre les fichiers modifiés. |
| `git pull origin main` | Récupère `main` dans ta branche actuelle. |
| `git add <fichier>` | Prépare **un** fichier pour le commit. Jamais `git add .` ni `git add -A` : ça ramasse des fichiers oubliés. |
| `git commit -m "message"` | Enregistre un point de sauvegarde local. |
| `git push` | Envoie tes commits sur GitHub. |
| `git checkout <branche>` | Change de branche. |
| `git log --oneline` | Historique résumé. |
| `git diff` | Montre ce qui a changé avant de commiter. |

### Format des messages de commit

```
feat: nouvelle fonctionnalité
fix: correction d'un bug
data: ajout ou modification de données
docs: documentation
test: tests
chore: configuration, nettoyage
```

Exemples : `feat: ajoute la carte Streamlit`, `fix: corrige la jointure sur le code commune`.

### En cas de problème

- **Conflit au `git pull`** : ouvre les fichiers marqués, garde la bonne version
  (supprime les lignes `<<<<<<<`, `=======`, `>>>>>>>`), puis `git add` sur chaque fichier corrigé et `git commit`.
  Bloqué plus de 30 minutes : demande à un coéquipier.
- **Commit fait par erreur (pas encore poussé)** : `git reset --soft HEAD~1`.
- **Clé API poussée par erreur** : la **régénérer immédiatement** (la supprimer de Git ne suffit pas).
- **Doute avant de tout casser** : copie le dossier en sauvegarde, puis demande de l'aide.

---

## 5. Équipe et organisation

- Équipe de 3 (FST Tanger). Rôles principaux : données et géo, pipeline, routes et application.
- Chaque brique doit pouvoir être expliquée par au moins deux personnes.
- Calendrier : mi-parcours **23 novembre**, dépôt des livrables **4 décembre**,
  finale **14 décembre**. Gel du code le 2 décembre au soir.

---

## 6. Sources et licences

- **HCP — RGPH 2024** : limites communales et population légale. Licence à confirmer (D-010).
- **OpenStreetMap, extrait Geofabrik** : hôpitaux et réseau routier — licence ODbL,
  « © contributeurs OpenStreetMap ». À citer dans toute publication.
- **Ministère de la Santé (MSPS)** : liste de 24 hôpitaux, utilisée pour un croisement partiel
  (16 retrouvés par leur nom).
- **OpenRouteService** : temps de trajet routiers.
- **Open-Meteo** : prévisions et historique météorologique.
- Code : licence MIT (voir `LICENSE`).

## 7. Limites

- OpenStreetMap peut être incomplet en zone rurale.
- Les temps de trajet sont des temps « normaux » (sans trafic ni fermeture).
- La météo est en mailles d'environ 10 km.
- Résultat = **indicateur d'aide à la décision**, pas une alerte officielle.