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
| `Makefile` | Raccourcis de commandes (installer, tester, lancer l'application, construire les données). |
| `docker-compose.yml` | Lance Airflow et PostgreSQL ensemble en une commande. |

### Dossiers

| Dossier | Contenu et intérêt |
|---|---|
| `requirements/` | Dépendances Python, en trois fichiers : `base.txt` (communes, données, base), `app.txt` (Streamlit, cartes), `dev.txt` (tests). Séparés pour éviter les conflits de versions avec Airflow. |
| `data/raw/` | Fichiers sources tels que reçus (HCP 2024, GeoVulnera). Ne pas modifier. |
| `data/interim/` | Résultats intermédiaires (ex. historique météo brut). **Non versionné** (lourd, régénérable). |
| `data/processed/` | Jeu de données final livrable (CSV/Parquet/GeoJSON) et export de démo hors ligne. |
| `src/tta_risk/` | **Le cœur du projet** : tout le code réutilisable. |
| `src/tta_risk/config.py` | Paramètres centraux (chemins, URLs, lecture du `.env`). |
| `src/tta_risk/ingest/` | Chargement des communes, des hôpitaux et des contours. |
| `src/tta_risk/routing/` | Client OpenRouteService et calcul des temps de trajet. |
| `src/tta_risk/weather/` | Client Open-Meteo (prévisions, historique) et calcul des seuils. |
| `src/tta_risk/scoring/` | Danger météo, classe de trajet, score, couleur, raison principale. |
| `src/tta_risk/db/` | Accès à la base PostgreSQL (connexion, lecture, écriture). |
| `scripts/` | Points d'entrée de la partie fixe, lancés une seule fois (`build_communes`, `build_hospitals`, `build_travel_time`, `build_thresholds`). |
| `sql/schema.sql` | Création des tables (`communes`, `hospitals`, `travel_time`, `thresholds`, `forecast_daily`, `risk_daily`). |
| `docker/postgres/init.sql` | Crée automatiquement la base `tta_risk` au premier démarrage de PostgreSQL. |
| `airflow/dags/` | Le DAG quotidien (`daily_risk_dag.py`). Il reste **fin** : il appelle seulement des fonctions de `src/`. |
| `airflow/Dockerfile` | Image Airflow avec nos dépendances et accès à `src/`. |
| `app/streamlit_app.py` | Application web : carte, filtres, détail par commune. |
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

```powershell
git clone https://github.com/abdo-maski04/tta-health-access-risk.git
cd tta-health-access-risk
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt
copy .env.example .env
pytest
```

Linux/macOS : `source .venv/bin/activate` et `cp .env.example .env`.
Les instructions pour Docker (Airflow, PostgreSQL) et Streamlit seront ajoutées ici.

---

## 4. Travailler avec Git : le guide simple

### Les règles

1. **Chacun a sa branche personnelle** : `abderrahmane`, `membre-b`, `membre-c`.
   On ne commite **jamais** directement sur `main`.
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

# 3. Enregistrer
git add .
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
| `git add .` | Prépare toutes les modifications pour le commit. |
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
  (supprime les lignes `<<<<<<<`, `=======`, `>>>>>>>`), puis `git add .` et `git commit`.
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

- **HCP 2024** : population, ménages, superficie par commune.
- **GeoVulnera** : données géographiques des communes.
- **© contributeurs OpenStreetMap** (licence ODbL) : hôpitaux, routes, contours.
- **OpenRouteService** : temps de trajet.
- **Open-Meteo** : prévisions et historique météo.
- Code : licence MIT (voir `LICENSE`).

## 7. Limites

- OpenStreetMap peut être incomplet en zone rurale.
- Les temps de trajet sont des temps « normaux » (sans trafic ni fermeture).
- La météo est en mailles d'environ 10 km.
- Résultat = **indicateur d'aide à la décision**, pas une alerte officielle.