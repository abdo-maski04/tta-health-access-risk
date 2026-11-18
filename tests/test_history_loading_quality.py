import csv
from datetime import date
from pathlib import Path

import pytest

from src.tta_risk.db.database import get_connection

pytestmark = pytest.mark.integration

CSV_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "communes_TTA_2024.csv"
)
START_DATE = date(2016, 1, 1)
END_DATE = date(2025, 12, 31)
EXPECTED_DAYS = (END_DATE - START_DATE).days + 1


@pytest.fixture(scope="module")
def csv_commune_codes():
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as csv_file:
        commune_codes = [
            row["commune_code"].strip()
            for row in csv.DictReader(csv_file)
            if row.get("commune_code", "").strip()
        ]

    assert len(commune_codes) == len(set(commune_codes)), (
        f"Le CSV contient des codes commune dupliqués: {CSV_PATH}"
    )
    return set(commune_codes)


def test_all_csv_communes_are_loaded(csv_commune_codes):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT commune_code
                FROM weather.weather_daily
                WHERE commune_code = ANY(%s)
                """,
                (sorted(csv_commune_codes),),
            )
            loaded_codes = {row[0] for row in cursor.fetchall()}

    missing_codes = csv_commune_codes - loaded_codes
    assert not missing_codes, (
        f"Communes dans le CSV: {len(csv_commune_codes)}; "
        f"communes chargées: {len(loaded_codes)}; "
        f"codes absents: {sorted(missing_codes)}"
    )


def test_weather_rows_have_no_duplicate_commune_dates():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT commune_code, date, COUNT(*)
                FROM weather.weather_daily
                GROUP BY commune_code, date
                HAVING COUNT(*) > 1
                LIMIT 10
                """
            )
            duplicates = cursor.fetchall()

    assert not duplicates, f"Lignes météo dupliquées (maximum 10 affichées): {duplicates}"


def test_each_csv_commune_has_complete_date_coverage(csv_commune_codes):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT commune_code, COUNT(DISTINCT date), MIN(date), MAX(date)
                FROM weather.weather_daily
                WHERE commune_code = ANY(%s) AND date BETWEEN %s AND %s
                GROUP BY commune_code
                """,
                (sorted(csv_commune_codes), START_DATE, END_DATE),
            )
            coverage = {
                row[0]: {"days": row[1], "first_date": row[2], "last_date": row[3]}
                for row in cursor.fetchall()
            }

    incomplete = {
        code: coverage.get(code)
        for code in sorted(csv_commune_codes)
        if code not in coverage
        or coverage[code]["days"] != EXPECTED_DAYS
        or coverage[code]["first_date"] != START_DATE
        or coverage[code]["last_date"] != END_DATE
    }
    assert not incomplete, (
        f"Couverture attendue: {EXPECTED_DAYS} jours par commune, "
        f"du {START_DATE} au {END_DATE}. Communes incomplètes: {incomplete}"
    )
