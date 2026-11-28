
import logging
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import dag, task

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("/opt/tta-risk")

COMMUNES_CSV = PROJECT_ROOT / "data/processed/communes_TTA_2024.csv"
TRAVEL_CSV = PROJECT_ROOT / "data/processed/travel_time_TTA_2024.csv"
CONFIG_FILE = PROJECT_ROOT / "config/scoring_config.yaml"

TIMEZONE = "Africa/Casablanca"

# Default task configuration
DEFAULT_ARGS = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=10),
}


@dag(
    dag_id="daily_health_access_risk",
    description="Daily health access risk pipeline",
    start_date=pendulum.datetime(2026, 11, 28, tz=TIMEZONE),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["tta", "weather", "risk"],
)
def daily_health_access_risk():

    # TASK 1: Check prerequisites
    @task
    def check_prerequisites():
        from src.tta_risk.db.database import get_connection

        logger.info("Checking prerequisites")

        # Check required files
        for path in [COMMUNES_CSV, TRAVEL_CSV, CONFIG_FILE]:
            if not path.is_file():
                raise FileNotFoundError(f"Missing file: {path}")

        # Check database and thresholds
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM weather.thresholds"
                )
                threshold_count = cursor.fetchone()[0]

        if threshold_count == 0:
            raise RuntimeError("Weather thresholds are missing")

        # Determine forecast issuance date
        issued_on = pendulum.now(TIMEZONE).to_date_string()

        logger.info("Thresholds available: %s", threshold_count)
        logger.info("Forecast issued on: %s", issued_on)
        logger.info("All prerequisites are available")

        return issued_on

    # TASK 2: Extract and load weather forecasts
    @task(execution_timeout=timedelta(minutes=30))
    def load_weather_forecast(issued_on: str):
        from datetime import date

        from src.tta_risk.weather.forecast_client import FORECAST_DAYS
        from src.tta_risk.weather.forecast_loader import load_forecast

        logger.info("Starting forecast ingestion: %s", issued_on)

        if issued_on != pendulum.now(TIMEZONE).to_date_string():
            raise RuntimeError(
                "Cannot load current forecasts with an old issuance date"
            )

        total, n_communes, failed = load_forecast(
            issued_on=date.fromisoformat(issued_on),
            csv_path=str(COMMUNES_CSV),
        )

        expected = n_communes * FORECAST_DAYS

        logger.info("Communes: %s", n_communes)
        logger.info("Expected rows: %s", expected)
        logger.info("Written rows: %s", total)
        logger.info("Failed communes: %s", len(failed))

        if failed:
            raise RuntimeError(
                f"Forecast ingestion failed for {len(failed)} communes: {failed}"
            )

        if total != expected:
            raise RuntimeError(
                f"Incomplete forecast: expected {expected}, got {total}"
            )

        return {
            "issued_on": issued_on,
            "total_rows": total,
            "n_communes": n_communes,
        }

    # TASK 3: Validate forecast data quality
    @task(retries=0)
    def validate_forecast(metadata: dict):
        from datetime import date

        import pandas as pd

        from src.tta_risk.db.database import get_connection
        from src.tta_risk.weather.forecast_client import FORECAST_DAYS

        issued_on = date.fromisoformat(metadata["issued_on"])

        logger.info("Validating forecasts for %s", issued_on)

        communes = pd.read_csv(
            COMMUNES_CSV,
            usecols=["commune_code"],
            dtype={"commune_code": str},
        )

        expected_communes = set(communes["commune_code"])

        expected_dates = {
            issued_on + timedelta(days=i)
            for i in range(FORECAST_DAYS)
        }

        expected_pairs = {
            (commune, target_date)
            for commune in expected_communes
            for target_date in expected_dates
        }

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT commune_code,
                           target_date,
                           precip_mm,
                           tmax_c
                    FROM weather.forecast_daily
                    WHERE forecast_issued_on = %s
                    """,
                    (issued_on,),
                )

                rows = cursor.fetchall()

        actual_pairs = {
            (row[0], row[1]) for row in rows
        }

        missing_pairs = expected_pairs - actual_pairs
        unexpected_pairs = actual_pairs - expected_pairs

        invalid_rows = [
            row for row in rows
            if pd.isna(row[2])
            or pd.isna(row[3])
            or row[2] < 0
        ]

        logger.info("Expected rows: %s", len(expected_pairs))
        logger.info("Stored rows: %s", len(rows))
        logger.info("Missing pairs: %s", len(missing_pairs))
        logger.info("Unexpected pairs: %s", len(unexpected_pairs))
        logger.info("Invalid rows: %s", len(invalid_rows))

        if (
            missing_pairs
            or unexpected_pairs
            or invalid_rows
            or len(rows) != len(expected_pairs)
        ):
            raise RuntimeError(
                "Forecast data quality validation failed"
            )

        logger.info("Forecast data quality validation passed")

        return metadata

    # TASK 4: Compute daily health access risk
    @task
    def compute_daily_risk(metadata: dict):
        from datetime import date

        from scripts.run_risk_daily import run

        issued_on = date.fromisoformat(metadata["issued_on"])
        expected_rows = metadata["total_rows"]

        logger.info("Starting risk computation for %s", issued_on)

        total = run(issued_on=issued_on)

        logger.info("Expected risk rows: %s", expected_rows)
        logger.info("Computed risk rows: %s", total)

        if total != expected_rows:
            raise RuntimeError(
                f"Incomplete risk computation: "
                f"expected {expected_rows}, got {total}"
            )

        logger.info("Risk computation completed successfully")

        return {
            **metadata,
            "risk_rows": total,
        }

    # TASK 5: Validate final risk results
    @task(retries=0)
    def validate_risk_results(metadata: dict):
        from datetime import date

        from src.tta_risk.db.database import get_connection
        from src.tta_risk.scoring.score import (
            DEFAUTS,
            charger_config,
            couleur,
        )

        issued_on = date.fromisoformat(metadata["issued_on"])
        expected_rows = metadata["total_rows"]

        config = charger_config(str(CONFIG_FILE))
        couleurs = config.get("couleurs", DEFAUTS["couleurs"])

        logger.info("Validating risk results for %s", issued_on)

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT commune_code, target_date
                    FROM weather.forecast_daily
                    WHERE forecast_issued_on = %s
                    """,
                    (issued_on,),
                )
                forecast_pairs = set(cursor.fetchall())

                cursor.execute(
                    """
                    SELECT commune_code,
                           target_date,
                           danger,
                           classe_trajet,
                           score,
                           niveau,
                           raison
                    FROM weather.risk_daily
                    WHERE forecast_issued_on = %s
                    """,
                    (issued_on,),
                )
                rows = cursor.fetchall()

        actual_pairs = {
            (row[0], row[1]) for row in rows
        }

        missing_pairs = forecast_pairs - actual_pairs
        unexpected_pairs = actual_pairs - forecast_pairs

        invalid_rows = []

        for row in rows:
            commune, target_date, danger, classe, score, niveau, raison = row

            if (
                danger not in (0, 1, 2, 3)
                or classe not in (1, 2, 3)
                or score != danger * classe
                or raison not in ("pluie", "chaleur", "eloignement")
                or niveau != couleur(score, couleurs)
            ):
                invalid_rows.append(row)

        logger.info("Expected rows: %s", expected_rows)
        logger.info("Stored risk rows: %s", len(rows))
        logger.info("Missing pairs: %s", len(missing_pairs))
        logger.info("Unexpected pairs: %s", len(unexpected_pairs))
        logger.info("Invalid risk rows: %s", len(invalid_rows))

        if (
            len(rows) != expected_rows
            or len(forecast_pairs) != expected_rows
            or missing_pairs
            or unexpected_pairs
            or invalid_rows
        ):
            raise RuntimeError(
                "Risk results data quality validation failed"
            )

        logger.info("Risk results validation passed")
        logger.info("Daily pipeline completed successfully")

        return metadata

    # Task dependencies and XCom communication
    issued_on = check_prerequisites()
    forecast_metadata = load_weather_forecast(issued_on)
    validated_metadata = validate_forecast(forecast_metadata)
    risk_metadata = compute_daily_risk(validated_metadata)
    validate_risk_results(risk_metadata)


daily_health_access_risk()
