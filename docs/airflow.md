
# Orchestration du pipeline avec Apache Airflow

## 1. Objectif

Automatiser quotidiennement la récupération des prévisions
météorologiques, le calcul des risques d'accès aux soins
et leur enregistrement dans PostgreSQL pour les 146 communes
de la région Tanger-Tétouan-Al Hoceima.

## 2. Architecture technique

- Apache Airflow 3.4.0
- Python 3.11
- Docker Compose
- LocalExecutor
- PostgreSQL 16
- API Open-Meteo

Airflow utilise une base PostgreSQL dédiée à ses métadonnées,
distincte de la base de données métier tta_risk.

## 3. Pipeline quotidien

DAG : daily_health_access_risk

Les cinq tâches sont exécutées dans l'ordre suivant :

1. check_prerequisites
   Vérification des fichiers nécessaires, de la connexion
   PostgreSQL et de la disponibilité des seuils météo.

2. load_weather_forecast
   Récupération et stockage des prévisions météorologiques
   pour les 146 communes sur trois jours.

3. validate_forecast
   Contrôle de la complétude et de la qualité des prévisions.

4. compute_daily_risk
   Calcul et enregistrement des scores de risque.

5. validate_risk_results
   Vérification de la cohérence des résultats enregistrés.

## 4. Configuration

- Planification : tous les jours à 06h00.
- Expression Cron : 0 6 * * *
- Fuseau horaire : Africa/Casablanca.
- Catchup : désactivé.
- Nombre maximal de DAG runs simultanés : 1.
- Retries : 3 pour les tâches métier concernées.
- Délai entre les tentatives : 5 minutes.
- Timeout standard : 10 minutes.
- Timeout de l'ingestion météo : 30 minutes.
- Tâches de validation : aucun retry.

Les tâches suivantes sont bloquées lorsqu'une tâche échoue.

## 5. Prérequis

- Docker Desktop démarré.
- Fichier .env configuré.
- Référentiel des communes disponible.
- Temps de trajet disponibles.
- Seuils météorologiques calculés et chargés en base.
- Connexion Internet pour accéder à Open-Meteo.

Variables supplémentaires nécessaires dans .env :

AIRFLOW_DB_PASSWORD=
AIRFLOW_JWT_SECRET=

Utiliser des valeurs sécurisées et ne jamais les publier.

## 6. Installation et démarrage

Depuis la racine du projet, sous PowerShell :

```powershell
$compose = @("-f", "docker-compose.yml", "-f", "docker-compose.airflow.yml")

docker build -t tta-airflow:1.0 -f airflow/Dockerfile .

docker compose @compose up -d postgres

docker compose @compose run --rm airflow-init

docker compose @compose up -d airflow-api-server airflow-scheduler airflow-dag-processor

docker compose @compose ps -a
```

Pour une base métier existante nécessitant la migration
des colonnes de scoring :

```powershell
Get-Content sql/migrate_score.sql -Raw | docker compose @compose exec -T postgres psql -U postgres -d tta_risk -v ON_ERROR_STOP=1 --single-transaction -f -
```

Adapter le nom d'utilisateur PostgreSQL à la configuration
du fichier .env.

## 7. Interface Airflow

URL : http://localhost:8080

Utilisateur : admin

Récupération du mot de passe généré :

```powershell
docker compose @compose exec airflow-api-server cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Activation du DAG :

```powershell
docker compose @compose exec airflow-scheduler airflow dags unpause daily_health_access_risk
```

Déclenchement manuel :

```powershell
docker compose @compose exec airflow-scheduler airflow dags trigger daily_health_access_risk
```

Les services Docker doivent rester actifs pour permettre
les exécutions automatiques.

## 8. Tests automatisés

Les tests Airflow utilisent unittest, intégré à Python.

Fichier : airflow/tests/test_daily_risk_dag.py

```powershell
docker compose @compose cp airflow/tests/test_daily_risk_dag.py airflow-scheduler:/tmp/test_daily_risk_dag.py

docker compose @compose exec airflow-scheduler python /tmp/test_daily_risk_dag.py -v
```

Résultat obtenu : 12 tests réussis sur 12.

Les tests couvrent le chargement du DAG, les tâches,
les dépendances, le scheduling, le fuseau horaire,
les retries, les timeouts et les règles de déclenchement.

## 9. Résultats de validation

- Exécution manuelle réussie.
- Déclenchement automatique validé.
- 438 lignes de prévisions par date d'émission.
- 438 lignes de risque par date d'émission.
- Absence de doublons lors des réexécutions.
- Mécanisme de retry testé.
- Blocage des tâches suivantes testé.
- 12 tests automatisés réussis.

## 10. Limites et améliorations futures

- Traitement des seuils météorologiques manquants.
- Notifications automatiques en cas d'échec.
- Monitoring avancé.
- Intégration des tests Airflow dans GitHub Actions.
- Tests métier et tests de panne approfondis.

Les seuils manquants doivent être traités avant une
exploitation réelle des scores de risque.

Ne jamais supprimer les volumes PostgreSQL avec
docker compose down -v.
